from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BulkUploadJobResponse(BaseModel):
    """Response schema for a BulkUploadJob record."""
    id: int
    filename: str
    file_type: str
    status: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_summary: List[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BulkUploadInitResponse(BaseModel):
    """Immediate response returned when an upload job is accepted."""
    job_id: int
    filename: str
    status: str
    message: str
