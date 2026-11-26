from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.rbac import require_institutional_role, verify_site_ownership, InstitutionalContext
from app.models.institutional import RoleEnum
from app.modules.operations.reporting import InstitutionalReportingService

router = APIRouter(prefix="/reports", tags=["Institutional Reports & Compliance"])

@router.get("/site/{site_id}/summary")
def get_site_operations_summary(
    site_id: str,
    days: int = Query(7, ge=1, le=90),
    ctx: InstitutionalContext = Depends(require_institutional_role([RoleEnum.ADMIN, RoleEnum.FACILITY_STAFF, RoleEnum.VIEWER])),
    db: Session = Depends(get_db)
):
    verify_site_ownership(db, site_id, ctx.organization_id)
    service = InstitutionalReportingService(db)
    summary = service.generate_site_operations_summary(site_id=site_id, days=days)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary

@router.get("/site/{site_id}/export/csv")
def export_site_telemetry_csv(
    site_id: str,
    days: int = Query(7, ge=1, le=90),
    ctx: InstitutionalContext = Depends(require_institutional_role([RoleEnum.ADMIN, RoleEnum.FACILITY_STAFF, RoleEnum.VIEWER])),
    db: Session = Depends(get_db)
):
    verify_site_ownership(db, site_id, ctx.organization_id)
    service = InstitutionalReportingService(db)
    csv_content = service.export_telemetry_csv(site_id=site_id, days=days)
    filename = f"telemetry_{site_id[:8]}_{days}d.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
