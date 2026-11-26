import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.modules.operations.reporting import InstitutionalReportingService
from app.models.telemetry import SensorReading
from app.models.alerts import Alert, AlertRule, AlertSeverity, AlertStatus
from app.models.work_orders import WorkOrder, WorkOrderStatus, WorkOrderPriority

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

def test_institutional_operations_summary_and_export(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    unique_suffix = str(uuid.uuid4())[:6]

    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"REP-ORG-{unique_suffix}")
    site = repo.create_site(org.id, name="South Mumbai Campus", city="Mumbai")
    _, _, z1 = repo.create_hierarchy_node(site.id, "Academic Block", 1, "Classroom 1A")
    _, _, z2 = repo.create_hierarchy_node(site.id, "Academic Block", 1, "Classroom 1B")
    s1, _ = repo.register_sensor(z1.id, serial_number=f"SN-REP-{unique_suffix}")
    test_db.commit()

    now = datetime.now(timezone.utc)
    # Add telemetry for z1
    r1 = SensorReading(
        id=str(uuid.uuid4()),
        sensor_id=s1.id,
        zone_id=z1.id,
        site_id=site.id,
        measurement_type="PM2.5",
        measurement_value=45.0,
        measurement_unit="µg/m³",
        sensor_timestamp=now,
        ingestion_timestamp=now,
        quality_status="VALID",
        provenance="MEASURED",
        idempotency_key=f"rep-pm-{unique_suffix}"
    )
    r2 = SensorReading(
        id=str(uuid.uuid4()),
        sensor_id=s1.id,
        zone_id=z1.id,
        site_id=site.id,
        measurement_type="CO2",
        measurement_value=720.0,
        measurement_unit="ppm",
        sensor_timestamp=now,
        ingestion_timestamp=now,
        quality_status="VALID",
        provenance="MEASURED",
        idempotency_key=f"rep-co2-{unique_suffix}"
    )
    test_db.add_all([r1, r2])

    # Add an alert
    rule = AlertRule(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        site_id=site.id,
        name="CO2 Alert",
        measurement_type="CO2",
        threshold_value=1000.0,
        threshold_unit="ppm",
        severity=AlertSeverity.WARNING
    )
    test_db.add(rule)
    test_db.commit()

    alert = Alert(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        organization_id=org.id,
        site_id=site.id,
        zone_id=z1.id,
        title="Classroom CO2 High",
        description="Observed CO2 above nominal threshold",
        measurement_type="CO2",
        observed_value=1100.0,
        threshold_value=1000.0,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.RESOLVED,
        triggered_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(hours=1)
    )
    test_db.add(alert)

    # Add a work order
    wo = WorkOrder(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        site_id=site.id,
        zone_id=z1.id,
        title="Check dampers",
        description="Verify fresh air dampers",
        priority=WorkOrderPriority.MEDIUM,
        status=WorkOrderStatus.RESOLVED,
        created_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(hours=1),
        completion_notes="Dampers opened to 40%."
    )
    test_db.add(wo)
    test_db.commit()

    # 1. Test Service Layer Summary
    service = InstitutionalReportingService(test_db)
    summary = service.generate_site_operations_summary(site.id, days=7)

    assert summary["site_id"] == site.id
    assert summary["monitoring_coverage"]["total_zones"] == 2
    assert summary["monitoring_coverage"]["instrumented_zones"] == 1
    assert summary["monitoring_coverage"]["coverage_percent"] == 50.0
    assert summary["telemetry_volume"]["total_readings"] == 2
    assert summary["alerts_summary"]["total_triggered"] == 1
    assert summary["alerts_summary"]["resolved_count"] == 1
    assert summary["alerts_summary"]["resolution_rate_percent"] == 100.0
    assert summary["operations_and_interventions"]["total_work_orders"] == 1
    assert summary["operations_and_interventions"]["completed_work_orders"] == 1

    # 2. Test CSV Export Service
    csv_out = service.export_telemetry_csv(site.id, days=7)
    assert "Timestamp_UTC,Zone_ID,Sensor_ID,Measurement_Type,Value,Unit,Quality_Status,Provenance" in csv_out
    assert "PM2.5,45.0,µg/m³,VALID,MEASURED" in csv_out

    # 3. Test HTTP API Endpoints
    from app.models.institutional import InstitutionalUser, InstitutionalMembership, RoleEnum
    admin_id = str(uuid.uuid4())
    test_db.add(InstitutionalUser(id=admin_id, email=f"{admin_id[:8]}@school.edu", full_name="Test Admin", password_hash="hashed", is_active=True))
    test_db.add(InstitutionalMembership(id=str(uuid.uuid4()), user_id=admin_id, organization_id=org.id, role=RoleEnum.ADMIN, is_active=True))
    test_db.commit()
    headers = {"x-institutional-user-id": admin_id}

    res_sum = client.get(f"/v1/reports/site/{site.id}/summary?days=7", headers=headers)
    assert res_sum.status_code == 200
    assert res_sum.json()["monitoring_coverage"]["coverage_percent"] == 50.0

    res_csv = client.get(f"/v1/reports/site/{site.id}/export/csv?days=7", headers=headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Timestamp_UTC" in res_csv.text
