from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid

from app.db.base import Base

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=True) # None = Org-wide
    name = Column(String(255), nullable=False) # e.g. "Classroom High CO2 Stagnation"
    measurement_type = Column(String(32), nullable=False) # PM2.5, CO2, TEMP, RH
    operator = Column(String(8), default=">", nullable=False) # >, <, >=, <=
    threshold_value = Column(Float, nullable=False)
    threshold_unit = Column(String(16), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False)
    averaging_window_min = Column(Integer, default=15, nullable=False)
    min_observations = Column(Integer, default=1, nullable=False)
    rationale = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    alerts = relationship("Alert", back_populates="rule")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("alert_rules.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    sensor_id = Column(String(36), ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    measurement_type = Column(String(32), nullable=False)
    observed_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.OPEN, nullable=False)

    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    rule = relationship("AlertRule", back_populates="alerts")
    events = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    performed_by = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    alert = relationship("Alert", back_populates="events")
