import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.modules.operations.work_orders import WorkOrderService
from app.models.work_orders import WorkOrderStatus, WorkOrderPriority, InterventionType
from app.models.alerts import Alert, AlertRule, AlertSeverity, AlertStatus

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

def test_work_order_lifecycle_and_interventions(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    unique_suffix = str(uuid.uuid4())[:6]

    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"WO-TEST-ORG-{unique_suffix}")
    site = repo.create_site(org.id, name="South Mumbai Campus", city="Mumbai")
    _, _, zone = repo.create_hierarchy_node(site.id, "Main Building", 2, "Physics Lab")
    test_db.commit()

    service = WorkOrderService(test_db)

    # Create real AlertRule to satisfy foreign key constraint
    rule = AlertRule(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        site_id=site.id,
        name="CO2 Threshold Rule",
        measurement_type="CO2",
        threshold_value=1000.0,
        threshold_unit="ppm",
        severity=AlertSeverity.WARNING
    )
    test_db.add(rule)
    test_db.commit()

    # 1. Create a work order linked to an alert
    alert = Alert(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        organization_id=org.id,
        site_id=site.id,
        zone_id=zone.id,
        title="Excessive CO2 in Physics Lab",
        description="CO2 observed at 1450 ppm exceeding 1000 ppm threshold",
        measurement_type="CO2",
        observed_value=1450.0,
        threshold_value=1000.0,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.OPEN
    )
    test_db.add(alert)
    test_db.commit()

    wo = service.create_work_order(
        site_id=site.id,
        organization_id=org.id,
        zone_id=zone.id,
        alert_id=alert.id,
        title="Ventilation purge for Physics Lab",
        description="Inspect HVAC fresh air dampers and purge classroom air.",
        priority=WorkOrderPriority.HIGH,
        actor_name="Facility Lead"
    )

    assert wo.id is not None
    assert wo.status == WorkOrderStatus.OPEN
    assert len(wo.events) == 1
    assert wo.events[0].event_type == "CREATED"

    # Verify linked alert transitioned to INVESTIGATING
    test_db.refresh(alert)
    assert alert.status == AlertStatus.INVESTIGATING

    # 2. Assign work order
    wo_assigned = service.assign_work_order(
        work_order_id=wo.id,
        assigned_to_name="Ramesh Sharma (Technician)",
        actor_name="Facility Lead"
    )
    assert wo_assigned.status == WorkOrderStatus.ASSIGNED
    assert wo_assigned.assigned_to_name == "Ramesh Sharma (Technician)"
    assert len(wo_assigned.events) == 2

    # 3. Transition to IN_PROGRESS
    wo_prog = service.transition_status(
        work_order_id=wo.id,
        new_status=WorkOrderStatus.IN_PROGRESS,
        actor_name="Ramesh Sharma"
    )
    assert wo_prog.status == WorkOrderStatus.IN_PROGRESS
    assert wo_prog.in_progress_at is not None

    # 4. Record physical intervention
    rec = service.record_intervention(
        work_order_id=wo.id,
        intervention_type=InterventionType.HVAC_VENTILATION_ADJUSTMENT,
        description="Adjusted mechanical damper to 60% fresh air intake and cleaned pre-filters.",
        performed_by="Ramesh Sharma",
        site_id=site.id,
        zone_id=zone.id,
        metadata_json={"damper_position_pct": 60, "prefilter_cleaned": True}
    )
    assert rec.id is not None
    assert rec.intervention_type == InterventionType.HVAC_VENTILATION_ADJUSTMENT

    # 5. Resolve work order with completion notes
    wo_resolved = service.transition_status(
        work_order_id=wo.id,
        new_status=WorkOrderStatus.RESOLVED,
        actor_name="Ramesh Sharma",
        completion_notes="Damper calibrated, pre-filters cleared, airflow restored."
    )
    assert wo_resolved.status == WorkOrderStatus.RESOLVED
    assert wo_resolved.resolved_at is not None
    assert "Damper calibrated" in wo_resolved.completion_notes

    # Verify linked alert is automatically resolved
    test_db.refresh(alert)
    assert alert.status == AlertStatus.RESOLVED
    assert "Resolved via Work Order" in alert.resolution_notes

def test_work_order_api_endpoints(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    unique_suffix = str(uuid.uuid4())[:6]

    repo = FacilityRepository(test_db)
    org = repo.get_or_create_pilot_organization(code=f"WO-API-ORG-{unique_suffix}")
    site = repo.create_site(org.id, name="Dadar Academy", city="Mumbai")
    _, _, zone = repo.create_hierarchy_node(site.id, "West Block", 1, "Biology Lab")
    test_db.commit()

    # 1. POST /v1/work-orders
    res = client.post("/v1/work-orders", json={
        "site_id": site.id,
        "organization_id": org.id,
        "zone_id": zone.id,
        "title": "Replace HEPA Filter Unit 3",
        "description": "Operating hours exceeded 2000h threshold.",
        "priority": "HIGH",
        "actor_name": "Senior Operator"
    })
    assert res.status_code == 201
    wo_data = res.json()
    wo_id = wo_data["id"]
    assert wo_data["status"] == "OPEN"

    # 2. GET /v1/work-orders/site/{site_id}
    res_list = client.get(f"/v1/work-orders/site/{site.id}")
    assert res_list.status_code == 200
    orders = res_list.json()
    assert len(orders) >= 1
    assert orders[0]["id"] == wo_id

    # 3. POST /v1/work-orders/{id}/assign
    res_assign = client.post(f"/v1/work-orders/{wo_id}/assign", json={
        "assigned_to_name": "Sunil Patil",
        "actor_name": "Supervisor"
    })
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "ASSIGNED"

    # 4. POST /v1/work-orders/{id}/interventions
    res_int = client.post(f"/v1/work-orders/{wo_id}/interventions", json={
        "intervention_type": "AIR_PURIFIER_FILTER_REPLACEMENT",
        "description": "Installed new H13 True-HEPA cartridge.",
        "performed_by": "Sunil Patil",
        "site_id": site.id,
        "zone_id": zone.id,
        "metadata_json": {"filter_serial": "FLT-H13-889"}
    })
    assert res_int.status_code == 201
    assert res_int.json()["intervention_type"] == "AIR_PURIFIER_FILTER_REPLACEMENT"

    # 5. POST /v1/work-orders/{id}/status
    res_stat = client.post(f"/v1/work-orders/{wo_id}/status", json={
        "status": "RESOLVED",
        "actor_name": "Sunil Patil",
        "completion_notes": "Cartridge fitted, differential pressure verified nominal."
    })
    assert res_stat.status_code == 200
    assert res_stat.json()["status"] == "RESOLVED"

    # 6. GET /v1/work-orders/{id}
    res_det = client.get(f"/v1/work-orders/{wo_id}")
    assert res_det.status_code == 200
    det = res_det.json()
    assert len(det["events"]) >= 3
    assert len(det["interventions"]) == 1
    assert det["completion_notes"] is not None
