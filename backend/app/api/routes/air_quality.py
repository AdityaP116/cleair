from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.modules.air_quality.service import air_service
from app.modules.safety.rules import safety_engine
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo

router = APIRouter()

@router.get("/current")
def get_current(
    lat: float = Query(28.6139, ge=-90.0, le=90.0),
    lon: float = Query(77.2090, ge=-180.0, le=180.0),
):
    return air_service.get_current(lat, lon)

@router.get("/risk")
def get_risk(user_id: str = Depends(get_current_user_id)):
    profile = repo.get_profile(user_id)
    lang = profile.get("language", "en")
    curr = air_service.get_current()
    risk = safety_engine.evaluate(worst_aqi=curr["aqi"], profile=profile, lang=lang)
    return risk
