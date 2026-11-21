from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, desc
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import json

from app.models.institutional import Organization, Site, Building, Floor, Zone, InstitutionalUser, InstitutionalMembership, RoleEnum
from app.models.telemetry import Sensor, SensorCredential, SensorReading
from app.core.security import generate_sensor_key, verify_sensor_key
from app.modules.ingestion.normalizer import validate_and_classify_measurement

class FacilityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_pilot_organization(self, name: str = "St. Xavier's Model School", code: str = "STX-MUM-01") -> Organization:
        stmt = select(Organization).where(Organization.code == code)
        org = self.session.execute(stmt).scalar_one_or_none()
        if not org:
            org = Organization(name=name, code=code)
            self.session.add(org)
            self.session.flush()
        return org

    def create_site(self, org_id: str, name: str = "South Mumbai Campus", city: str = "Mumbai") -> Site:
        site = Site(organization_id=org_id, name=name, city=city)
        self.session.add(site)
        self.session.flush()
        return site

    def get_site(self, site_id: str) -> Optional[Site]:
        stmt = select(Site).where(Site.id == site_id, Site.is_deleted == False)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_hierarchy_node(self, site_id: str, building_name: str, floor_num: int, zone_name: str, zone_type: str = "classroom") -> Tuple[Building, Floor, Zone]:
        b = Building(site_id=site_id, name=building_name)
        self.session.add(b)
        self.session.flush()

        f = Floor(building_id=b.id, floor_number=floor_num, name=f"Floor {floor_num}")
        self.session.add(f)
        self.session.flush()

        z = Zone(floor_id=f.id, name=zone_name, zone_type=zone_type)
        self.session.add(z)
        self.session.flush()

        return b, f, z

    def register_sensor(self, zone_id: str, serial_number: str, model: str = "AirMonitor-Pro-V2") -> Tuple[Sensor, str]:
        sensor = Sensor(zone_id=zone_id, serial_number=serial_number, model=model)
        self.session.add(sensor)
        self.session.flush()

        plaintext_key, prefix, salt, key_hash = generate_sensor_key()
        cred = SensorCredential(
            sensor_id=sensor.id,
            key_prefix=prefix,
            key_hash=key_hash,
            salt=salt,
            is_active=True
        )
        self.session.add(cred)
        self.session.flush()
        return sensor, plaintext_key

    def get_sensor(self, sensor_id: str) -> Optional[Sensor]:
        stmt = select(Sensor).where(Sensor.id == sensor_id, Sensor.is_deleted == False)
        return self.session.execute(stmt).scalar_one_or_none()

    def authenticate_sensor(self, sensor_id: str, provided_key: str) -> bool:
        stmt = select(SensorCredential).where(
            SensorCredential.sensor_id == sensor_id,
            SensorCredential.is_active == True,
            SensorCredential.is_revoked == False
        )
        cred = self.session.execute(stmt).scalar_one_or_none()
        if not cred:
            return False
        return verify_sensor_key(provided_key, cred.salt, cred.key_hash)

    def revoke_sensor_credential(self, sensor_id: str) -> bool:
        stmt = update(SensorCredential).where(
            SensorCredential.sensor_id == sensor_id,
            SensorCredential.is_active == True
        ).values(
            is_active=False,
            is_revoked=True,
            revoked_at=datetime.now(timezone.utc)
        )
        res = self.session.execute(stmt)
        self.session.flush()
        return res.rowcount > 0

    def ingest_reading(
        self,
        sensor_id: str,
        site_id: str,
        zone_id: Optional[str],
        measurement_type: str,
        measurement_value: float,
        sensor_timestamp: datetime,
        idempotency_key: str,
        provenance: str = "MEASURED",
        raw_payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[SensorReading, bool]:
        """
        Idempotent ingestion. Returns (reading_instance, was_created).
        """
        stmt = select(SensorReading).where(
            SensorReading.sensor_id == sensor_id,
            SensorReading.idempotency_key == idempotency_key
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing:
            return existing, False

        quality, unit = validate_and_classify_measurement(measurement_type, measurement_value)

        reading = SensorReading(
            sensor_id=sensor_id,
            site_id=site_id,
            zone_id=zone_id,
            measurement_type=measurement_type.upper(),
            measurement_value=measurement_value,
            measurement_unit=unit,
            provenance=provenance,
            quality_status=quality,
            sensor_timestamp=sensor_timestamp,
            raw_payload_json=json.dumps(raw_payload) if raw_payload else None,
            idempotency_key=idempotency_key
        )
        self.session.add(reading)

        # Update sensor last_seen_at
        sensor_stmt = update(Sensor).where(Sensor.id == sensor_id).values(last_seen_at=datetime.now(timezone.utc))
        self.session.execute(sensor_stmt)

        self.session.flush()
        return reading, True

    def calculate_sensor_freshness(self, last_seen_at: Optional[datetime], expected_interval_sec: int = 300) -> str:
        if not last_seen_at:
            return "UNKNOWN"
        now = datetime.now(timezone.utc)
        # Handle SQLite returning offset-naive datetime
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
        diff_sec = (now - last_seen_at).total_seconds()

        if diff_sec <= (2 * expected_interval_sec):
            return "ONLINE"
        elif diff_sec <= 86400: # 24 hours
            return "STALE"
        else:
            return "OFFLINE"

    def get_site_zones_status(self, site_id: str) -> List[Dict[str, Any]]:
        """
        Returns full hierarchy zones for a site with their latest readings and sensor freshness.
        """
        stmt = select(Zone).join(Floor).join(Building).where(
            Building.site_id == site_id,
            Zone.is_deleted == False
        )
        zones = self.session.execute(stmt).scalars().all()
        results = []

        for z in zones:
            # Find active sensor in this zone
            sensor_stmt = select(Sensor).where(Sensor.zone_id == z.id, Sensor.is_deleted == False)
            sensor = self.session.execute(sensor_stmt).scalar_one_or_none()
            freshness = self.calculate_sensor_freshness(sensor.last_seen_at, sensor.expected_interval_sec) if sensor else "NO_SENSOR"

            # Get latest readings for this zone
            readings_stmt = select(SensorReading).where(
                SensorReading.zone_id == z.id
            ).order_by(desc(SensorReading.sensor_timestamp)).limit(5)
            readings = self.session.execute(readings_stmt).scalars().all()

            results.append({
                "zone_id": z.id,
                "name": z.name,
                "zone_type": z.zone_type,
                "building_name": z.floor.building.name if z.floor and z.floor.building else "Main Block",
                "floor_number": z.floor.floor_number if z.floor else 0,
                "target_co2_max": z.target_co2_max,
                "target_pm25_max": z.target_pm25_max,
                "sensor_id": sensor.id if sensor else None,
                "sensor_status": freshness,
                "latest_readings": [
                    {
                        "measurement_type": r.measurement_type,
                        "value": r.measurement_value,
                        "unit": r.measurement_unit,
                        "quality_status": r.quality_status,
                        "provenance": r.provenance,
                        "timestamp": r.sensor_timestamp
                    }
                    for r in readings
                ]
            })

        return results

    def soft_delete_zone(self, zone_id: str) -> bool:
        stmt = update(Zone).where(Zone.id == zone_id).values(
            is_deleted=True,
            deleted_at=datetime.now(timezone.utc)
        )
        res = self.session.execute(stmt)
        self.session.flush()
        return res.rowcount > 0

    def soft_delete_sensor(self, sensor_id: str) -> bool:
        stmt = update(Sensor).where(Sensor.id == sensor_id).values(
            is_deleted=True,
            deleted_at=datetime.now(timezone.utc)
        )
        res = self.session.execute(stmt)
        self.session.flush()
        return res.rowcount > 0

    def can_purge_site(self, site_id: str) -> bool:
        stmt = select(func.count(SensorReading.id)).where(SensorReading.site_id == site_id)
        count = self.session.execute(stmt).scalar()
        return count == 0
