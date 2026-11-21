import pytest
import uuid
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.db.base import Base
from app.db.session import SessionLocal, get_db
from app.repositories.facilities import FacilityRepository

client = TestClient(app)

@pytest.fixture
def test_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    Base.metadata.create_all(test_engine)
    SessionMaker = sessionmaker(bind=test_engine)
    session = SessionMaker()
    yield session
    session.close()

def test_telemetry_ingestion_api_flow(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    # Setup test hierarchy with unique serial number per run
    unique_suffix = str(uuid.uuid4())[:6]
    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"API-TEST-ORG-{unique_suffix}")
    site = repo.create_site(org.id, name="Bandra Academic Campus", city="Mumbai")
    _, _, z = repo.create_hierarchy_node(site.id, "Main Block", 1, "Auditorium")
    sensor, secret_key = repo.register_sensor(z.id, serial_number=f"API-SN-{unique_suffix}")
    test_db.commit()

    # 1. Ingest valid telemetry via API
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "sensor_id": sensor.id,
        "idempotency_key": "api-packet-01",
        "timestamp": now_iso,
        "measurements": [
            {"type": "PM2.5", "value": 42.5},
            {"type": "CO2", "value": 850.0},
            {"type": "TEMP", "value": 26.5},
            {"type": "RH", "value": 65.0}
        ],
        "provenance": "MEASURED"
    }

    headers = {"x-sensor-key": secret_key}
    res = client.post("/v1/telemetry/ingest", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["readings_recorded"] == 4
    assert data["was_duplicate"] is False

    # 2. Re-submitting identical idempotency key returns duplicate acknowledgment without crash
    res_dup = client.post("/v1/telemetry/ingest", json=payload, headers=headers)
    assert res_dup.status_code == 200
    assert res_dup.json()["was_duplicate"] is True

    # 3. Submitting with revoked or invalid key is rejected with HTTP 401
    bad_headers = {"x-sensor-key": "sq_live_forged_key_12345"}
    res_bad = client.post("/v1/telemetry/ingest", json=payload, headers=bad_headers)
    assert res_bad.status_code == 401

    # 4. Check sensor status endpoint
    res_status = client.get(f"/v1/telemetry/sensors/{sensor.id}/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["freshness"] == "ONLINE"
    assert status_data["zone_name"] == "Auditorium"

    # 5. Check facility zones status
    res_zones = client.get(f"/v1/facilities/sites/{site.id}/zones")
    assert res_zones.status_code == 200
    zones = res_zones.json()
    assert len(zones) >= 1
    assert any(z["name"] == "Auditorium" for z in zones)

    # 6. Check Mumbai outdoor context
    res_outdoor = client.get(f"/v1/facilities/sites/{site.id}/outdoor")
    assert res_outdoor.status_code == 200
    outdoor = res_outdoor.json()
    assert outdoor["city"] == "Mumbai"
    assert "pm25" in outdoor
