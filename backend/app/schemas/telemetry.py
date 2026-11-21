from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

class SingleMeasurement(BaseModel):
    type: str # PM2.5, PM10, CO2, TEMP, RH
    value: float
    unit: Optional[str] = None

class TelemetryIngestPayload(BaseModel):
    sensor_id: str
    idempotency_key: str
    timestamp: datetime
    measurements: List[SingleMeasurement]
    provenance: Optional[Literal["MEASURED", "SIMULATED", "ESTIMATED"]] = "MEASURED"
    raw_metadata: Optional[Dict[str, Any]] = None

class IngestionResultItem(BaseModel):
    measurement_type: str
    value: float
    unit: str
    quality_status: str

class TelemetryIngestResponse(BaseModel):
    success: bool
    sensor_id: str
    readings_recorded: int
    was_duplicate: bool
    results: List[IngestionResultItem]

class SensorStatusResponse(BaseModel):
    sensor_id: str
    serial_number: str
    model: str
    zone_id: Optional[str]
    zone_name: Optional[str]
    freshness: Literal["ONLINE", "STALE", "OFFLINE", "UNKNOWN"]
    last_seen_at: Optional[datetime]
    expected_interval_sec: int

class ZoneReadingSummary(BaseModel):
    measurement_type: str
    value: float
    unit: str
    quality_status: str
    provenance: str
    timestamp: datetime

class ZoneStatusResponse(BaseModel):
    zone_id: str
    name: str
    zone_type: str
    building_name: str
    floor_number: int
    target_co2_max: float
    target_pm25_max: float
    sensor_status: Optional[str]
    latest_readings: List[ZoneReadingSummary]
