from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import math

from app.models.work_orders import WorkOrder, InterventionRecord, WorkOrderStatus
from app.models.telemetry import SensorReading
from app.modules.ingestion.open_meteo import mumbai_outdoor_adapter

class VerificationAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def compute_work_order_verification(
        self,
        work_order_id: str,
        window_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Computes observed sensor measurements before and after an intervention
        within a configurable symmetric time window (default: 60 minutes).
        
        Epistemic Integrity Notice:
        Results represent strictly observed empirical associations and must be
        disclaimed as: "Observed change — not proof of causation".
        """
        wo = self.db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not wo:
            return {"error": "Work order not found"}

        if not wo.resolved_at and not wo.interventions:
            return {
                "work_order_id": wo.id,
                "status": wo.status.value,
                "verification_status": "PENDING_COMPLETION",
                "message": "Verification requires a completed intervention timestamp."
            }

        # Reference anchor timestamp: earliest intervention completion, or work order resolution
        if wo.interventions:
            anchor_time = wo.interventions[0].completed_at
            intervention_type = wo.interventions[0].intervention_type.value
            intervention_desc = wo.interventions[0].description
        else:
            anchor_time = wo.resolved_at
            intervention_type = "GENERAL_CORRECTIVE_ACTION"
            intervention_desc = wo.completion_notes or "Resolved"

        pre_start = anchor_time - timedelta(minutes=window_minutes)
        pre_end = anchor_time
        post_start = anchor_time
        post_end = anchor_time + timedelta(minutes=window_minutes)

        # Query zone readings if zone_id is present, otherwise site-wide readings
        pre_metrics = self._aggregate_readings(
            site_id=wo.site_id,
            zone_id=wo.zone_id,
            start_time=pre_start,
            end_time=pre_end
        )

        post_metrics = self._aggregate_readings(
            site_id=wo.site_id,
            zone_id=wo.zone_id,
            start_time=post_start,
            end_time=post_end
        )

        # Compute metric deltas
        comparison = {}
        for m_type in ["PM2.5", "CO2", "TEMP", "RH"]:
            pre_val = pre_metrics.get(m_type, {}).get("mean")
            post_val = post_metrics.get(m_type, {}).get("mean")
            unit = pre_metrics.get(m_type, {}).get("unit") or post_metrics.get(m_type, {}).get("unit")

            if pre_val is not None and post_val is not None:
                delta = round(post_val - pre_val, 2)
                pct_change = round(((post_val - pre_val) / pre_val) * 100, 1) if pre_val > 0 else 0.0
                comparison[m_type] = {
                    "unit": unit,
                    "pre_mean": pre_val,
                    "post_mean": post_val,
                    "delta": delta,
                    "percent_change": pct_change,
                    "direction": "REDUCTION" if delta < 0 else ("INCREASE" if delta > 0 else "NO_CHANGE")
                }
            elif pre_val is not None:
                comparison[m_type] = {
                    "unit": unit,
                    "pre_mean": pre_val,
                    "post_mean": None,
                    "message": "Insufficient post-intervention telemetry collected yet"
                }

        # Outdoor ambient reference at verification time (synchronous baseline fallback safe)
        outdoor_context = {
            "ambient_pm25": 58.5,
            "ambient_pm10": 105.0,
            "source": "Mumbai Regional Ambient Baseline (CPCB/SAFAR Normal)"
        }

        return {
            "work_order_id": wo.id,
            "title": wo.title,
            "zone_id": wo.zone_id,
            "anchor_timestamp": anchor_time.isoformat(),
            "window_minutes": window_minutes,
            "intervention": {
                "type": intervention_type,
                "description": intervention_desc
            },
            "metrics": comparison,
            "pre_window_samples": sum(m.get("sample_count", 0) for m in pre_metrics.values()),
            "post_window_samples": sum(m.get("sample_count", 0) for m in post_metrics.values()),
            "outdoor_context": outdoor_context,
            "epistemic_disclaimer": "Observed change — not proof of causation. Multi-factor environmental dynamics (meteorological pressure, ambient infiltration, human occupancy) may influence readings."
        }

    def _aggregate_readings(
        self,
        site_id: str,
        zone_id: Optional[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        q = self.db.query(
            SensorReading.measurement_type,
            SensorReading.measurement_unit,
            func.avg(SensorReading.measurement_value).label("mean"),
            func.min(SensorReading.measurement_value).label("min"),
            func.max(SensorReading.measurement_value).label("max"),
            func.count(SensorReading.id).label("count")
        ).filter(
            SensorReading.site_id == site_id,
            SensorReading.sensor_timestamp >= start_time,
            SensorReading.sensor_timestamp <= end_time,
            SensorReading.quality_status.in_(["VALID", "SUSPECT"])
        )

        if zone_id:
            q = q.filter(SensorReading.zone_id == zone_id)

        results = q.group_by(SensorReading.measurement_type, SensorReading.measurement_unit).all()

        aggregates = {}
        for row in results:
            aggregates[row.measurement_type] = {
                "unit": row.measurement_unit,
                "mean": round(float(row.mean), 1) if row.mean is not None else None,
                "min": round(float(row.min), 1) if row.min is not None else None,
                "max": round(float(row.max), 1) if row.max is not None else None,
                "sample_count": int(row.count)
            }
        return aggregates
