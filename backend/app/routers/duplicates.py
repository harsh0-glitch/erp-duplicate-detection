import logging
from typing import Optional
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.duplicate import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateReviewRequest,
    DuplicateDecisionResponse,
    DuplicateDetailResponse,
    DuplicateHistoryResponse,
)
from app.services.duplicate_service import DuplicateDetectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/duplicates", tags=["Duplicate Detection"])


def get_duplicate_service(db: Session = Depends(get_db)) -> DuplicateDetectionService:
    """Dependency provider for DuplicateDetectionService."""
    return DuplicateDetectionService(db=db)


# ---------------------------------------------------------------------------
# POST /api/duplicates/check — Detection Endpoint (Stage 6)
# ---------------------------------------------------------------------------
@router.post(
    "/check",
    response_model=DuplicateCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check product for duplicates",
    description=(
        "Submit a product payload to check for potential duplicates in the catalog. "
        "The endpoint queries candidate products from PostgreSQL and prepares data for ML inference. "
        "While the ML model is under development, returns a clear status indicating model availability "
        "without generating fake predictions."
    ),
)
def check_duplicate(
    payload: DuplicateCheckRequest,
    threshold: float = Query(
        0.80,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold to flag as duplicate",
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=50,
        description="Maximum number of top matching products to return",
    ),
    service: DuplicateDetectionService = Depends(get_duplicate_service),
):
    return service.check_duplicate(
        payload=payload,
        threshold=threshold,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# GET /api/duplicates/history — Detection History (Stage 7)
# ---------------------------------------------------------------------------
@router.get(
    "/history",
    response_model=DuplicateHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get duplicate detection history",
    description=(
        "Retrieve paginated history of past duplicate detection runs and suspected matches. "
        "Supports filtering by detection status (e.g. `COMPLETED`, `MODEL_UNAVAILABLE`), "
        "review decision (`CONFIRMED`, `REJECTED`, `PENDING`), query product ID, "
        "and minimum similarity score."
    ),
)
def get_duplicate_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: Optional[str] = Query(None, description="Filter by run status (e.g. COMPLETED, MODEL_UNAVAILABLE)"),
    decision: Optional[str] = Query(None, description="Filter by review decision (CONFIRMED, REJECTED, PENDING)"),
    query_product_id: Optional[int] = Query(None, description="Filter by query product ID"),
    min_similarity: Optional[float] = Query(None, ge=0.0, le=1.0, description="Filter by minimum similarity score"),
    service: DuplicateDetectionService = Depends(get_duplicate_service),
):
    return service.get_history(
        page=page,
        page_size=page_size,
        status_filter=status,
        decision_filter=decision,
        query_product_id=query_product_id,
        min_similarity=min_similarity,
    )


# ---------------------------------------------------------------------------
# POST /api/duplicates/{duplicate_id}/confirm — Confirm Duplicate (Stage 7)
# ---------------------------------------------------------------------------
@router.post(
    "/{duplicate_id}/confirm",
    response_model=DuplicateDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm suspected duplicate",
    description=(
        "Mark a suspected duplicate match as CONFIRMED. "
        "Stores the reviewer's decision, optional comment/reason, and decision timestamp."
    ),
)
def confirm_duplicate(
    duplicate_id: int,
    payload: Optional[DuplicateReviewRequest] = Body(None),
    service: DuplicateDetectionService = Depends(get_duplicate_service),
):
    return service.confirm_duplicate(
        duplicate_id=duplicate_id,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# POST /api/duplicates/{duplicate_id}/reject — Reject Duplicate (Stage 7)
# ---------------------------------------------------------------------------
@router.post(
    "/{duplicate_id}/reject",
    response_model=DuplicateDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject suspected duplicate",
    description=(
        "Mark a suspected duplicate match as REJECTED (distinct product). "
        "Stores the reviewer's decision, optional comment/reason, and decision timestamp."
    ),
)
def reject_duplicate(
    duplicate_id: int,
    payload: Optional[DuplicateReviewRequest] = Body(None),
    service: DuplicateDetectionService = Depends(get_duplicate_service),
):
    return service.reject_duplicate(
        duplicate_id=duplicate_id,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# GET /api/duplicates/{duplicate_id} — Get Duplicate Details (Stage 7)
# ---------------------------------------------------------------------------
@router.get(
    "/{duplicate_id}",
    response_model=DuplicateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get duplicate record details",
    description=(
        "Retrieve detailed information for a specific duplicate candidate match or detection run. "
        "Returns input specifications, candidate comparison details, similarity scores, and review decision."
    ),
)
def get_duplicate_details(
    duplicate_id: int,
    service: DuplicateDetectionService = Depends(get_duplicate_service),
):
    return service.get_duplicate(duplicate_id=duplicate_id)
