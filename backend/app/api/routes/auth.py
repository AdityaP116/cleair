from fastapi import APIRouter
from app.repositories.memory import repo
import uuid

router = APIRouter()

@router.post("/session")
def create_session():
    token = "sess-" + str(uuid.uuid4())
    user_id = "user-" + str(uuid.uuid4())[:8]
    repo.create_session(token, user_id)
    return {"session_token": token, "user_id": user_id}
