import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.models.institutional import InstitutionalUser, InstitutionalMembership, RoleEnum

client = TestClient(app)


@pytest.fixture
def rbac_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()
    session.close()


def _create_user(db, org_id: str, role: RoleEnum, active: bool = True) -> str:
    uid = str(uuid.uuid4())
    user = InstitutionalUser(
        id=uid,
        email=f"{uid[:8]}@school.edu",
        full_name=f"Test {role.value}",
        password_hash="hashed",
        is_active=active,
    )
    mem = InstitutionalMembership(
        id=str(uuid.uuid4()),
        user_id=uid,
        organization_id=org_id,
        role=role,
        is_active=True,
    )
    db.add_all([user, mem])
    db.commit()
    return uid


def test_unauthenticated_work_order_and_alert_rule_rejected(rbac_db):
    assert client.post("/v1/work-orders", json={}).status_code == 401
    assert client.post("/v1/alerts/rules", json={}).status_code == 401
    assert client.get("/v1/reports/site/any/summary").status_code == 401


def test_disabled_user_rejected(rbac_db):
    repo = FacilityRepository(rbac_db)
    org = repo.get_or_create_pilot_organization(code="RBAC-DIS")
    site = repo.create_site(org.id, name="Campus", city="Mumbai")
    rbac_db.commit()
    uid = _create_user(rbac_db, org.id, RoleEnum.ADMIN, active=False)

    res = client.get(
        f"/v1/reports/site/{site.id}/summary",
        headers={"x-institutional-user-id": uid},
    )
    assert res.status_code == 401


def test_role_hierarchy_enforced(rbac_db):
    repo = FacilityRepository(rbac_db)
    org = repo.get_or_create_pilot_organization(code="RBAC-ORG")
    site = repo.create_site(org.id, name="Campus A", city="Mumbai")
    rbac_db.commit()

    viewer_id = _create_user(rbac_db, org.id, RoleEnum.VIEWER)
    staff_id = _create_user(rbac_db, org.id, RoleEnum.FACILITY_STAFF)
    admin_id = _create_user(rbac_db, org.id, RoleEnum.ADMIN)

    # VIEWER cannot create work order or alert rule
    assert (
        client.post(
            "/v1/work-orders",
            json={"site_id": site.id, "title": "Test", "description": "Desc"},
            headers={"x-institutional-user-id": viewer_id},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/v1/alerts/rules",
            json={
                "organization_id": org.id,
                "site_id": site.id,
                "name": "R1",
                "measurement_type": "PM2.5",
                "threshold_value": 60.0,
                "threshold_unit": "ug/m3",
            },
            headers={"x-institutional-user-id": viewer_id},
        ).status_code
        == 403
    )

    # FACILITY_STAFF can create work order (201) but NOT alert rule (403)
    assert (
        client.post(
            "/v1/work-orders",
            json={"site_id": site.id, "title": "Fix fan", "description": "Desc"},
            headers={"x-institutional-user-id": staff_id},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/v1/alerts/rules",
            json={
                "organization_id": org.id,
                "site_id": site.id,
                "name": "R1",
                "measurement_type": "PM2.5",
                "threshold_value": 60.0,
                "threshold_unit": "ug/m3",
            },
            headers={"x-institutional-user-id": staff_id},
        ).status_code
        == 403
    )

    # ADMIN can create alert rule
    assert (
        client.post(
            "/v1/alerts/rules",
            json={
                "organization_id": org.id,
                "site_id": site.id,
                "name": "R1",
                "measurement_type": "PM2.5",
                "threshold_value": 60.0,
                "threshold_unit": "ug/m3",
            },
            headers={"x-institutional-user-id": admin_id},
        ).status_code
        == 201
    )


def test_cross_tenant_isolation_enforced(rbac_db):
    repo = FacilityRepository(rbac_db)
    org_a = repo.get_or_create_pilot_organization(code="ORG-A")
    org_b = repo.get_or_create_pilot_organization(code="ORG-B")
    site_b = repo.create_site(org_b.id, name="Org B Campus", city="Pune")
    rbac_db.commit()

    admin_a = _create_user(rbac_db, org_a.id, RoleEnum.ADMIN)

    # Org A admin cannot read Org B's reports or create work orders on Org B's site
    assert (
        client.get(
            f"/v1/reports/site/{site_b.id}/summary",
            headers={"x-institutional-user-id": admin_a},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/v1/work-orders",
            json={"site_id": site_b.id, "title": "Cross-tenant", "description": "Attack"},
            headers={"x-institutional-user-id": admin_a},
        ).status_code
        == 403
    )
