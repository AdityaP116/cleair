from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

AdviceLevel = Literal["NORMAL", "CAUTION", "HIGH", "SEVERE", "EMERGENCY"]
ConfidenceLevel = Literal["Low", "Medium", "High"]

class SessionCreateResponse(BaseModel):
    session_token: str
    user_id: str

class ProfileBase(BaseModel):
    city: Optional[str] = "Delhi"
    locality: Optional[str] = None
    geohash: Optional[str] = "ttnfv2"
    has_child: bool = False
    has_elderly: bool = False
    is_pregnant: bool = False
    has_respiratory_condition: bool = False
    has_heart_condition: bool = False
    commute_mode: Optional[str] = "two_wheeler"
    commute_minutes_per_day: Optional[int] = 45
    outdoor_work: bool = False
    home_size_sqm: Optional[float] = 25.0
    ceiling_height_m: Optional[float] = 2.7
    has_purifier: bool = True
    purifier_cadr_m3h: Optional[float] = 250.0
    has_ac: bool = True
    cooking_fuel: Optional[str] = "png"
    budget_tier: str = "low"
    language: str = "en"
    briefing_time: str = "06:30"

class ProfileUpdate(BaseModel):
    city: Optional[str] = None
    locality: Optional[str] = None
    geohash: Optional[str] = None
    has_child: Optional[bool] = None
    has_elderly: Optional[bool] = None
    is_pregnant: Optional[bool] = None
    has_respiratory_condition: Optional[bool] = None
    has_heart_condition: Optional[bool] = None
    commute_mode: Optional[str] = None
    commute_minutes_per_day: Optional[int] = None
    outdoor_work: Optional[bool] = None
    home_size_sqm: Optional[float] = None
    ceiling_height_m: Optional[float] = None
    has_purifier: Optional[bool] = None
    purifier_cadr_m3h: Optional[float] = None
    has_ac: Optional[bool] = None
    cooking_fuel: Optional[str] = None
    budget_tier: Optional[str] = None
    language: Optional[str] = None
    briefing_time: Optional[str] = None

class ProfileResponse(ProfileBase):
    user_id: str

class StationInfo(BaseModel):
    name: str
    distance_km: float
    source: str

class AirCurrentResponse(BaseModel):
    location: Dict[str, Any]
    aqi: int
    category: str
    dominant_pollutant: str
    pm25: float
    pm10: float
    no2: Optional[float] = None
    o3: Optional[float] = None
    so2: Optional[float] = None
    co: Optional[float] = None
    station: StationInfo
    confidence: ConfidenceLevel
    observed_at: str
    stale: bool

class ForecastPoint(BaseModel):
    valid_at: str
    aqi: int
    aqi_category: str
    pm25: float
    pm10: float
    wind_speed_ms: Optional[float] = None
    humidity_pct: Optional[float] = None
    temp_c: Optional[float] = None

class AirForecastResponse(BaseModel):
    geohash: str
    issued_at: str
    points: List[ForecastPoint]

class RiskAssessmentResponse(BaseModel):
    advice_level: AdviceLevel
    worst_aqi: int
    worst_category: str
    rule_id: str
    mandatory_actions: List[str]
    grap_stage: Optional[str] = None
    evaluated_at: str

class ImpactEstimateRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None

class ImpactResult(BaseModel):
    value: float
    unit: str
    before: Optional[float] = None
    after: Optional[float] = None
    reduction_pct: Optional[float] = None
    assumptions: List[str]
    confidence: ConfidenceLevel
    formula_id: str

class Citation(BaseModel):
    id: str
    title: str
    publisher: str
    url: str
    published: Optional[str] = None
    content_snippet: Optional[str] = None

class ActionRecommendation(BaseModel):
    title: str
    why: str
    impact: Optional[Dict[str, Any]] = None
    cost_tier: Optional[str] = "free"
    citations: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class AgentResponse(BaseModel):
    advice_level: AdviceLevel
    headline: str
    summary: str
    actions: List[ActionRecommendation]
    plan_blocks: Optional[List[Dict[str, Any]]] = None
    citations: List[Citation]
    uncertainty_note: Optional[str] = None
    disclaimer: str
    followups: Optional[List[str]] = None
    symptom_escalation: bool = False
    limited_mode: bool = False

class LogActionRequest(BaseModel):
    action_type: str
    params: Optional[Dict[str, Any]] = None

class LogActionResponse(BaseModel):
    success: bool
    exposure_delta_ugm3h: float
    co2_saved_kg: float
    clean_air_score: int
