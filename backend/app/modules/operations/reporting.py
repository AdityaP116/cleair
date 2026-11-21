from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
import io

from app.models.institutional import Site, Zone, Building, Floor
from app.models.telemetry import Sensor, SensorReading
from app.models.alerts import Alert, AlertStatus, AlertSeverity
from app.models.work_orders import WorkOrder, InterventionRecord, WorkOrderStatus

class InstitutionalReportingService:
    def __init__(self, db: Session):
        self.db = db

    def generate_site_operations_summary(self, site_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Generates an auditable institutional air-quality operations summary report.
        """
        site = self.db.query(Site).filter(Site.id == site_id).first()
        if not site:
            return {"error": "Site not found"}

        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        # 1. Physical zone & sensor monitoring coverage
        zones = self.db.query(Zone).join(Floor, Zone.floor_id == Floor.id).join(Building, Floor.building_id == Building.id).filter(
            Building.site_id == site_id,
            Zone.is_deleted == False
        ).all()
        total_zones = len(zones)
        zones_with_sensors = sum(1 for z in zones if len(z.sensors) > 0)
        coverage_pct = round((zones_with_sensors / total_zones) * 100, 1) if total_zones > 0 else 0.0

        # 2. Total telemetry ingestion volume
        total_readings = self.db.query(func.count(SensorReading.id)).filter(
            SensorReading.site_id == site_id,
            SensorReading.sensor_timestamp >= since
        ).scalar() or 0

        valid_readings = self.db.query(func.count(SensorReading.id)).filter(
            SensorReading.site_id == site_id,
            SensorReading.sensor_timestamp >= since,
            SensorReading.quality_status == "VALID"
        ).scalar() or 0

        data_integrity_pct = round((valid_readings / total_readings) * 100, 1) if total_readings > 0 else 100.0

        # 3. Alert metrics
        total_alerts = self.db.query(func.count(Alert.id)).filter(
            Alert.site_id == site_id,
            Alert.triggered_at >= since
        ).scalar() or 0

        resolved_alerts = self.db.query(func.count(Alert.id)).filter(
            Alert.site_id == site_id,
            Alert.triggered_at >= since,
            Alert.status == AlertStatus.RESOLVED
        ).scalar() or 0

        critical_alerts = self.db.query(func.count(Alert.id)).filter(
            Alert.site_id == site_id,
            Alert.triggered_at >= since,
            Alert.severity == AlertSeverity.CRITICAL
        ).scalar() or 0

        alert_resolution_rate_pct = round((resolved_alerts / total_alerts) * 100, 1) if total_alerts > 0 else 100.0

        # 4. Corrective actions & work orders
        work_orders = self.db.query(WorkOrder).filter(
            WorkOrder.site_id == site_id,
            WorkOrder.created_at >= since
        ).all()
        total_work_orders = len(work_orders)
        completed_work_orders = sum(1 for w in work_orders if w.status == WorkOrderStatus.RESOLVED)

        interventions = self.db.query(InterventionRecord).filter(
            InterventionRecord.site_id == site_id,
            InterventionRecord.completed_at >= since
        ).all()

        intervention_breakdown = {}
        for i in interventions:
            key = i.intervention_type.value
            intervention_breakdown[key] = intervention_breakdown.get(key, 0) + 1

        # 5. Zone air quality performance
        zone_performance = []
        for z in zones:
            pm25_avg = self.db.query(func.avg(SensorReading.measurement_value)).filter(
                SensorReading.zone_id == z.id,
                SensorReading.measurement_type == "PM2.5",
                SensorReading.sensor_timestamp >= since,
                SensorReading.quality_status == "VALID"
            ).scalar()

            co2_avg = self.db.query(func.avg(SensorReading.measurement_value)).filter(
                SensorReading.zone_id == z.id,
                SensorReading.measurement_type == "CO2",
                SensorReading.sensor_timestamp >= since,
                SensorReading.quality_status == "VALID"
            ).scalar()

            zone_performance.append({
                "zone_id": z.id,
                "name": z.name,
                "zone_type": z.zone_type.value if hasattr(z.zone_type, "value") else str(z.zone_type),
                "target_pm25_max": z.target_pm25_max,
                "observed_pm25_mean": round(float(pm25_avg), 1) if pm25_avg is not None else None,
                "target_co2_max": z.target_co2_max,
                "observed_co2_mean": round(float(co2_avg), 1) if co2_avg is not None else None,
                "pm25_compliant": (pm25_avg <= z.target_pm25_max) if pm25_avg is not None else True,
                "co2_compliant": (co2_avg <= z.target_co2_max) if co2_avg is not None else True
            })

        return {
            "site_id": site.id,
            "site_name": site.name,
            "city": site.city,
            "report_period_days": days,
            "generated_at": now.isoformat(),
            "monitoring_coverage": {
                "total_zones": total_zones,
                "instrumented_zones": zones_with_sensors,
                "coverage_percent": coverage_pct
            },
            "telemetry_volume": {
                "total_readings": total_readings,
                "valid_readings": valid_readings,
                "data_integrity_percent": data_integrity_pct
            },
            "alerts_summary": {
                "total_triggered": total_alerts,
                "critical_count": critical_alerts,
                "resolved_count": resolved_alerts,
                "resolution_rate_percent": alert_resolution_rate_pct
            },
            "operations_and_interventions": {
                "total_work_orders": total_work_orders,
                "completed_work_orders": completed_work_orders,
                "total_physical_interventions": len(interventions),
                "interventions_by_type": intervention_breakdown
            },
            "zone_compliance": zone_performance
        }

    def export_telemetry_csv(self, site_id: str, days: int = 7) -> str:
        """
        Exports clean, auditable CSV stream of all sensor telemetry within time window.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        readings = self.db.query(
            SensorReading.sensor_timestamp,
            SensorReading.zone_id,
            SensorReading.sensor_id,
            SensorReading.measurement_type,
            SensorReading.measurement_value,
            SensorReading.measurement_unit,
            SensorReading.quality_status,
            SensorReading.provenance
        ).filter(
            SensorReading.site_id == site_id,
            SensorReading.sensor_timestamp >= since
        ).order_by(SensorReading.sensor_timestamp.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp_UTC",
            "Zone_ID",
            "Sensor_ID",
            "Measurement_Type",
            "Value",
            "Unit",
            "Quality_Status",
            "Provenance"
        ])

        for r in readings:
            writer.writerow([
                r.sensor_timestamp.isoformat() if r.sensor_timestamp else "",
                r.zone_id or "",
                r.sensor_id or "",
                r.measurement_type,
                r.measurement_value,
                r.measurement_unit,
                r.quality_status,
                r.provenance
            ])

        return output.getvalue()
