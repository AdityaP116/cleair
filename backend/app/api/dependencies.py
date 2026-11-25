from fastapi import Header, HTTPException
from typing import Optional
from app.repositories.memory import repo
import uuid

async def get_current_user_id(x_session_token: Optional[str] = Header(None)) -> str:
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Authentication required: missing x-session-token")
    
    user_id = repo.get_user_id_by_token(x_session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return user_id
