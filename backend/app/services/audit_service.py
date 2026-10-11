import math
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import (
    ActivityFeedResponse,
    ActivityItemResponse,
    AuditLogListResponse,
    AuditLogPaginationMeta,
    AuditLogResponse,
)
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AuditAction:
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"
    PRODUCT_DEACTIVATED = "PRODUCT_DEACTIVATED"
    BULK_UPLOAD_STARTED = "BULK_UPLOAD_STARTED"
    BULK_UPLOAD_COMPLETED = "BULK_UPLOAD_COMPLETED"
    BULK_UPLOAD_FAILED = "BULK_UPLOAD_FAILED"
    DUPLICATE_CHECKED = "DUPLICATE_CHECKED"
    DUPLICATE_CONFIRMED = "DUPLICATE_CONFIRMED"
    DUPLICATE_REJECTED = "DUPLICATE_REJECTED"


class AuditEntityType:
    PRODUCT = "PRODUCT"
    BULK_UPLOAD = "BULK_UPLOAD"
    DUPLICATE = "DUPLICATE"


class AuditService:
    """Central service for recording and retrieving audit trails and activity events."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)

    # -----------------------------------------------------------------------
    # Logging Methods
    # -----------------------------------------------------------------------

    def log(
        self,
        *,
        action: str,
        entity_type: str,
        description: str,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record an audit log entry. Catches and logs DB exceptions without breaking caller."""
        try:
            return self.repo.create(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                metadata=metadata,
            )
        except Exception as exc:
            logger.error(f"Audit log recording failed for action {action}: {exc}", exc_info=True)
            return None

    def log_product_created(self, product, user_id: Optional[str] = None):
        """Audit log for product creation."""
        new_vals = {
            "sku": product.sku,
            "name": product.name,
            "brand": product.brand,
            "category": product.category,
            "subcategory": product.subcategory,
            "unit": product.unit,
            "is_active": product.is_active,
        }
        return self.log(
            action=AuditAction.PRODUCT_CREATED,
            entity_type=AuditEntityType.PRODUCT,
            entity_id=product.id,
            user_id=user_id,
            description=f"Created product '{product.name}' (SKU: {product.sku})",
            new_values=new_vals,
            metadata={"sku": product.sku},
        )

    def log_product_updated(
        self,
        product_id: int,
        old_dict: Dict[str, Any],
        new_dict: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Audit log for product update, capturing ONLY changed fields."""
        old_diff: Dict[str, Any] = {}
        new_diff: Dict[str, Any] = {}

        for k, v in new_dict.items():
            if k in old_dict and old_dict[k] != v:
                old_diff[k] = old_dict[k]
                new_diff[k] = v

        if not old_diff:
            # No effective field changes
            return None

        sku = new_dict.get("sku") or old_dict.get("sku")
        return self.log(
            action=AuditAction.PRODUCT_UPDATED,
            entity_type=AuditEntityType.PRODUCT,
            entity_id=product_id,
            user_id=user_id,
            description=f"Updated product ID {product_id} (changed fields: {', '.join(sorted(old_diff.keys()))})",
            old_values=old_diff,
            new_values=new_diff,
            metadata={"sku": sku, "fields_changed": list(old_diff.keys())},
        )

    def log_product_deactivated(self, product, user_id: Optional[str] = None):
        """Audit log for product soft deletion."""
        return self.log(
            action=AuditAction.PRODUCT_DEACTIVATED,
            entity_type=AuditEntityType.PRODUCT,
            entity_id=product.id,
            user_id=user_id,
            description=f"Deactivated product '{product.name}' (SKU: {product.sku})",
            old_values={"is_active": True},
            new_values={"is_active": False},
            metadata={"sku": product.sku},
        )

    def log_bulk_upload_started(
        self,
        job_id: int,
        filename: str,
        file_type: str,
        user_id: Optional[str] = None,
    ):
        """Audit log when a bulk upload job is accepted."""
        return self.log(
            action=AuditAction.BULK_UPLOAD_STARTED,
            entity_type=AuditEntityType.BULK_UPLOAD,
            entity_id=job_id,
            user_id=user_id,
            description=f"Bulk upload started for file '{filename}' ({file_type})",
            metadata={"job_id": job_id, "filename": filename, "file_type": file_type},
        )

    def log_bulk_upload_completed(
        self,
        job_id: int,
        filename: str,
        total_rows: int,
        successful_rows: int,
        failed_rows: int,
        status: str,
        user_id: Optional[str] = None,
    ):
        """Audit log when a bulk upload finishes processing."""
        action = AuditAction.BULK_UPLOAD_COMPLETED if failed_rows == 0 else AuditAction.BULK_UPLOAD_FAILED
        desc = (
            f"Bulk upload {status.lower()} for '{filename}': "
            f"{successful_rows}/{total_rows} succeeded, {failed_rows} failed."
        )
        return self.log(
            action=action,
            entity_type=AuditEntityType.BULK_UPLOAD,
            entity_id=job_id,
            user_id=user_id,
            description=desc,
            metadata={
                "job_id": job_id,
                "filename": filename,
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "final_status": status,
            },
        )

    def log_bulk_upload_failed(
        self,
        job_id: int,
        filename: str,
        error_message: str,
        user_id: Optional[str] = None,
    ):
        """Audit log when a bulk upload fails completely (e.g. invalid format/missing columns)."""
        return self.log(
            action=AuditAction.BULK_UPLOAD_FAILED,
            entity_type=AuditEntityType.BULK_UPLOAD,
            entity_id=job_id,
            user_id=user_id,
            description=f"Bulk upload failed for '{filename}': {error_message}",
            metadata={"job_id": job_id, "filename": filename, "error": error_message},
        )

    def log_duplicate_checked(
        self,
        run_id: Optional[int],
        query_sku: str,
        query_name: str,
        status: str,
        model_version: Optional[str],
        total_candidates: int,
        user_id: Optional[str] = None,
    ):
        """Audit log when a duplicate check is executed."""
        desc = f"Checked duplicates for '{query_name}' (SKU: {query_sku}) — status: {status}"
        return self.log(
            action=AuditAction.DUPLICATE_CHECKED,
            entity_type=AuditEntityType.DUPLICATE,
            entity_id=run_id,
            user_id=user_id,
            description=desc,
            metadata={
                "run_id": run_id,
                "query_sku": query_sku,
                "status": status,
                "model_version": model_version,
                "total_candidates": total_candidates,
            },
        )

    def log_duplicate_review(
        self,
        candidate_id: int,
        decision: str,  # CONFIRMED or REJECTED
        reason: Optional[str] = None,
        reviewer_id: Optional[str] = None,
    ):
        """Audit log for duplicate review decisions."""
        action = AuditAction.DUPLICATE_CONFIRMED if decision == "CONFIRMED" else AuditAction.DUPLICATE_REJECTED
        desc = f"Duplicate match ID {candidate_id} was {decision.lower()} by {reviewer_id or 'user'}"
        if reason:
            desc += f": {reason}"
        return self.log(
            action=action,
            entity_type=AuditEntityType.DUPLICATE,
            entity_id=candidate_id,
            user_id=reviewer_id,
            description=desc,
            new_values={"decision": decision, "reason": reason},
            metadata={"candidate_id": candidate_id, "decision": decision, "reviewer_id": reviewer_id},
        )

    # -----------------------------------------------------------------------
    # Retrieval Methods
    # -----------------------------------------------------------------------

    def get_audit_log(self, log_id: int) -> AuditLogResponse:
        """Fetch a specific audit log by ID or raise 404."""
        log = self.repo.get_by_id(log_id)
        if log is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit log with ID {log_id} not found.",
            )
        return AuditLogResponse.model_validate(log)

    def list_audit_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AuditLogListResponse:
        """Query paginated audit logs."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        items, total = self.repo.list_logs(
            page=page,
            page_size=page_size,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(i) for i in items],
            pagination=AuditLogPaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    def get_activity_feed(
        self,
        limit: int = 20,
        entity_type: Optional[str] = None,
    ) -> ActivityFeedResponse:
        """Retrieve recent human-readable activity feed for dashboard views."""
        limit = max(1, min(limit, 100))
        logs = self.repo.get_recent_activity(limit=limit, entity_type=entity_type)
        return ActivityFeedResponse(
            items=[ActivityItemResponse.model_validate(l) for l in logs],
            total=len(logs),
        )
