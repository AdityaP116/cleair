from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.modules.ingestion.open_meteo import mumbai_outdoor_adapter
from app.schemas.telemetry import ZoneStatusResponse

router = APIRouter()

@router.get("/sites/{site_id}/zones", response_model=List[ZoneStatusResponse])
def get_site_zones(site_id: str, db: Session = Depends(get_db)):
    repo = FacilityRepository(db)
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site ID '{site_id}' not found"
        )
    return repo.get_site_zones_status(site_id)

@router.get("/sites/{site_id}/outdoor")
async def get_site_outdoor_context(site_id: str, db: Session = Depends(get_db)):
    repo = FacilityRepository(db)
    site = repo.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    outdoor_data = await mumbai_outdoor_adapter.fetch_current_mumbai_outdoor(
        lat=site.latitude,
        lon=site.longitude
    )
    return outdoor_data
