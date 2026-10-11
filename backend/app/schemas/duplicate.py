from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Duplicate Detection Request & Match Schemas (Stage 6)
# ---------------------------------------------------------------------------

class DuplicateCheckRequest(BaseModel):
    """Product payload submitted for duplicate checking."""
    sku: str = Field(..., min_length=1, max_length=100, description="Product SKU / code to check")
    name: str = Field(..., min_length=1, max_length=255, description="Product title / name")
    description: Optional[str] = Field(None, description="Product description")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    category: Optional[str] = Field(None, max_length=100, description="Primary product category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Product subcategory")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measure (e.g., pcs, box, kg)")
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible key-value attributes for product specifications",
    )
    product_id: Optional[int] = Field(
        None,
        description="Optional existing database ID if checking an already persisted product",
    )


class MatchedProductDetails(BaseModel):
    """Core product details of a candidate match for side-by-side comparison."""
    id: int = Field(..., description="Matched product database ID")
    sku: str = Field(..., description="Matched product SKU")
    name: str = Field(..., description="Matched product title")
    brand: Optional[str] = Field(None, description="Matched product brand")
    category: Optional[str] = Field(None, description="Matched product category")
    subcategory: Optional[str] = Field(None, description="Matched product subcategory")
    unit: Optional[str] = Field(None, description="Matched product unit")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Matched product attributes")
    is_active: bool = Field(True, description="Whether the matched product is currently active")

    model_config = ConfigDict(from_attributes=True)


class DuplicateMatchItem(BaseModel):
    """A single candidate duplicate match returned by the detection engine."""
    matched_product_id: int = Field(..., description="ID of the matching product in the database")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score between 0.0 and 1.0")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence score")
    rank: int = Field(..., ge=1, description="Ranking position of this match (1 = closest match)")
    matching_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of matching features / explainability (e.g. name similarity, brand match)",
    )
    matched_product: Optional[MatchedProductDetails] = Field(
        None,
        description="Full product specifications of the matched item for comparison",
    )


class DuplicateCheckResponse(BaseModel):
    """Response returned by the duplicate check API."""
    status: str = Field(
        ...,
        description="Detection status: 'completed', 'model_unavailable', or 'failed'",
        examples=["model_unavailable", "completed"],
    )
    is_duplicate_detected: Optional[bool] = Field(
        None,
        description="True if similarity exceeds threshold, False if distinct, None if model unavailable",
    )
    confidence_score: Optional[float] = Field(
        None,
        description="Overall confidence score of duplicate determination",
    )
    model_version: Optional[str] = Field(
        None,
        description="Identifier of the model used, or None if no model is loaded",
    )
    message: str = Field(
        ...,
        description="Human-readable status or integration message",
    )
    detection_run_id: Optional[int] = Field(
        None,
        description="Unique ID of the detection run logged in the database, if recorded",
    )
    total_candidates_analyzed: int = Field(
        0,
        description="Number of catalog candidate products considered",
    )
    matches: List[DuplicateMatchItem] = Field(
        default_factory=list,
        description="Top matching candidate products ordered by similarity score",
    )


# ---------------------------------------------------------------------------
# Duplicate Review & Decision Schemas (Stage 7)
# ---------------------------------------------------------------------------

class DuplicateReviewRequest(BaseModel):
    """Optional review payload when confirming or rejecting a duplicate."""
    reviewer_id: Optional[str] = Field(None, max_length=100, description="Reviewer identifier or username")
    reason: Optional[str] = Field(None, description="Optional explanation, decision reason, or comment")


class DuplicateReviewResponse(BaseModel):
    """Review decision record."""
    id: int = Field(..., description="Review ID")
    candidate_id: int = Field(..., description="Associated candidate duplicate ID")
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")
    decision: str = Field(..., description="Decision: 'CONFIRMED' or 'REJECTED'")
    reason: Optional[str] = Field(None, description="Optional explanation or reason")
    created_at: datetime = Field(..., description="Timestamp when decision was first recorded")
    updated_at: datetime = Field(..., description="Timestamp when decision was last updated")

    model_config = ConfigDict(from_attributes=True)


