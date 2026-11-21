from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.models.work_orders import WorkOrderStatus, WorkOrderPriority, InterventionType
from app.modules.operations.work_orders import WorkOrderService

router = APIRouter(prefix="/work-orders", tags=["Work Orders & Interventions"])

class CreateWorkOrderRequest(BaseModel):
    site_id: str
    organization_id: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: str
    priority: WorkOrderPriority = WorkOrderPriority.MEDIUM
    zone_id: Optional[str] = None
    alert_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    due_at: Optional[datetime] = None
    actor_name: str = "Operator"

class AssignWorkOrderRequest(BaseModel):
    assigned_to_name: str
    assigned_to_user_id: Optional[str] = None
    actor_name: str = "Facility Manager"

class UpdateStatusRequest(BaseModel):
    status: WorkOrderStatus
    actor_name: str
    notes: Optional[str] = None
    completion_notes: Optional[str] = None

class RecordInterventionRequest(BaseModel):
    intervention_type: InterventionType
    description: str
    performed_by: str
    site_id: str
    zone_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

@router.post("", status_code=201)
def create_work_order(req: CreateWorkOrderRequest, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    org_id = req.organization_id
    if not org_id:
        from app.models.institutional import Site
        site = db.query(Site).filter(Site.id == req.site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        org_id = site.organization_id

    wo = service.create_work_order(
        site_id=req.site_id,
        organization_id=org_id,
        title=req.title,
        description=req.description,
        priority=req.priority,
        zone_id=req.zone_id,
        alert_id=req.alert_id,
        assigned_to_name=req.assigned_to_name,
        due_at=req.due_at,
        actor_name=req.actor_name
    )
    return {
        "id": wo.id,
        "site_id": wo.site_id,
        "title": wo.title,
        "priority": wo.priority.value,
        "status": wo.status.value,
        "assigned_to_name": wo.assigned_to_name,
        "created_at": wo.created_at.isoformat()
    }

@router.get("/site/{site_id}")
def list_site_work_orders(site_id: str, status: Optional[WorkOrderStatus] = None, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    orders = service.list_work_orders(site_id, status=status)
    return [
        {
            "id": o.id,
            "site_id": o.site_id,
            "zone_id": o.zone_id,
            "alert_id": o.alert_id,
            "title": o.title,
            "description": o.description,
            "priority": o.priority.value,
            "status": o.status.value,
            "assigned_to_name": o.assigned_to_name,
            "created_at": o.created_at.isoformat(),
            "resolved_at": o.resolved_at.isoformat() if o.resolved_at else None,
            "completion_notes": o.completion_notes,
            "events_count": len(o.events),
            "interventions_count": len(o.interventions)
        }
        for o in orders
    ]

@router.get("/{work_order_id}")
def get_work_order_details(work_order_id: str, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    o = service.get_work_order(work_order_id)
    if not o:
        raise HTTPException(status_code=404, detail="Work order not found")
    return {
        "id": o.id,
        "site_id": o.site_id,
        "zone_id": o.zone_id,
        "alert_id": o.alert_id,
        "title": o.title,
        "description": o.description,
        "priority": o.priority.value,
        "status": o.status.value,
        "assigned_to_name": o.assigned_to_name,
        "created_at": o.created_at.isoformat(),
        "in_progress_at": o.in_progress_at.isoformat() if o.in_progress_at else None,
        "resolved_at": o.resolved_at.isoformat() if o.resolved_at else None,
        "completion_notes": o.completion_notes,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "actor_name": e.actor_name,
                "notes": e.notes,
                "created_at": e.created_at.isoformat()
            }
            for e in o.events
        ],
        "interventions": [
            {
                "id": i.id,
                "intervention_type": i.intervention_type.value,
                "description": i.description,
                "performed_by": i.performed_by,
                "started_at": i.started_at.isoformat(),
                "completed_at": i.completed_at.isoformat(),
                "metadata_json": i.metadata_json
            }
            for i in o.interventions
        ]
    }

@router.post("/{work_order_id}/assign")
def assign_work_order(work_order_id: str, req: AssignWorkOrderRequest, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    wo = service.assign_work_order(
        work_order_id=work_order_id,
        assigned_to_name=req.assigned_to_name,
        assigned_to_user_id=req.assigned_to_user_id,
        actor_name=req.actor_name
    )
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return {
        "id": wo.id,
        "status": wo.status.value,
        "assigned_to_name": wo.assigned_to_name
    }

@router.post("/{work_order_id}/status")
def update_work_order_status(work_order_id: str, req: UpdateStatusRequest, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    wo = service.transition_status(
        work_order_id=work_order_id,
        new_status=req.status,
        actor_name=req.actor_name,
        notes=req.notes,
        completion_notes=req.completion_notes
    )
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return {
        "id": wo.id,
        "status": wo.status.value,
        "resolved_at": wo.resolved_at.isoformat() if wo.resolved_at else None,
        "completion_notes": wo.completion_notes
    }

@router.post("/{work_order_id}/interventions", status_code=201)
def record_intervention(work_order_id: str, req: RecordInterventionRequest, db: Session = Depends(get_db)):
    service = WorkOrderService(db)
    wo = service.get_work_order(work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    rec = service.record_intervention(
        work_order_id=work_order_id,
        intervention_type=req.intervention_type,
        description=req.description,
        performed_by=req.performed_by,
        site_id=req.site_id,
        zone_id=req.zone_id,
        metadata_json=req.metadata_json
    )
    return {
        "id": rec.id,
        "work_order_id": rec.work_order_id,
        "intervention_type": rec.intervention_type.value,
        "performed_by": rec.performed_by,
        "completed_at": rec.completed_at.isoformat()
    }

@router.get("/{work_order_id}/verification")
def get_work_order_verification(work_order_id: str, window_minutes: int = 60, db: Session = Depends(get_db)):
    from app.modules.operations.verification import VerificationAnalyticsService
    service = VerificationAnalyticsService(db)
    result = service.compute_work_order_verification(work_order_id=work_order_id, window_minutes=window_minutes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
