import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.b2c import B2CUserSession, B2CUserProfile

# Ensure B2C tables exist
Base.metadata.create_all(bind=engine)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PersistentB2CRepository:
    """Drop-in replacement for InMemoryRepository backed by SQLAlchemy."""

    DEFAULT_PROFILE = {
        "city": "Mumbai",
        "locality": "Andheri West",
        "geohash": "te7u",
        "has_child": False,
        "has_elderly": False,
        "is_pregnant": False,
        "has_respiratory_condition": False,
        "has_heart_condition": False,
        "commute_mode": "two_wheeler",
        "commute_minutes_per_day": 45,
        "outdoor_work": False,
        "home_size_sqm": 25.0,
        "ceiling_height_m": 2.7,
        "has_purifier": False,
        "purifier_cadr_m3h": 250.0,
        "has_ac": False,
        "cooking_fuel": "lpg",
        "budget_tier": "low",
        "language": "en",
        "briefing_time": "06:30",
    }

    def create_session(self, token: str, user_id: str, ttl_hours: int = 24) -> None:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            sess = B2CUserSession(
                token_hash=_hash_token(token),
                user_id=user_id,
                expires_at=now + timedelta(hours=ttl_hours),
                is_revoked=False,
            )
            db.merge(sess)
            db.commit()
        finally:
            db.close()

    def get_user_id_by_token(self, token: str) -> Optional[str]:
        db = SessionLocal()
        try:
            rec = db.query(B2CUserSession).filter(
                B2CUserSession.token_hash == _hash_token(token),
                B2CUserSession.is_revoked == False,
            ).first()
            if not rec:
                return None
            exp = rec.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                return None
            return rec.user_id
        finally:
            db.close()

    def revoke_session(self, token: str) -> None:
        db = SessionLocal()
        try:
            rec = db.query(B2CUserSession).filter(B2CUserSession.token_hash == _hash_token(token)).first()
            if rec:
                rec.is_revoked = True
                db.commit()
        finally:
            db.close()

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            rec = db.query(B2CUserProfile).filter(B2CUserProfile.user_id == user_id).first()
            if not rec:
                return dict(self.DEFAULT_PROFILE)
            return {**self.DEFAULT_PROFILE, **json.loads(rec.profile_json)}
        finally:
            db.close()

    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            current = self.get_profile(user_id)
            for k, v in updates.items():
                if v is not None:
                    current[k] = v
            now = datetime.now(timezone.utc)
            rec = B2CUserProfile(
                user_id=user_id,
                profile_json=json.dumps(current),
                consent_given=bool(current.get("consent_given", True)),
                consent_at=now,
                updated_at=now,
            )
            db.merge(rec)
            db.commit()
            return current
        finally:
            db.close()

    def delete_user_data(self, user_id: str) -> None:
        db = SessionLocal()
        try:
            db.query(B2CUserProfile).filter(B2CUserProfile.user_id == user_id).delete()
            db.query(B2CUserSession).filter(B2CUserSession.user_id == user_id).delete()
            db.commit()
        finally:
            db.close()

    def log_impact(self, user_id: str, action: str, saved_ug: float) -> None:
        pass

    def get_impact_logs(self, user_id: str) -> List[Dict[str, Any]]:
        return []


repo = PersistentB2CRepository()
