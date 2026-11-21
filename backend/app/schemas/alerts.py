from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.alerts import AlertSeverity, AlertStatus

class AlertRuleCreate(BaseModel):
    name: str
    measurement_type: str # PM2.5, CO2, etc.
    operator: str = ">"
    threshold_value: float
    threshold_unit: str
    severity: AlertSeverity = AlertSeverity.WARNING
    averaging_window_min: int = 15
    rationale: Optional[str] = None
    site_id: Optional[str] = None

class AlertRuleResponse(AlertRuleCreate):
    id: str
    organization_id: str
    is_active: bool
    created_at: datetime

class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None

class AlertResolveRequest(BaseModel):
    resolved_by: str
    resolution_notes: str

class AlertResponse(BaseModel):
    id: str
    rule_id: str
    site_id: str
    zone_id: Optional[str]
    zone_name: Optional[str]
    title: str
    description: str
    measurement_type: str
    observed_value: float
    threshold_value: float
    severity: AlertSeverity
    status: AlertStatus
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
