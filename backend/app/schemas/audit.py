from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class AuditLogResponse(BaseModel):
    """Serialized audit log record."""
    id: int = Field(..., description="Audit log ID")
    action: str = Field(..., description="Action performed, e.g. PRODUCT_CREATED")
    entity_type: str = Field(..., description="Entity category, e.g. PRODUCT, BULK_UPLOAD, DUPLICATE")
    entity_id: Optional[int] = Field(None, description="Primary ID of the affected entity")
    user_id: Optional[str] = Field(None, description="User or system actor ID")
    description: str = Field(..., description="Human-readable event summary")
    old_values: Optional[Dict[str, Any]] = Field(None, description="Prior values for modified fields")
    new_values: Optional[Dict[str, Any]] = Field(None, description="Updated values for modified fields")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("log_metadata", "metadata"),
        description="Structured operational context (IDs, counts, flags)",
    )
    created_at: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuditLogPaginationMeta(BaseModel):
    """Pagination metadata for audit logs listing."""
    total: int = Field(..., description="Total matching logs")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of logs per page")
    total_pages: int = Field(..., description="Total available pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""
    items: List[AuditLogResponse] = Field(default_factory=list, description="Audit log entries")
    pagination: AuditLogPaginationMeta = Field(..., description="Pagination metadata")


class ActivityItemResponse(BaseModel):
    """Human-readable activity summary item for dashboard activity streams."""
    id: int = Field(..., description="Audit log ID")
    action: str = Field(..., description="Action performed")
    entity_type: str = Field(..., description="Entity category")
    entity_id: Optional[int] = Field(None, description="Affected entity ID")
    user_id: Optional[str] = Field(None, description="Actor ID")
    description: str = Field(..., description="Formatted summary of activity")
    created_at: datetime = Field(..., description="Event timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("log_metadata", "metadata"),
        description="Additional context",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ActivityFeedResponse(BaseModel):
    """Recent human-readable activity feed."""
    items: List[ActivityItemResponse] = Field(default_factory=list, description="Recent activities")
    total: int = Field(..., description="Total number of items returned")
