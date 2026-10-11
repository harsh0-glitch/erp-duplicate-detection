from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.audit import (
    ActivityFeedResponse,
    AuditLogListResponse,
    AuditLogResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/audit-logs", tags=["Audit & Activity Logs"])


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)


# ---------------------------------------------------------------------------
# GET /api/audit-logs — List and filter audit logs
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audit logs",
    description=(
        "Retrieve paginated system audit logs. Supports filtering by action, "
        "entity type, entity ID, user ID, and date range."
    ),
)
def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    action: Optional[str] = Query(None, description="Filter by action (e.g. PRODUCT_CREATED, DUPLICATE_CONFIRMED)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (PRODUCT, BULK_UPLOAD, DUPLICATE)"),
    entity_id: Optional[int] = Query(None, description="Filter by affected entity ID"),
    user_id: Optional[str] = Query(None, description="Filter by user or actor ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events after this ISO-8601 timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this ISO-8601 timestamp"),
    service: AuditService = Depends(get_audit_service),
):
    return service.list_audit_logs(
        page=page,
        page_size=page_size,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# GET /api/audit-logs/activity — Recent human-readable activity feed
# ---------------------------------------------------------------------------
@router.get(
    "/activity",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent activity feed",
    description="Retrieve recent human-readable activity events for dashboard widgets and activity streams.",
)
def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of recent activity entries to return"),
    entity_type: Optional[str] = Query(None, description="Optional entity category filter"),
    service: AuditService = Depends(get_audit_service),
):
    return service.get_activity_feed(limit=limit, entity_type=entity_type)


# ---------------------------------------------------------------------------
# GET /api/audit-logs/{log_id} — Single audit log details
# ---------------------------------------------------------------------------
@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single audit log entry",
    description="Fetch a specific audit log record by its ID. Returns 404 if not found.",
)
def get_audit_log(
    log_id: int,
    service: AuditService = Depends(get_audit_service),
):
    return service.get_audit_log(log_id)
