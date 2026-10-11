import logging
from datetime import datetime, timezone
from typing import List, Optional, Set

from sqlalchemy import select, insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.bulk_upload import BulkUploadJob
from app.models.product import Product
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Rows per single INSERT statement to Supabase (tuned for pg connection pooler)
BATCH_INSERT_SIZE = 500


class BulkUploadRepository:
    """Database operations for BulkUploadJob and bulk product insertion."""

    def __init__(self, db: Session):
        self.db = db

    # ── BulkUploadJob CRUD ─────────────────────────────────────────────────────

    def create_job(self, filename: str, file_type: str) -> BulkUploadJob:
        try:
            job = BulkUploadJob(
                filename=filename,
                file_type=file_type,
                status="PENDING",
                total_rows=0,
                successful_rows=0,
                failed_rows=0,
                error_summary=[],
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"Failed to create BulkUploadJob: {exc}")
            raise DatabaseError() from exc

    def get_job(self, job_id: int) -> Optional[BulkUploadJob]:
        try:
            return self.db.get(BulkUploadJob, job_id)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch BulkUploadJob id={job_id}: {exc}")
            raise DatabaseError() from exc

    def update_job_status(
        self,
        job: BulkUploadJob,
        *,
        status: str,
        total_rows: int = 0,
        successful_rows: int = 0,
        failed_rows: int = 0,
        error_summary: list = None,
        completed_at: datetime = None,
    ) -> BulkUploadJob:
        try:
            job.status = status
            job.total_rows = total_rows
            job.successful_rows = successful_rows
            job.failed_rows = failed_rows
            if error_summary is not None:
                job.error_summary = error_summary
            if completed_at is not None:
                job.completed_at = completed_at
            self.db.commit()
            self.db.refresh(job)
            return job
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"Failed to update BulkUploadJob id={job.id}: {exc}")
            raise DatabaseError() from exc

    # ── Product bulk operations ────────────────────────────────────────────────

    def get_existing_skus(self) -> Set[str]:
        """Fetch ALL existing product SKUs in one query to power in-memory dedup."""
        try:
            result = self.db.execute(select(Product.sku))
            return {row[0] for row in result}
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch existing SKUs: {exc}")
            raise DatabaseError() from exc

    def bulk_insert_products(self, rows: List[dict]) -> int:
        """Insert product dicts in batches using Core INSERT for performance.

        Returns the number of rows successfully inserted.
        """
        if not rows:
            return 0

        inserted = 0
        for i in range(0, len(rows), BATCH_INSERT_SIZE):
            batch = rows[i: i + BATCH_INSERT_SIZE]
            try:
                self.db.execute(insert(Product), batch)
                self.db.commit()
                inserted += len(batch)
            except SQLAlchemyError as exc:
                self.db.rollback()
                logger.error(f"Batch insert failed (batch starting at {i}): {exc}")
                # Re-raise so the service layer can mark job as FAILED
                raise DatabaseError(
                    f"Database batch insert failed at row offset {i}."
                ) from exc

        return inserted
