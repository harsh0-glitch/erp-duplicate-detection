import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.product import Product
from app.models.duplicate import DuplicateDetectionRun, DuplicateCandidate, DuplicateReview
from app.models.bulk_upload import BulkUploadJob
from app.models.audit_log import AuditLog
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DashboardRepository:
    """Read-only data queries aggregating statistics for the dashboard.
    No writes are performed here. Reuses existing tables only.
    """

    def __init__(self, db: Session):
        self.db = db

    # -----------------------------------------------------------------------
    # Product Statistics
    # -----------------------------------------------------------------------

    def get_product_counts(self) -> Dict[str, int]:
        """Return total, active, and inactive product counts."""
        try:
            rows = self.db.execute(
                select(
                    func.count().label("total"),
                    func.sum(case((Product.is_active == True, 1), else_=0)).label("active"),
                    func.sum(case((Product.is_active == False, 1), else_=0)).label("inactive"),
                )
            ).one()
            return {
                "total_products": int(rows.total or 0),
                "active_products": int(rows.active or 0),
                "inactive_products": int(rows.inactive or 0),
            }
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching product counts: {exc}")
            raise DatabaseError("Failed to fetch product counts.") from exc

    def get_products_by_category(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Count active products grouped by category, ordered descending."""
        try:
            rows = self.db.execute(
                select(Product.category, func.count().label("count"))
                .where(Product.is_active == True)
                .where(Product.category.isnot(None))
                .group_by(Product.category)
                .order_by(func.count().desc())
                .limit(limit)
            ).all()
            return [{"category": r.category, "count": r.count} for r in rows]
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching products by category: {exc}")
            raise DatabaseError("Failed to fetch category stats.") from exc

    def get_products_by_brand(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Count active products grouped by brand, ordered descending."""
        try:
            rows = self.db.execute(
                select(Product.brand, func.count().label("count"))
                .where(Product.is_active == True)
                .where(Product.brand.isnot(None))
                .group_by(Product.brand)
                .order_by(func.count().desc())
                .limit(limit)
            ).all()
            return [{"brand": r.brand, "count": r.count} for r in rows]
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching products by brand: {exc}")
            raise DatabaseError("Failed to fetch brand stats.") from exc

    # -----------------------------------------------------------------------
    # Duplicate Detection Statistics
    # -----------------------------------------------------------------------

    def get_duplicate_run_counts(self) -> Dict[str, int]:
        """Return total duplicate detection run count."""
        try:
            total = self.db.execute(
                select(func.count()).select_from(DuplicateDetectionRun)
            ).scalar_one()
            return {"total_duplicate_checks": int(total or 0)}
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching duplicate run counts: {exc}")
            raise DatabaseError("Failed to fetch duplicate check counts.") from exc

    def get_review_counts(self) -> Dict[str, int]:
        """Return confirmed, rejected, and pending candidate counts."""
        try:
            total_candidates = self.db.execute(
                select(func.count()).select_from(DuplicateCandidate)
            ).scalar_one()

            confirmed = self.db.execute(
                select(func.count()).select_from(DuplicateReview)
                .where(DuplicateReview.decision == "CONFIRMED")
            ).scalar_one()

            rejected = self.db.execute(
                select(func.count()).select_from(DuplicateReview)
                .where(DuplicateReview.decision == "REJECTED")
            ).scalar_one()

            reviewed = int(confirmed or 0) + int(rejected or 0)
            pending = max(0, int(total_candidates or 0) - reviewed)

            return {
                "confirmed_duplicates": int(confirmed or 0),
                "rejected_duplicates": int(rejected or 0),
                "pending_duplicates": pending,
            }
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching review counts: {exc}")
            raise DatabaseError("Failed to fetch duplicate review counts.") from exc

    def get_recent_duplicate_runs(self, limit: int = 10) -> List[Any]:
        """Return the most recent detection runs for the duplicates dashboard section."""
        try:
            return list(
                self.db.execute(
                    select(DuplicateDetectionRun)
                    .order_by(DuplicateDetectionRun.id.desc())
                    .limit(limit)
                ).scalars().all()
            )
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching recent duplicate runs: {exc}")
            raise DatabaseError("Failed to fetch recent duplicate activity.") from exc

    # -----------------------------------------------------------------------
    # Bulk Upload Statistics
    # -----------------------------------------------------------------------

    def get_bulk_upload_counts(self) -> Dict[str, int]:
        """Return total, successful, and failed bulk upload job counts."""
        try:
            rows = self.db.execute(
                select(
                    func.count().label("total"),
                    func.sum(
                        case((BulkUploadJob.status == "COMPLETED", 1), else_=0)
                    ).label("successful"),
                    func.sum(
                        case(
                            (BulkUploadJob.status.in_(["FAILED", "COMPLETED_WITH_ERRORS"]), 1),
                            else_=0,
                        )
                    ).label("failed"),
                )
            ).one()
            return {
                "total_bulk_uploads": int(rows.total or 0),
                "successful_uploads": int(rows.successful or 0),
                "failed_uploads": int(rows.failed or 0),
            }
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching bulk upload counts: {exc}")
            raise DatabaseError("Failed to fetch bulk upload stats.") from exc

    # -----------------------------------------------------------------------
    # Activity Feed
    # -----------------------------------------------------------------------

    def get_recent_activity(self, limit: int = 20) -> List[Any]:
        """Return the most recent audit log records for the activity feed."""
        try:
            return list(
                self.db.execute(
                    select(AuditLog)
                    .order_by(AuditLog.id.desc())
                    .limit(limit)
                ).scalars().all()
            )
        except SQLAlchemyError as exc:
            logger.error(f"Error fetching recent activity: {exc}")
            raise DatabaseError("Failed to fetch recent activity.") from exc
