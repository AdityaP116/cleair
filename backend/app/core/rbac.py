from dataclasses import dataclass
from typing import List, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.institutional import (
    InstitutionalUser,
    InstitutionalMembership,
    RoleEnum,
    Site,
)


@dataclass
class InstitutionalContext:
    user_id: str
    organization_id: str
    role: RoleEnum


def require_institutional_role(allowed_roles: List[RoleEnum]):
    def _dependency(
        x_institutional_user_id: Optional[str] = Header(None),
        db: Session = Depends(get_db),
    ) -> InstitutionalContext:
        if not x_institutional_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Institutional authentication required (missing x-institutional-user-id)",
            )

        user = (
            db.query(InstitutionalUser)
            .filter(
                InstitutionalUser.id == x_institutional_user_id,
                InstitutionalUser.is_active == True,
            )
            .first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or disabled institutional user",
            )

        membership = (
            db.query(InstitutionalMembership)
            .filter(
                InstitutionalMembership.user_id == user.id,
                InstitutionalMembership.is_active == True,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no active organization membership",
            )

        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{membership.role.value}' is not permitted for this operation",
            )

        return InstitutionalContext(
            user_id=user.id,
            organization_id=membership.organization_id,
            role=membership.role,
        )

    return _dependency


def verify_site_ownership(db: Session, site_id: str, organization_id: str) -> Site:
    site = db.query(Site).filter(Site.id == site_id, Site.is_deleted == False).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if site.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied: site belongs to another organization",
        )
    return site
