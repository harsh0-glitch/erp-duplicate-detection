from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Dashboard Overview Schemas
# ---------------------------------------------------------------------------

class ProductOverviewStats(BaseModel):
    total_products: int = Field(..., description="Total products in catalog")
    active_products: int = Field(..., description="Active products available in catalog")
    inactive_products: int = Field(..., description="Deactivated products")


class DuplicateOverviewStats(BaseModel):
    total_duplicate_checks: int = Field(..., description="Total duplicate detection runs performed")
    confirmed_duplicates: int = Field(..., description="Total duplicate matches confirmed by users")
    rejected_duplicates: int = Field(..., description="Total suspected duplicates rejected")
    pending_duplicates: int = Field(..., description="Candidate matches awaiting review")


class BulkUploadOverviewStats(BaseModel):
    total_bulk_uploads: int = Field(..., description="Total bulk upload jobs initiated")
    successful_uploads: int = Field(..., description="Upload jobs completed without errors")
    failed_uploads: int = Field(..., description="Upload jobs failed or completed with errors")


class DashboardOverviewResponse(BaseModel):
    """Aggregate statistics for the ERP system overview dashboard."""
    # Top-level unified fields as requested
    total_products: int
    active_products: int
    inactive_products: int

    total_duplicate_checks: int
    confirmed_duplicates: int
    rejected_duplicates: int
    pending_duplicates: int

    total_bulk_uploads: int
    successful_uploads: int
    failed_uploads: int


# ---------------------------------------------------------------------------
# 2. Product Statistics Schemas
# ---------------------------------------------------------------------------

class CategoryCount(BaseModel):
    category: str
    count: int


class BrandCount(BaseModel):
    brand: str
    count: int


class ProductStatsResponse(BaseModel):
    """Product catalog distribution metrics."""
    total_products: int
    active_products: int
    inactive_products: int
    by_category: List[CategoryCount] = Field(default_factory=list)
    by_brand: List[BrandCount] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 3. Duplicate Statistics Schemas
# ---------------------------------------------------------------------------

class RecentDuplicateActivity(BaseModel):
    run_id: int
    query_sku: Optional[str]
    query_name: Optional[str]
    status: str
    total_candidates: int
    created_at: datetime


class DuplicateStatsResponse(BaseModel):
    """Duplicate detection and review metrics."""
    total_duplicate_checks: int
    confirmed_duplicates: int
    rejected_duplicates: int
    pending_duplicates: int
    recent_activity: List[RecentDuplicateActivity] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. Dashboard Activity Feed Schema
# ---------------------------------------------------------------------------

class DashboardActivityItem(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    user_id: Optional[str] = None
    description: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class DashboardActivityResponse(BaseModel):
    items: List[DashboardActivityItem] = Field(default_factory=list)
    total: int
