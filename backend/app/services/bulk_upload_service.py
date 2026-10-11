"""
Bulk upload service — orchestrates the full pipeline:

  File bytes
    → validate extension / columns
    → fetch existing SKUs (one DB round-trip)
    → parse + validate rows (chunked, no full-table memory load)
    → batch-insert valid products
    → update BulkUploadJob with results

Runs as a FastAPI BackgroundTask so the upload API returns immediately
with job_id while processing continues in the background.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bulk_upload import BulkUploadJob
from app.repositories.bulk_upload_repository import BulkUploadRepository
from app.schemas.bulk_upload import BulkUploadInitResponse, BulkUploadJobResponse
from app.services.audit_service import AuditService
from app.utils.exceptions import DatabaseError
from app.utils.file_parser import (
    validate_columns,
    validate_and_parse_rows,
    read_file_to_dataframe,
    validate_extension,
    REQUIRED_COLUMNS,
)

logger = logging.getLogger(__name__)

# Maximum errors captured in error_summary (prevent giant JSONB payloads)
MAX_ERRORS_STORED = 500


class BulkUploadService:
    """Orchestrates bulk product upload: parse → validate → insert → track."""

    def __init__(self, db: Session):
        self.repo = BulkUploadRepository(db)
        self.audit = AuditService(db)
        self.db = db

    # ── Public API methods ────────────────────────────────────────────────────

    def create_upload_job(self, filename: str, file_type: str) -> BulkUploadJob:
        """Create a PENDING job record and return it."""
        job = self.repo.create_job(filename, file_type)
        self.audit.log_bulk_upload_started(job.id, filename, file_type)
        return job

    def get_job(self, job_id: int) -> BulkUploadJobResponse:
        """Retrieve a job by ID or raise 404."""
        try:
            job = self.repo.get_job(job_id)
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error fetching upload job.",
            )
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload job {job_id} not found.",
            )
        return BulkUploadJobResponse.model_validate(job)

    def process_upload(self, job_id: int, file_bytes: bytes, filename: str) -> None:
        """Full processing pipeline — intended to run as a BackgroundTask.

        Marks job PROCESSING, streams rows through validation, batch-inserts
        valid products, then finalises the job status.
        """
        try:
            job = self.repo.get_job(job_id)
        except DatabaseError:
            logger.error(f"Could not retrieve job {job_id} for processing.")
            return

        if job is None:
            logger.error(f"Job {job_id} disappeared before processing started.")
            return

        # ── Mark PROCESSING ───────────────────────────────────────────────────
        self.repo.update_job_status(job, status="PROCESSING")

        try:
            # ── Parse file into DataFrame ─────────────────────────────────────
            df = read_file_to_dataframe(file_bytes, filename)

            # ── Column validation ─────────────────────────────────────────────
            missing_cols = validate_columns(list(df.columns))
            if missing_cols:
                err_msg = f"Missing required columns: {', '.join(missing_cols)}"
                self.repo.update_job_status(
                    job,
                    status="FAILED",
                    total_rows=0,
                    successful_rows=0,
                    failed_rows=0,
                    error_summary=[{"error": err_msg}],
                    completed_at=datetime.now(timezone.utc),
                )
                self.audit.log_bulk_upload_failed(job_id, filename, err_msg)
                return

            # ── Fetch existing SKUs once (efficient dedup) ────────────────────
            existing_skus = self.repo.get_existing_skus()

            # ── Row-by-row validation (chunked, generator-based) ──────────────
            valid_rows: List[dict] = []
            error_summary: List[dict] = []
            total = 0

            for row_num, parsed, error in validate_and_parse_rows(df, existing_skus):
                total += 1
                if error:
                    if len(error_summary) < MAX_ERRORS_STORED:
                        error_summary.append({"row": row_num, "error": error})
                else:
                    valid_rows.append(parsed)

            # ── Batch insert ──────────────────────────────────────────────────
            inserted = self.repo.bulk_insert_products(valid_rows)
            failed = total - inserted

            # ── Determine final status ────────────────────────────────────────
            if inserted == 0 and total > 0:
                final_status = "FAILED"
            elif failed > 0:
                final_status = "COMPLETED_WITH_ERRORS"
            else:
                final_status = "COMPLETED"

            self.repo.update_job_status(
                job,
                status=final_status,
                total_rows=total,
                successful_rows=inserted,
                failed_rows=failed,
                error_summary=error_summary,
                completed_at=datetime.now(timezone.utc),
            )
            self.audit.log_bulk_upload_completed(
                job_id=job_id,
                filename=filename,
                total_rows=total,
                successful_rows=inserted,
                failed_rows=failed,
                status=final_status,
            )
            logger.info(
                f"Job {job_id}: {final_status} — "
                f"{inserted}/{total} rows inserted, {failed} failed."
            )

        except ValueError as exc:
            # File-level errors (empty file, bad format)
            self.repo.update_job_status(
                job,
                status="FAILED",
                error_summary=[{"error": str(exc)}],
                completed_at=datetime.now(timezone.utc),
            )
            self.audit.log_bulk_upload_failed(job_id, filename, str(exc))
            logger.warning(f"Job {job_id} FAILED (file error): {exc}")

        except DatabaseError as exc:
            self.repo.update_job_status(
                job,
                status="FAILED",
                error_summary=[{"error": str(exc)}],
                completed_at=datetime.now(timezone.utc),
            )
            self.audit.log_bulk_upload_failed(job_id, filename, str(exc))
            logger.error(f"Job {job_id} FAILED (DB error): {exc}")

        except Exception as exc:
            # Unexpected error — fail safely, never crash the background task
            logger.error(f"Job {job_id} unexpected error: {exc}", exc_info=True)
            try:
                self.repo.update_job_status(
                    job,
                    status="FAILED",
                    error_summary=[{"error": "An unexpected internal error occurred."}],
                    completed_at=datetime.now(timezone.utc),
                )
            except Exception:
                pass  # Swallow secondary errors silently
