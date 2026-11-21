from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.base import Base

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # On deleting zone, sensor reference is set to NULL rather than cascading
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    serial_number = Column(String(128), unique=True, nullable=False, index=True)
    model = Column(String(128), nullable=False)
    expected_interval_sec = Column(Integer, default=300, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    zone = relationship("Zone", back_populates="sensors")
    credentials = relationship("SensorCredential", back_populates="sensor")
    readings = relationship("SensorReading", back_populates="sensor")

class SensorCredential(Base):
    __tablename__ = "sensor_credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sensor_id = Column(String(36), ForeignKey("sensors.id"), nullable=False)
    key_prefix = Column(String(8), nullable=False, index=True)
    key_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    sensor = relationship("Sensor", back_populates="credentials")

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Historical integrity: if sensor or zone is removed/decommissioned, reading remains intact
    sensor_id = Column(String(36), ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True, index=True)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True, index=True)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False, index=True)
    
    measurement_type = Column(String(32), nullable=False) # PM2.5, PM10, CO2, TEMP, RH
    measurement_value = Column(Float, nullable=False)
    measurement_unit = Column(String(16), nullable=False) # ug/m3, ppm, C, %
    provenance = Column(String(16), default="MEASURED", nullable=False) # MEASURED, SIMULATED, ESTIMATED
    quality_status = Column(String(16), default="VALID", nullable=False) # VALID, SUSPECT, OUT_OF_RANGE, INVALID
    
    sensor_timestamp = Column(DateTime(timezone=True), nullable=False)
    ingestion_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_payload_json = Column(Text, nullable=True)
    
    idempotency_key = Column(String(128), nullable=False)

    __table_args__ = (
        UniqueConstraint("sensor_id", "idempotency_key", name="uq_sensor_reading_idempotent"),
    )

    sensor = relationship("Sensor", back_populates="readings")
