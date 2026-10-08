from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from app.core.security import require_role
from app.models.schemas import AuditLogResponse, StatsResponse
from app.services.audit_service import get_audit_logs, get_system_stats

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=AuditLogResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    action: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_role("admin")),
):
    entries, total = get_audit_logs(page=page, size=size, action=action)
    return AuditLogResponse(
        entries=entries,
        total=total,
        page=page,
        size=size,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    user: Dict[str, Any] = Depends(require_role("viewer")),
):
    return get_system_stats()
