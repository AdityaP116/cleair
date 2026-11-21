from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.repositories.facilities import FacilityRepository
from app.schemas.telemetry import (
    TelemetryIngestPayload,
    TelemetryIngestResponse,
    IngestionResultItem,
    SensorStatusResponse
)

router = APIRouter()

@router.post("/ingest", response_model=TelemetryIngestResponse)
def ingest_telemetry(
    payload: TelemetryIngestPayload,
    x_sensor_key: str = Header(..., description="High-entropy sensor ingestion credential"),
    db: Session = Depends(get_db)
):
    repo = FacilityRepository(db)
    
    # 1. Fetch sensor record
    sensor = repo.get_sensor(payload.sensor_id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor ID '{payload.sensor_id}' not found or decommissioned"
        )

    # 2. Authenticate sensor token with constant-time check
    is_authenticated = repo.authenticate_sensor(sensor.id, x_sensor_key)
    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, revoked, or missing sensor credential"
        )

    # Determine site & zone context
    zone_id = sensor.zone_id
    site_id = None
    if sensor.zone and sensor.zone.floor and sensor.zone.floor.building:
        site_id = sensor.zone.floor.building.site_id
    else:
        # Default to primary organization site if unlinked
        org = repo.get_or_create_pilot_organization()
        if org.sites:
            site_id = org.sites[0].id
        else:
            site = repo.create_site(org.id)
            site_id = site.id

    recorded_items = []
    any_duplicate = False

    # 3. Process each measurement under composite idempotency
    for m in payload.measurements:
        reading_key = f"{payload.idempotency_key}_{m.type}"
        reading, was_created = repo.ingest_reading(
            sensor_id=sensor.id,
            site_id=site_id,
            zone_id=zone_id,
            measurement_type=m.type,
            measurement_value=m.value,
            sensor_timestamp=payload.timestamp,
            idempotency_key=reading_key,
            provenance=payload.provenance or "MEASURED",
            raw_payload=payload.raw_metadata
        )
        if not was_created:
            any_duplicate = True
        else:
            # Phase 4: Trigger operational alert evaluation on new readings
            from app.modules.alerts.engine import AlertEngineService
            alert_engine = AlertEngineService(db)
            alert_engine.evaluate_reading_against_rules(reading)

        recorded_items.append(IngestionResultItem(
            measurement_type=reading.measurement_type,
            value=reading.measurement_value,
            unit=reading.measurement_unit,
            quality_status=reading.quality_status
        ))

    db.commit()

    return TelemetryIngestResponse(
        success=True,
        sensor_id=sensor.id,
        readings_recorded=len(recorded_items),
        was_duplicate=any_duplicate,
        results=recorded_items
    )

@router.get("/sensors/{sensor_id}/status", response_model=SensorStatusResponse)
def get_sensor_status(sensor_id: str, db: Session = Depends(get_db)):
    repo = FacilityRepository(db)
    sensor = repo.get_sensor(sensor_id)
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor ID '{sensor_id}' not found"
        )

    freshness = repo.calculate_sensor_freshness(sensor.last_seen_at, sensor.expected_interval_sec)
    zone_name = sensor.zone.name if sensor.zone else None

    return SensorStatusResponse(
        sensor_id=sensor.id,
        serial_number=sensor.serial_number,
        model=sensor.model,
        zone_id=sensor.zone_id,
        zone_name=zone_name,
        freshness=freshness,
        last_seen_at=sensor.last_seen_at,
        expected_interval_sec=sensor.expected_interval_sec
    )
