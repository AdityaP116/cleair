from datetime import datetime, timezone, timedelta
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.institutional import Organization, Site, Building, Floor, Zone, InstitutionalUser, InstitutionalMembership, RoleEnum
from app.models.telemetry import Sensor, SensorCredential, SensorReading
from app.repositories.facilities import FacilityRepository

def seed_pilot():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    repo = FacilityRepository(db)

    # 1. Organization
    org = repo.get_or_create_pilot_organization(
        name="St. Xavier's Model School",
        code="STX-MUM-01"
    )

    # 2. Site
    site = db.query(Site).filter(Site.organization_id == org.id, Site.name == "South Mumbai Campus").first()
    if not site:
        site = repo.create_site(org.id, name="South Mumbai Campus", city="Mumbai")

    # 3. Hierarchy: Building -> Floors -> Zones
    existing_building = db.query(Building).filter(Building.site_id == site.id, Building.name == "Primary Academic Block").first()
    if not existing_building:
        b1, f1, z1 = repo.create_hierarchy_node(site.id, "Primary Academic Block", 1, "Classroom 4B (Grade 8)", "classroom")
        _, _, z2 = repo.create_hierarchy_node(site.id, "Primary Academic Block", 1, "Science Lab", "laboratory")
        _, f2, z3 = repo.create_hierarchy_node(site.id, "Primary Academic Block", 2, "Senior Library", "library")
        _, _, z4 = repo.create_hierarchy_node(site.id, "Primary Academic Block", 2, "Indoor Sports Hall", "gymnasium")
    else:
        zones = db.query(Zone).all()
        z1, z2, z3, z4 = zones[0], zones[1], zones[2], zones[3]

    # 4. Sensor & Initial Readings
    existing_sensor = db.query(Sensor).filter(Sensor.serial_number == "SN-PILOT-4B").first()
    if not existing_sensor:
        sensor, key = repo.register_sensor(z1.id, serial_number="SN-PILOT-4B", model="AeroSense-Institutional-Pro")
        print(f"Registered Sensor SN-PILOT-4B. Plaintext Key: {key}")
        
        # Seed initial baseline readings (clearly tagged as SIMULATED for pilot demo)
        now = datetime.now(timezone.utc)
        repo.ingest_reading(
            sensor_id=sensor.id,
            site_id=site.id,
            zone_id=z1.id,
            measurement_type="PM2.5",
            measurement_value=38.4,
            sensor_timestamp=now,
            idempotency_key="seed-init-01",
            provenance="SIMULATED"
        )
        repo.ingest_reading(
            sensor_id=sensor.id,
            site_id=site.id,
            zone_id=z1.id,
            measurement_type="CO2",
            measurement_value=720.0,
            sensor_timestamp=now,
            idempotency_key="seed-init-02",
            provenance="SIMULATED"
        )

    # 5. Seed pilot user
    existing_user = db.query(InstitutionalUser).filter(InstitutionalUser.email == "facility.head@stxaviers.edu").first()
    if not existing_user:
        user = InstitutionalUser(
            email="facility.head@stxaviers.edu",
            full_name="Rajesh Sharma",
            password_hash="dev_mock_hash"
        )
        db.add(user)
        db.flush()
        membership = InstitutionalMembership(
            user_id=user.id,
            organization_id=org.id,
            site_id=site.id,
            role=RoleEnum.FACILITY_STAFF
        )
        db.add(membership)

    db.commit()
    db.close()
    print("Pilot database successfully seeded with St. Xavier's Model School hierarchy and baseline telemetry.")

if __name__ == "__main__":
    seed_pilot()
