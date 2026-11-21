import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.modules.operations.work_orders import WorkOrderService
from app.modules.operations.verification import VerificationAnalyticsService
from app.models.work_orders import WorkOrderStatus, WorkOrderPriority, InterventionType
from app.models.telemetry import SensorReading

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

def test_before_after_intervention_verification(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    unique_suffix = str(uuid.uuid4())[:6]

    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"VERIF-ORG-{unique_suffix}")
    site = repo.create_site(org.id, name="South Mumbai Campus", city="Mumbai")
    _, _, zone = repo.create_hierarchy_node(site.id, "Science Wing", 1, "Chemistry Lab")
    sensor, _ = repo.register_sensor(zone.id, serial_number=f"SN-VERIF-{unique_suffix}")
    test_db.commit()

    wo_service = WorkOrderService(test_db)
    wo = wo_service.create_work_order(
        site_id=site.id,
        organization_id=org.id,
        zone_id=zone.id,
        title="Deploy Secondary Air Purifier",
        description="High particle concentration during lab experiment.",
        priority=WorkOrderPriority.HIGH,
        actor_name="Lab Coordinator"
    )

    # Intervention anchor timestamp: 30 minutes ago
    now = datetime.now(timezone.utc)
    anchor_time = now - timedelta(minutes=30)

    # 1. Seed Pre-Intervention Telemetry (T - 50m, T - 40m, T - 35m) -> High PM2.5 (~80 µg/m³), High CO2 (~1200 ppm)
    for delta_m, pm_val, co2_val in [(-50, 85.0, 1250.0), (-40, 80.0, 1200.0), (-35, 75.0, 1150.0)]:
        t = anchor_time + timedelta(minutes=delta_m)
        r_pm = SensorReading(
            id=str(uuid.uuid4()),
            sensor_id=sensor.id,
            zone_id=zone.id,
            site_id=site.id,
            measurement_type="PM2.5",
            measurement_value=pm_val,
            measurement_unit="µg/m³",
            sensor_timestamp=t,
            ingestion_timestamp=t,
            quality_status="VALID",
            provenance="MEASURED",
            idempotency_key=f"pre-pm-{delta_m}-{unique_suffix}"
        )
        r_co2 = SensorReading(
            id=str(uuid.uuid4()),
            sensor_id=sensor.id,
            zone_id=zone.id,
            site_id=site.id,
            measurement_type="CO2",
            measurement_value=co2_val,
            measurement_unit="ppm",
            sensor_timestamp=t,
            ingestion_timestamp=t,
            quality_status="VALID",
            provenance="MEASURED",
            idempotency_key=f"pre-co2-{delta_m}-{unique_suffix}"
        )
        test_db.add_all([r_pm, r_co2])

    # 2. Record Completed Intervention
    wo_service.transition_status(wo.id, WorkOrderStatus.IN_PROGRESS, actor_name="Technician")
    rec = wo_service.record_intervention(
        work_order_id=wo.id,
        intervention_type=InterventionType.AIR_PURIFIER_SPEED_BOOST,
        description="Turned dual CADR purifiers to maximum flow 450 m3/h.",
        performed_by="Technician",
        site_id=site.id,
        zone_id=zone.id
    )
    rec.completed_at = anchor_time
    wo_service.transition_status(wo.id, WorkOrderStatus.RESOLVED, actor_name="Technician", completion_notes="Purifiers active.")
    test_db.commit()

    # 3. Seed Post-Intervention Telemetry (T + 10m, T + 20m) -> Reduced PM2.5 (~35 µg/m³), Reduced CO2 (~700 ppm)
    for delta_m, pm_val, co2_val in [(10, 40.0, 750.0), (20, 30.0, 650.0)]:
        t = anchor_time + timedelta(minutes=delta_m)
        r_pm = SensorReading(
            id=str(uuid.uuid4()),
            sensor_id=sensor.id,
            zone_id=zone.id,
            site_id=site.id,
            measurement_type="PM2.5",
            measurement_value=pm_val,
            measurement_unit="µg/m³",
            sensor_timestamp=t,
            ingestion_timestamp=t,
            quality_status="VALID",
            provenance="MEASURED",
            idempotency_key=f"post-pm-{delta_m}-{unique_suffix}"
        )
        r_co2 = SensorReading(
            id=str(uuid.uuid4()),
            sensor_id=sensor.id,
            zone_id=zone.id,
            site_id=site.id,
            measurement_type="CO2",
            measurement_value=co2_val,
            measurement_unit="ppm",
            sensor_timestamp=t,
            ingestion_timestamp=t,
            quality_status="VALID",
            provenance="MEASURED",
            idempotency_key=f"post-co2-{delta_m}-{unique_suffix}"
        )
        test_db.add_all([r_pm, r_co2])
    test_db.commit()

    # 4. Compute Verification Analytics
    verif_service = VerificationAnalyticsService(test_db)
    result = verif_service.compute_work_order_verification(work_order_id=wo.id, window_minutes=60)

    assert result["work_order_id"] == wo.id
    assert "metrics" in result
    assert "PM2.5" in result["metrics"]
    pm_comp = result["metrics"]["PM2.5"]
    assert pm_comp["pre_mean"] == 80.0
    assert pm_comp["post_mean"] == 35.0
    assert pm_comp["delta"] == -45.0
    assert pm_comp["direction"] == "REDUCTION"
    assert pm_comp["percent_change"] < 0

    assert "CO2" in result["metrics"]
    co2_comp = result["metrics"]["CO2"]
    assert co2_comp["pre_mean"] == 1200.0
    assert co2_comp["post_mean"] == 700.0
    assert co2_comp["delta"] == -500.0

    # Epistemic integrity check
    assert "Observed change — not proof of causation" in result["epistemic_disclaimer"]
    assert "outdoor_context" in result

    # 5. Verify HTTP API endpoint
    res = client.get(f"/v1/work-orders/{wo.id}/verification?window_minutes=60")
    assert res.status_code == 200
    api_res = res.json()
    assert api_res["metrics"]["PM2.5"]["direction"] == "REDUCTION"
