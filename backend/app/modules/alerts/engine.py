from sqlalchemy.orm import Session
from sqlalchemy import select, update, desc
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.models.alerts import AlertRule, Alert, AlertEvent, AlertSeverity, AlertStatus
from app.models.telemetry import SensorReading, Sensor
from app.models.institutional import Zone

class AlertEngineService:
    def __init__(self, session: Session):
        self.session = session

    def evaluate_reading_against_rules(self, reading: SensorReading) -> List[Alert]:
        """
        Evaluates a newly ingested reading against active AlertRules.
        Implements alert deduplication: if an alert for this rule and zone is already OPEN or INVESTIGATING,
        do not flood with duplicate alerts.
        """
        stmt = select(AlertRule).where(
            AlertRule.is_active == True,
            AlertRule.measurement_type == reading.measurement_type
        )
        rules = self.session.execute(stmt).scalars().all()
        created_alerts = []

        for rule in rules:
            # Check site specificity if rule is bound to a specific site
            if rule.site_id and rule.site_id != reading.site_id:
                continue

            is_triggered = False
            if rule.operator == ">" and reading.measurement_value > rule.threshold_value:
                is_triggered = True
            elif rule.operator == ">=" and reading.measurement_value >= rule.threshold_value:
                is_triggered = True
            elif rule.operator == "<" and reading.measurement_value < rule.threshold_value:
                is_triggered = True
            elif rule.operator == "<=" and reading.measurement_value <= rule.threshold_value:
                is_triggered = True

            if is_triggered:
                # Deduplication check: Is there an existing OPEN or ACKNOWLEDGED alert for this rule & zone?
                existing_stmt = select(Alert).where(
                    Alert.rule_id == rule.id,
                    Alert.zone_id == reading.zone_id,
                    Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING])
                )
                existing = self.session.execute(existing_stmt).scalar_one_or_none()
                if existing:
                    # Update observed value without creating duplicate alert storm
                    existing.observed_value = reading.measurement_value
                    continue

                zone_name = "Zone"
                if reading.zone_id:
                    z = self.session.get(Zone, reading.zone_id)
                    if z:
                        zone_name = z.name

                alert = Alert(
                    rule_id=rule.id,
                    organization_id=rule.organization_id,
                    site_id=reading.site_id,
                    zone_id=reading.zone_id,
                    sensor_id=reading.sensor_id,
                    title=f"{rule.name} in {zone_name}",
                    description=f"{reading.measurement_type} observed at {reading.measurement_value} {reading.measurement_unit}, exceeding threshold of {rule.threshold_value} {rule.threshold_unit}.",
                    measurement_type=reading.measurement_type,
                    observed_value=reading.measurement_value,
                    threshold_value=rule.threshold_value,
                    severity=rule.severity,
                    status=AlertStatus.OPEN
                )
                self.session.add(alert)
                self.session.flush()

                # Add initial audit event
                event = AlertEvent(
                    alert_id=alert.id,
                    from_status="NONE",
                    to_status=AlertStatus.OPEN.value,
                    performed_by="SYSTEM_DETECTOR",
                    notes="Deterministic threshold violation detected"
                )
                self.session.add(event)
                created_alerts.append(alert)

        return created_alerts

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: Optional[str] = None) -> Optional[Alert]:
        alert = self.session.get(Alert, alert_id)
        if not alert:
            return None
        
        old_status = alert.status.value
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by

        event = AlertEvent(
            alert_id=alert.id,
            from_status=old_status,
            to_status=AlertStatus.ACKNOWLEDGED.value,
            performed_by=acknowledged_by,
            notes=notes or "Acknowledged by operations staff"
        )
        self.session.add(event)
        self.session.flush()
        return alert

    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str) -> Optional[Alert]:
        alert = self.session.get(Alert, alert_id)
        if not alert:
            return None

        old_status = alert.status.value
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = resolution_notes

        event = AlertEvent(
            alert_id=alert.id,
            from_status=old_status,
            to_status=AlertStatus.RESOLVED.value,
            performed_by=resolved_by,
            notes=resolution_notes
        )
        self.session.add(event)
        self.session.flush()
        return alert

    def get_site_alerts(self, site_id: str, limit: int = 50) -> List[Alert]:
        stmt = select(Alert).where(
            Alert.site_id == site_id
        ).order_by(desc(Alert.triggered_at)).limit(limit)
        return self.session.execute(stmt).scalars().all()
