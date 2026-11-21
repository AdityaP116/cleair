from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo
from app.modules.ai.orchestrator import orchestrator
from app.schemas import ChatRequest

router = APIRouter()

@router.post("")
def chat_turn(req: ChatRequest, user_id: str = Depends(get_current_user_id)):
    profile = repo.get_profile(user_id)
    return orchestrator.process_turn(
        message=req.message,
        profile=profile,
        current_aqi=348
    )
