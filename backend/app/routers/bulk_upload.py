import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bulk_upload import BulkUploadInitResponse, BulkUploadJobResponse
from app.services.bulk_upload_service import BulkUploadService
from app.utils.file_parser import validate_extension

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bulk-upload", tags=["Bulk Upload"])

# 50 MB file size limit
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def get_bulk_service(db: Session = Depends(get_db)) -> BulkUploadService:
    return BulkUploadService(db)


# ---------------------------------------------------------------------------
# POST /api/bulk-upload/products
# ---------------------------------------------------------------------------
@router.post(
    "/products",
    response_model=BulkUploadInitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk upload products from CSV or XLSX",
    description=(
        "Upload a CSV or XLSX file to import products in bulk. "
        "The file is validated immediately (extension, size, required columns). "
        "Row processing and database insertion run asynchronously as a background task. "
        "Use the returned `job_id` to poll `GET /api/bulk-upload/{job_id}` for progress. "
        "**Required columns:** `sku`, `name`. "
        "**Optional columns:** `description`, `brand`, `category`, `subcategory`, "
        "`unit`, `attributes` (JSON string), `is_active` (true/false)."
    ),
)
async def upload_products(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV or XLSX file containing products"),
    service: BulkUploadService = Depends(get_bulk_service),
):
    # ── Extension check ───────────────────────────────────────────────────────
    filename = file.filename or "upload"
    try:
        file_type = validate_extension(filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # ── Read bytes (with size guard) ──────────────────────────────────────────
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit.",
        )

    # ── Create PENDING job record ─────────────────────────────────────────────
    job = service.create_upload_job(filename=filename, file_type=file_type)

    # ── Kick off background processing ───────────────────────────────────────
    background_tasks.add_task(
        service.process_upload,
        job_id=job.id,
        file_bytes=file_bytes,
        filename=filename,
    )

    logger.info(f"Bulk upload job {job.id} created for file '{filename}' ({len(file_bytes)} bytes).")

    return BulkUploadInitResponse(
        job_id=job.id,
        filename=filename,
        status="PENDING",
        message=(
            f"Upload accepted. Processing {len(file_bytes)} bytes in the background. "
            f"Poll GET /api/bulk-upload/{job.id} for status."
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/bulk-upload/{job_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{job_id}",
    response_model=BulkUploadJobResponse,
    summary="Get bulk upload job status",
    description=(
        "Poll this endpoint to check the status and results of a bulk upload job. "
        "**Statuses:** `PENDING` → `PROCESSING` → `COMPLETED` / `COMPLETED_WITH_ERRORS` / `FAILED`. "
        "When `COMPLETED` or `COMPLETED_WITH_ERRORS`, `error_summary` contains "
        "per-row errors (up to 500 entries)."
    ),
)
def get_job_status(
    job_id: int,
    service: BulkUploadService = Depends(get_bulk_service),
):
    return service.get_job(job_id)
