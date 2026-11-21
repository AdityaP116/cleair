from fastapi import Header, HTTPException
from typing import Optional
from app.repositories.memory import repo
import uuid

async def get_current_user_id(x_session_token: Optional[str] = Header(None)) -> str:
    if not x_session_token:
        # Default anonymous test user
        token = "default-session"
        user_id = "default-user"
        if not repo.get_user_id_by_token(token):
            repo.create_session(token, user_id)
        return user_id
    
    user_id = repo.get_user_id_by_token(x_session_token)
    if not user_id:
        user_id = "user-" + str(uuid.uuid4())[:8]
        repo.create_session(x_session_token, user_id)
    return user_id
