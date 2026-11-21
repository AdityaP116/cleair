from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import uuid

from app.models.work_orders import (
    WorkOrder,
    WorkOrderEvent,
    InterventionRecord,
    WorkOrderStatus,
    WorkOrderPriority,
    InterventionType
)
from app.models.alerts import Alert, AlertStatus

class WorkOrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_work_order(
        self,
        site_id: str,
        title: str,
        description: str,
        organization_id: str,
        zone_id: Optional[str] = None,
        alert_id: Optional[str] = None,
        priority: WorkOrderPriority = WorkOrderPriority.MEDIUM,
        assigned_to_user_id: Optional[str] = None,
        assigned_to_name: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
        due_at: Optional[datetime] = None,
        actor_name: str = "System"
    ) -> WorkOrder:
        status = WorkOrderStatus.ASSIGNED if assigned_to_name or assigned_to_user_id else WorkOrderStatus.OPEN

        wo = WorkOrder(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            site_id=site_id,
            zone_id=zone_id,
            alert_id=alert_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            assigned_to_user_id=assigned_to_user_id,
            assigned_to_name=assigned_to_name,
            created_by_user_id=created_by_user_id,
            due_at=due_at
        )
        self.db.add(wo)

        # Audit event
        event = WorkOrderEvent(
            id=str(uuid.uuid4()),
            work_order_id=wo.id,
            event_type="CREATED",
            from_status=None,
            to_status=status.value,
            actor_name=actor_name,
            notes=f"Work order created with priority {priority.value}"
        )
        self.db.add(event)

        # If created from an alert, update alert status to INVESTIGATING
        if alert_id:
            alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
            if alert and alert.status == AlertStatus.OPEN:
                alert.status = AlertStatus.INVESTIGATING

        self.db.commit()
        self.db.refresh(wo)
        return wo

    def assign_work_order(
        self,
        work_order_id: str,
        assigned_to_name: str,
        assigned_to_user_id: Optional[str] = None,
        actor_name: str = "Facility Manager"
    ) -> Optional[WorkOrder]:
        wo = self.db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not wo:
            return None

        old_status = wo.status.value
        wo.assigned_to_name = assigned_to_name
        wo.assigned_to_user_id = assigned_to_user_id
        if wo.status == WorkOrderStatus.OPEN:
            wo.status = WorkOrderStatus.ASSIGNED

        event = WorkOrderEvent(
            id=str(uuid.uuid4()),
            work_order_id=wo.id,
            event_type="ASSIGNED",
            from_status=old_status,
            to_status=wo.status.value,
            actor_name=actor_name,
            notes=f"Assigned to {assigned_to_name}"
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(wo)
        return wo

    def transition_status(
        self,
        work_order_id: str,
        new_status: WorkOrderStatus,
        actor_name: str,
        notes: Optional[str] = None,
        completion_notes: Optional[str] = None
    ) -> Optional[WorkOrder]:
        wo = self.db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
        if not wo:
            return None

        old_status = wo.status.value
        now = datetime.now(timezone.utc)

        if new_status == WorkOrderStatus.IN_PROGRESS and not wo.in_progress_at:
            wo.in_progress_at = now
        elif new_status == WorkOrderStatus.RESOLVED:
            wo.resolved_at = now
            if completion_notes:
                wo.completion_notes = completion_notes
            # If linked to alert, auto-resolve the alert if still open/investigating
            if wo.alert_id:
                alert = self.db.query(Alert).filter(Alert.id == wo.alert_id).first()
                if alert and alert.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING]:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = now
                    alert.resolved_by = actor_name
                    alert.resolution_notes = f"Resolved via Work Order {wo.id}: {completion_notes or 'Corrective intervention completed'}"

        wo.status = new_status

        event = WorkOrderEvent(
            id=str(uuid.uuid4()),
            work_order_id=wo.id,
            event_type="STATUS_CHANGE",
            from_status=old_status,
            to_status=new_status.value,
            actor_name=actor_name,
            notes=notes or completion_notes or f"Status changed to {new_status.value}"
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(wo)
        return wo

    def record_intervention(
        self,
        work_order_id: str,
        intervention_type: InterventionType,
        description: str,
        performed_by: str,
        site_id: str,
        zone_id: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> InterventionRecord:
        record = InterventionRecord(
            id=str(uuid.uuid4()),
            work_order_id=work_order_id,
            site_id=site_id,
            zone_id=zone_id,
            intervention_type=intervention_type,
            description=description,
            performed_by=performed_by,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            metadata_json=metadata_json or {}
        )
        self.db.add(record)

        event = WorkOrderEvent(
            id=str(uuid.uuid4()),
            work_order_id=work_order_id,
            event_type="INTERVENTION_RECORDED",
            from_status=None,
            to_status=None,
            actor_name=performed_by,
            notes=f"Logged intervention: {intervention_type.value} - {description}"
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_work_orders(
        self,
        site_id: str,
        status: Optional[WorkOrderStatus] = None
    ) -> List[WorkOrder]:
        q = self.db.query(WorkOrder).filter(WorkOrder.site_id == site_id)
        if status:
            q = q.filter(WorkOrder.status == status)
        return q.order_by(WorkOrder.created_at.desc()).all()

    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        return self.db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