class DuplicateDecisionResponse(BaseModel):
    """Response returned after confirming or rejecting a duplicate."""
    message: str = Field(..., description="Status message")
    duplicate_id: int = Field(..., description="ID of the reviewed duplicate candidate")
    decision: str = Field(..., description="Recorded decision: 'CONFIRMED' or 'REJECTED'")
    review: DuplicateReviewResponse = Field(..., description="Detailed review record")


# ---------------------------------------------------------------------------
# Duplicate History & Detail Schemas (Stage 7)
# ---------------------------------------------------------------------------

class DuplicateMatchHistoryItem(BaseModel):
    """Candidate match summary for history listing."""
    id: int = Field(..., description="Duplicate candidate match ID")
    matched_product_id: Optional[int] = Field(None, description="Matched catalog product ID")
    matched_product_sku: Optional[str] = Field(None, description="Matched product SKU")
    matched_product_name: Optional[str] = Field(None, description="Matched product name")
    similarity_score: float = Field(..., description="Similarity score between 0.0 and 1.0")
    confidence_score: Optional[float] = Field(None, description="Model confidence score")
    rank: int = Field(..., description="Rank position of the match")
    matching_features: Dict[str, Any] = Field(default_factory=dict, description="Feature breakdown")
    review_status: str = Field(..., description="'CONFIRMED', 'REJECTED', or 'PENDING'")
    review_decision: Optional[str] = Field(None, description="Recorded decision, if reviewed")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    reviewer_id: Optional[str] = Field(None, description="Reviewer ID")


class DuplicateHistoryItem(BaseModel):
    """Detection run record in history listing."""
    id: int = Field(..., description="Detection run ID")
    status: str = Field(..., description="Run status: 'COMPLETED', 'MODEL_UNAVAILABLE', 'FAILED'")
    model_version: Optional[str] = Field(None, description="Model version")
    query_product_id: Optional[int] = Field(None, description="Query product ID if linked to catalog")
    query_product_sku: Optional[str] = Field(None, description="Query product SKU")
    query_product_name: Optional[str] = Field(None, description="Query product title")
    input_product: Dict[str, Any] = Field(default_factory=dict, description="Input product data snapshot")
    total_candidates_analyzed: int = Field(0, description="Total candidates analyzed in catalog")
    execution_time_ms: Optional[float] = Field(None, description="Execution duration in milliseconds")
    created_at: datetime = Field(..., description="Detection timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    matches: List[DuplicateMatchHistoryItem] = Field(
        default_factory=list,
        description="Candidate matches found during this detection run",
    )


class DuplicatePaginationMeta(BaseModel):
    """Pagination metadata for duplicate history listing."""
    total: int = Field(..., description="Total matching detection runs")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total available pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")


class DuplicateHistoryResponse(BaseModel):
    """Paginated response containing detection history and pagination meta."""
    items: List[DuplicateHistoryItem] = Field(default_factory=list, description="History items")
    pagination: DuplicatePaginationMeta = Field(..., description="Pagination metadata")


class DuplicateDetailResponse(BaseModel):
    """Comprehensive details of a specific duplicate record."""
    id: int = Field(..., description="Duplicate record ID (candidate ID or run ID)")
    record_type: str = Field(..., description="'candidate' or 'detection_run'")
    run_id: int = Field(..., description="Associated detection run ID")
    status: str = Field(..., description="Detection / review status")
    model_version: Optional[str] = Field(None, description="Model version used")
    similarity_score: Optional[float] = Field(None, description="Similarity score (if candidate)")
    confidence_score: Optional[float] = Field(None, description="Confidence score (if candidate)")
    rank: Optional[int] = Field(None, description="Rank position (if candidate)")
    matching_features: Dict[str, Any] = Field(default_factory=dict, description="Feature breakdown")
    created_at: datetime = Field(..., description="Detection timestamp")
    query_product: Optional[Dict[str, Any]] = Field(None, description="Query / input product specifications")
    matched_product: Optional[Dict[str, Any]] = Field(None, description="Matched catalog product specifications")
    review: Optional[DuplicateReviewResponse] = Field(None, description="Review decision record")
    review_status: str = Field("PENDING", description="'CONFIRMED', 'REJECTED', or 'PENDING'")
    matches: List[DuplicateMatchHistoryItem] = Field(
        default_factory=list,
        description="All matches associated with this run (if queried by run ID)",
    )
