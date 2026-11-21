from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Enum as SQLEnum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
import uuid

from app.db.base import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    FACILITY_STAFF = "FACILITY_STAFF"
    VIEWER = "VIEWER"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    code = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    sites = relationship("Site", back_populates="organization")
    users = relationship("InstitutionalMembership", back_populates="organization")

class InstitutionalUser(Base):
    __tablename__ = "institutional_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    memberships = relationship("InstitutionalMembership", back_populates="user")

class InstitutionalMembership(Base):
    __tablename__ = "institutional_memberships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("institutional_users.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=True) # Null means org-wide
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("InstitutionalUser", back_populates="memberships")
    organization = relationship("Organization", back_populates="users")
    site = relationship("Site")

class Site(Base):
    __tablename__ = "sites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    city = Column(String(64), default="Mumbai", nullable=False)
    latitude = Column(Float, default=18.9400, nullable=False)
    longitude = Column(Float, default=72.8350, nullable=False)
    timezone = Column(String(32), default="Asia/Kolkata", nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="sites")
    buildings = relationship("Building", back_populates="site")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    site_id = Column(String(36), ForeignKey("sites.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(64), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    site = relationship("Site", back_populates="buildings")
    floors = relationship("Floor", back_populates="building")

class Floor(Base):
    __tablename__ = "floors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    building_id = Column(String(36), ForeignKey("buildings.id"), nullable=False)
    floor_number = Column(Integer, nullable=False)
    name = Column(String(128), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    building = relationship("Building", back_populates="floors")
    zones = relationship("Zone", back_populates="floor")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    floor_id = Column(String(36), ForeignKey("floors.id"), nullable=False)
    name = Column(String(128), nullable=False)
    zone_type = Column(String(64), default="classroom", nullable=False)
    target_co2_max = Column(Float, default=1000.0, nullable=False)
    target_pm25_max = Column(Float, default=60.0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    floor = relationship("Floor", back_populates="zones")
    sensors = relationship("Sensor", back_populates="zone")
