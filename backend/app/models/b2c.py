from sqlalchemy import Column, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from app.db.base import Base


class B2CUserSession(Base):
    __tablename__ = "b2c_user_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class B2CUserProfile(Base):
    __tablename__ = "b2c_user_profiles"

    user_id = Column(String(64), primary_key=True)
    profile_json = Column(Text, nullable=False)
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
