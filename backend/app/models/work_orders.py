from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid

from app.db.base import Base

class WorkOrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class InterventionType(str, enum.Enum):
    HVAC_VENTILATION_ADJUSTMENT = "HVAC_VENTILATION_ADJUSTMENT"
    WINDOW_OPENING_PURGE = "WINDOW_OPENING_PURGE"
    WINDOW_SEALING_OUTDOOR_SPIKE = "WINDOW_SEALING_OUTDOOR_SPIKE"
    AIR_PURIFIER_FILTER_REPLACEMENT = "AIR_PURIFIER_FILTER_REPLACEMENT"
    AIR_PURIFIER_SPEED_BOOST = "AIR_PURIFIER_SPEED_BOOST"
    SOURCE_EMISSION_ISOLATION = "SOURCE_EMISSION_ISOLATION"
    OCCUPANCY_REDUCTION = "OCCUPANCY_REDUCTION"
    OTHER = "OTHER"

class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(SQLEnum(WorkOrderPriority), default=WorkOrderPriority.MEDIUM, nullable=False)
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.OPEN, nullable=False)

    assigned_to_user_id = Column(String(36), ForeignKey("institutional_users.id", ondelete="SET NULL"), nullable=True)
    assigned_to_name = Column(String(255), nullable=True)

    created_by_user_id = Column(String(36), ForeignKey("institutional_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=True)
    in_progress_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    completion_notes = Column(Text, nullable=True)

    # Relationships
    events = relationship("WorkOrderEvent", back_populates="work_order", cascade="all, delete-orphan")
    interventions = relationship("InterventionRecord", back_populates="work_order", cascade="all, delete-orphan")

class WorkOrderEvent(Base):
    __tablename__ = "work_order_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_order_id = Column(String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False) # CREATED, ASSIGNED, STATUS_CHANGE, COMMENT, RESOLVED, CANCELLED
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    actor_name = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    work_order = relationship("WorkOrder", back_populates="events")

class InterventionRecord(Base):
    __tablename__ = "intervention_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    work_order_id = Column(String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)

    intervention_type = Column(SQLEnum(InterventionType), nullable=False)
    description = Column(Text, nullable=False)
    performed_by = Column(String(255), nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    metadata_json = Column(JSON, nullable=True)

    work_order = relationship("WorkOrder", back_populates="interventions")
