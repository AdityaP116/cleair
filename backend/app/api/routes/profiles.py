from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.api.dependencies import get_current_user_id
from app.repositories.memory import repo
from app.schemas import ProfileUpdate

router = APIRouter()

@router.get("")
def get_profile(user_id: str = Depends(get_current_user_id)):
    return repo.get_profile(user_id)

@router.put("")
def update_profile(update: ProfileUpdate, user_id: str = Depends(get_current_user_id)):
    return repo.update_profile(user_id, update.model_dump(exclude_unset=True))

@router.patch("")
def patch_profile(update: ProfileUpdate, user_id: str = Depends(get_current_user_id)):
    return repo.update_profile(user_id, update.model_dump(exclude_unset=True))

@router.delete("")
def delete_profile(user_id: str = Depends(get_current_user_id)):
    repo.delete_user_data(user_id)
    return {"deleted": True}
