from fastapi import APIRouter, Query
from typing import Optional
from app.modules.air_quality.service import air_service

router = APIRouter()

@router.get("/forecast")
def get_forecast(lat: Optional[float] = 28.6139, lon: Optional[float] = 77.2090, hours: int = 48):
    return air_service.get_forecast(lat, lon, hours)
