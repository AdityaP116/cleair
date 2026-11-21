import pytest
from sqlalchemy import create_engine, select, func, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone, timedelta
import uuid

from app.db.base import Base
from app.models.institutional import Organization, Site, Building, Floor, Zone, InstitutionalUser, InstitutionalMembership, RoleEnum
from app.models.telemetry import Sensor, SensorCredential, SensorReading
from app.repositories.facilities import FacilityRepository
from app.core.security import generate_sensor_key, verify_sensor_key
from app.modules.ingestion.normalizer import validate_and_classify_measurement

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, echo=False)

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionMaker()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

def test_user_membership_and_roles(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()

    user = InstitutionalUser(
        email="facility.head@stxaviers.edu",
        full_name="Rajesh Sharma",
        password_hash="mock_hash_for_testing"
    )
    db_session.add(user)
    db_session.flush()

    membership = InstitutionalMembership(
        user_id=user.id,
        organization_id=org.id,
        role=RoleEnum.FACILITY_STAFF
    )
    db_session.add(membership)
    db_session.flush()

    assert membership.role == RoleEnum.FACILITY_STAFF
    assert membership.user.full_name == "Rajesh Sharma"
    assert membership.organization.code == "STX-MUM-01"

def test_institutional_hierarchy_traversal(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()
    site = repo.create_site(org.id, name="South Mumbai Campus")
    b, f, z = repo.create_hierarchy_node(site.id, "Primary Block", 1, "Classroom 4B")

    assert z.name == "Classroom 4B"
    assert z.floor.floor_number == 1
    assert z.floor.building.site.organization.id == org.id

def test_sensor_key_entropy_and_timing(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()
    site = repo.create_site(org.id)
    _, _, z = repo.create_hierarchy_node(site.id, "Block A", 1, "Science Lab")

    sensor, key = repo.register_sensor(z.id, serial_number="SN-MUM-99882")
    assert key.startswith("sq_live_")
    assert len(key) > 40 # 256-bit entropy token

    # Authenticate with valid key
    auth_ok = repo.authenticate_sensor(sensor.id, key)
    assert auth_ok is True

    # Authenticate with forged key
    auth_fail = repo.authenticate_sensor(sensor.id, "sq_live_invalid_forged_key")
    assert auth_fail is False

def test_revoked_sensor_key_rejected(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()
    site = repo.create_site(org.id)
    _, _, z = repo.create_hierarchy_node(site.id, "Block A", 1, "Science Lab")

    sensor, key = repo.register_sensor(z.id, serial_number="SN-MUM-REVOKE-1")
    assert repo.authenticate_sensor(sensor.id, key) is True

    # Revoke key
    revoked = repo.revoke_sensor_credential(sensor.id)
    assert revoked is True

    # After revocation, must reject
    assert repo.authenticate_sensor(sensor.id, key) is False

def test_telemetry_idempotency_duplicate_rejection(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()
    site = repo.create_site(org.id)
    _, _, z = repo.create_hierarchy_node(site.id, "Block A", 1, "Science Lab")
    sensor, _ = repo.register_sensor(z.id, serial_number="SN-IDEMP-01")

    now = datetime.now(timezone.utc)
    idemp_key = "packet-uuid-55123"

    reading1, created1 = repo.ingest_reading(
        sensor_id=sensor.id,
        site_id=site.id,
        zone_id=z.id,
        measurement_type="PM2.5",
        measurement_value=48.5,
        sensor_timestamp=now,
        idempotency_key=idemp_key
    )
    assert created1 is True

    # Ingest duplicate
    reading2, created2 = repo.ingest_reading(
        sensor_id=sensor.id,
        site_id=site.id,
        zone_id=z.id,
        measurement_type="PM2.5",
        measurement_value=48.5,
        sensor_timestamp=now,
        idempotency_key=idemp_key
    )
    assert created2 is False
    assert reading1.id == reading2.id

    # Count must be exactly 1
    count = db_session.scalar(select(func.count(SensorReading.id)))
    assert count == 1

def test_measurement_boundary_classification():
    # Valid PM2.5
    status_pm25, u1 = validate_and_classify_measurement("PM2.5", 55.4)
    assert status_pm25 == "VALID"
    assert u1 == "ug/m3"

    # Negative PM2.5 -> INVALID
    status_neg, _ = validate_and_classify_measurement("PM2.5", -12.0)
    assert status_neg == "INVALID"

    # Extreme PM2.5 -> OUT_OF_RANGE
    status_high, _ = validate_and_classify_measurement("PM2.5", 1450.0)
    assert status_high == "OUT_OF_RANGE"

    # Unrealistic low CO2 indoors (<350 ppm) -> SUSPECT
    status_co2, u2 = validate_and_classify_measurement("CO2", 280.0)
    assert status_co2 == "SUSPECT"
    assert u2 == "ppm"

def test_sensor_stale_and_offline_precedence(db_session: Session):
    repo = FacilityRepository(db_session)
    now = datetime.now(timezone.utc)

    # 1. Online: within 2x interval (interval = 300s -> 600s threshold)
    last_seen_online = now - timedelta(seconds=200)
    assert repo.calculate_sensor_freshness(last_seen_online, expected_interval_sec=300) == "ONLINE"

    # 2. Stale: > 2x interval but <= 24 hours
    last_seen_stale = now - timedelta(hours=3)
    assert repo.calculate_sensor_freshness(last_seen_stale, expected_interval_sec=300) == "STALE"

    # 3. Offline: > 24 hours
    last_seen_offline = now - timedelta(hours=28)
    assert repo.calculate_sensor_freshness(last_seen_offline, expected_interval_sec=300) == "OFFLINE"

def test_soft_delete_preserves_telemetry(db_session: Session):
    repo = FacilityRepository(db_session)
    org = repo.get_or_create_pilot_organization()
    site = repo.create_site(org.id)
    _, _, z = repo.create_hierarchy_node(site.id, "Block A", 1, "Classroom 4B")
    sensor, _ = repo.register_sensor(z.id, serial_number="SN-DECOM-01")

    now = datetime.now(timezone.utc)
    for i in range(10):
        repo.ingest_reading(
            sensor_id=sensor.id,
            site_id=site.id,
            zone_id=z.id,
            measurement_type="PM2.5",
            measurement_value=35.0 + i,
            sensor_timestamp=now + timedelta(minutes=i),
            idempotency_key=f"packet-{i}"
        )

    # Total 10 readings
    total_before = db_session.scalar(select(func.count(SensorReading.id)))
    assert total_before == 10

    # Soft delete zone & sensor
    repo.soft_delete_zone(z.id)
    repo.soft_delete_sensor(sensor.id)

    # Readings remain completely untouched and queryable
    total_after = db_session.scalar(select(func.count(SensorReading.id)))
    assert total_after == 10

    # Site with telemetry cannot be purged
    can_purge = repo.can_purge_site(site.id)
    assert can_purge is False
