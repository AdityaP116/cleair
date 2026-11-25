from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo
from app.modules.ai.orchestrator import orchestrator
from app.modules.air_quality.service import air_service
from app.schemas import ChatRequest

router = APIRouter()

@router.post("")
def chat_turn(req: ChatRequest, user_id: str = Depends(get_current_user_id)):
    profile = repo.get_profile(user_id)
    lat = profile.get("lat", 19.0760 if profile.get("city") == "Mumbai" else 28.6139)
    lon = profile.get("lon", 72.8777 if profile.get("city") == "Mumbai" else 77.2090)
    air_reading = air_service.get_current(lat, lon)
    return orchestrator.process_turn(
        message=req.message,
        profile=profile,
        current_aqi=air_reading["aqi"],
        air_reading=air_reading,
    )
