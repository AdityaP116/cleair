import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import uuid

from app.main import app
from app.db.base import Base
from app.db.session import SessionLocal, get_db
from app.repositories.facilities import FacilityRepository
from app.models.alerts import AlertRule, AlertSeverity, AlertStatus
from app.modules.alerts.engine import AlertEngineService

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

def test_alert_rule_creation_and_threshold_evaluation(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"ALERT-TEST-{str(uuid.uuid4())[:6]}")
    site = repo.create_site(org.id, name="Test Campus", city="Mumbai")
    _, _, z = repo.create_hierarchy_node(site.id, "Academic Block", 1, "Classroom 3A")
    sensor, secret_key = repo.register_sensor(z.id, serial_number=f"SN-ALERT-{str(uuid.uuid4())[:6]}")

    from app.models.institutional import InstitutionalUser, InstitutionalMembership, RoleEnum
    admin_id = str(uuid.uuid4())
    test_db.add(InstitutionalUser(id=admin_id, email=f"{admin_id[:8]}@school.edu", full_name="Test Admin", password_hash="hashed", is_active=True))
    test_db.add(InstitutionalMembership(id=str(uuid.uuid4()), user_id=admin_id, organization_id=org.id, role=RoleEnum.ADMIN, is_active=True))
    test_db.commit()
    headers = {"x-institutional-user-id": admin_id}

    # 1. Create AlertRule for High CO2 (> 1000 ppm)
    rule_payload = {
        "name": "Classroom Elevated CO2",
        "measurement_type": "CO2",
        "operator": ">",
        "threshold_value": 1000.0,
        "threshold_unit": "ppm",
        "severity": "WARNING",
        "site_id": site.id,
        "rationale": "ASHRAE indoor ventilation standard"
    }
    res_rule = client.post("/v1/alerts/rules", json=rule_payload, headers=headers)
    assert res_rule.status_code in (200, 201)
    rule_data = res_rule.json()
    rule_id = rule_data["id"]

    # 2. Ingest reading BELOW threshold (CO2 = 800) -> NO ALERT
    now = datetime.now(timezone.utc).isoformat()
    client.post("/v1/telemetry/ingest", json={
        "sensor_id": sensor.id,
        "idempotency_key": "pkt-below",
        "timestamp": now,
        "measurements": [{"type": "CO2", "value": 800.0}]
    }, headers={"x-sensor-key": secret_key})

    res_alerts_0 = client.get(f"/v1/alerts/site/{site.id}")
    assert len(res_alerts_0.json()) == 0

    # 3. Ingest reading EXCEEDING threshold (CO2 = 1250) -> TRIGGERS ALERT
    client.post("/v1/telemetry/ingest", json={
        "sensor_id": sensor.id,
        "idempotency_key": "pkt-exceed-1",
        "timestamp": now,
        "measurements": [{"type": "CO2", "value": 1250.0}]
    }, headers={"x-sensor-key": secret_key})

    res_alerts_1 = client.get(f"/v1/alerts/site/{site.id}")
    alerts_list = res_alerts_1.json()
    assert len(alerts_list) == 1
    alert = alerts_list[0]
    assert alert["status"] == "OPEN"
    assert alert["observed_value"] == 1250.0

    # 4. Ingest another high reading -> DEDUPLICATION prevents alert flooding
    client.post("/v1/telemetry/ingest", json={
        "sensor_id": sensor.id,
        "idempotency_key": "pkt-exceed-2",
        "timestamp": now,
        "measurements": [{"type": "CO2", "value": 1310.0}]
    }, headers={"x-sensor-key": secret_key})

    res_alerts_2 = client.get(f"/v1/alerts/site/{site.id}")
    assert len(res_alerts_2.json()) == 1 # Still exactly 1 active alert!

    # 5. Acknowledge the alert
    res_ack = client.post(f"/v1/alerts/{alert['id']}/acknowledge", json={
        "acknowledged_by": "Staff Operator"
    })
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "ACKNOWLEDGED"

    # 6. Resolve the alert
    res_res = client.post(f"/v1/alerts/{alert['id']}/resolve", json={
        "resolved_by": "Facility Manager",
        "resolution_notes": "Opened windows and adjusted ventilation fan."
    })
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"

