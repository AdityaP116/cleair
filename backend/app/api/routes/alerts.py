from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.alerts import AlertRule, AlertSeverity
from app.modules.alerts.engine import AlertEngineService
from app.repositories.facilities import FacilityRepository
from app.schemas.alerts import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertResponse,
    AlertAcknowledgeRequest,
    AlertResolveRequest
)

router = APIRouter()

@router.post("/rules", response_model=AlertRuleResponse)
def create_alert_rule(rule_in: AlertRuleCreate, db: Session = Depends(get_db)):
    repo = FacilityRepository(db)
    org = repo.get_or_create_pilot_organization()

    rule = AlertRule(
        organization_id=org.id,
        site_id=rule_in.site_id,
        name=rule_in.name,
        measurement_type=rule_in.measurement_type.upper(),
        operator=rule_in.operator,
        threshold_value=rule_in.threshold_value,
        threshold_unit=rule_in.threshold_unit,
        severity=rule_in.severity,
        averaging_window_min=rule_in.averaging_window_min,
        rationale=rule_in.rationale,
        is_active=True
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.get("/rules", response_model=List[AlertRuleResponse])
def list_alert_rules(db: Session = Depends(get_db)):
    rules = db.query(AlertRule).filter(AlertRule.is_active == True).all()
    return rules

@router.get("/site/{site_id}", response_model=List[AlertResponse])
def get_site_alerts(site_id: str, db: Session = Depends(get_db)):
    engine_svc = AlertEngineService(db)
    alerts = engine_svc.get_site_alerts(site_id)
    out = []
    for a in alerts:
        zone_name = a.rule.name if a.rule else "Zone"
        if a.zone_id:
            from app.models.institutional import Zone
            z = db.get(Zone, a.zone_id)
            if z:
                zone_name = z.name

        out.append(AlertResponse(
            id=a.id,
            rule_id=a.rule_id,
            site_id=a.site_id,
            zone_id=a.zone_id,
            zone_name=zone_name,
            title=a.title,
            description=a.description,
            measurement_type=a.measurement_type,
            observed_value=a.observed_value,
            threshold_value=a.threshold_value,
            severity=a.severity,
            status=a.status,
            triggered_at=a.triggered_at,
            acknowledged_at=a.acknowledged_at,
            acknowledged_by=a.acknowledged_by,
            resolved_at=a.resolved_at
        ))
    return out

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: str, req: AlertAcknowledgeRequest, db: Session = Depends(get_db)):
    engine_svc = AlertEngineService(db)
    alert = engine_svc.acknowledge_alert(alert_id, req.acknowledged_by, req.notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.commit()
    return AlertResponse(
        id=alert.id,
        rule_id=alert.rule_id,
        site_id=alert.site_id,
        zone_id=alert.zone_id,
        zone_name="Zone",
        title=alert.title,
        description=alert.description,
        measurement_type=alert.measurement_type,
        observed_value=alert.observed_value,
        threshold_value=alert.threshold_value,
        severity=alert.severity,
        status=alert.status,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at
    )

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: str, req: AlertResolveRequest, db: Session = Depends(get_db)):
    engine_svc = AlertEngineService(db)
    alert = engine_svc.resolve_alert(alert_id, req.resolved_by, req.resolution_notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.commit()
    return AlertResponse(
        id=alert.id,
        rule_id=alert.rule_id,
        site_id=alert.site_id,
        zone_id=alert.zone_id,
        zone_name="Zone",
        title=alert.title,
        description=alert.description,
        measurement_type=alert.measurement_type,
        observed_value=alert.observed_value,
        threshold_value=alert.threshold_value,
        severity=alert.severity,
        status=alert.status,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        resolved_at=alert.resolved_at
    )
