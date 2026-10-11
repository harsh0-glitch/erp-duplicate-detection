import logging
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import (
    DashboardActivityResponse,
    DashboardOverviewResponse,
    DuplicateStatsResponse,
    ProductStatsResponse,
)
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


# ---------------------------------------------------------------------------
# GET /api/dashboard/overview
# ---------------------------------------------------------------------------
@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard overview statistics",
    description=(
        "Returns a single aggregated snapshot of product, duplicate detection, "
        "and bulk upload statistics. Suitable for an ERP dashboard overview panel."
    ),
)
def get_overview(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_overview()


# ---------------------------------------------------------------------------
# GET /api/dashboard/products
# ---------------------------------------------------------------------------
@router.get(
    "/products",
    response_model=ProductStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Product catalog statistics",
    description=(
        "Returns product distribution metrics including totals, active/inactive counts, "
        "top categories, and top brands."
    ),
)
def get_product_stats(
    category_limit: int = Query(20, ge=1, le=50, description="Max category groups to return"),
    brand_limit: int = Query(20, ge=1, le=50, description="Max brand groups to return"),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_product_stats(
        category_limit=category_limit,
        brand_limit=brand_limit,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/duplicates
# ---------------------------------------------------------------------------
@router.get(
    "/duplicates",
    response_model=DuplicateStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Duplicate detection statistics",
    description=(
        "Returns duplicate detection metrics including totals per status, confirmed, rejected, "
        "pending review counts, and recent detection activity."
    ),
)
def get_duplicate_stats(
    activity_limit: int = Query(10, ge=1, le=50, description="Number of recent duplicate runs to return"),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_duplicate_stats(activity_limit=activity_limit)


# ---------------------------------------------------------------------------
# GET /api/dashboard/activity
# ---------------------------------------------------------------------------
@router.get(
    "/activity",
    response_model=DashboardActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Recent system activity feed",
    description=(
        "Returns the latest system activity events drawn from the audit_logs table. "
        "Suitable for an activity timeline or feed widget. Returns up to 20 entries by default."
    ),
)
def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of recent events to return"),
    service: DashboardService = Depends(get_dashboard_service),
):
    return service.get_recent_activity(limit=limit)
