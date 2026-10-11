import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    BrandCount,
    CategoryCount,
    DashboardActivityItem,
    DashboardActivityResponse,
    DashboardOverviewResponse,
    DuplicateStatsResponse,
    ProductStatsResponse,
    RecentDuplicateActivity,
)
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregates metrics from existing tables for dashboard API responses.
    Read-only. No tables are created or modified.
    """

    def __init__(self, db: Session):
        self.repo = DashboardRepository(db)

    def get_overview(self) -> DashboardOverviewResponse:
        """Combine product, duplicate, and bulk upload summary stats."""
        try:
            product_counts = self.repo.get_product_counts()
            dup_run_counts = self.repo.get_duplicate_run_counts()
            review_counts = self.repo.get_review_counts()
            upload_counts = self.repo.get_bulk_upload_counts()

            return DashboardOverviewResponse(
                **product_counts,
                **dup_run_counts,
                **review_counts,
                **upload_counts,
            )
        except DatabaseError as exc:
            logger.error(f"DashboardService.get_overview failed: {exc}")
            raise

    def get_product_stats(
        self,
        category_limit: int = 20,
        brand_limit: int = 20,
    ) -> ProductStatsResponse:
        """Return product distribution by category and brand."""
        try:
            product_counts = self.repo.get_product_counts()
            by_category = [
                CategoryCount(**row)
                for row in self.repo.get_products_by_category(limit=category_limit)
            ]
            by_brand = [
                BrandCount(**row)
                for row in self.repo.get_products_by_brand(limit=brand_limit)
            ]
            return ProductStatsResponse(
                **product_counts,
                by_category=by_category,
                by_brand=by_brand,
            )
        except DatabaseError as exc:
            logger.error(f"DashboardService.get_product_stats failed: {exc}")
            raise

    def get_duplicate_stats(self, activity_limit: int = 10) -> DuplicateStatsResponse:
        """Return duplicate check metrics and recent detection activity."""
        try:
            dup_run_counts = self.repo.get_duplicate_run_counts()
            review_counts = self.repo.get_review_counts()
            runs = self.repo.get_recent_duplicate_runs(limit=activity_limit)

            recent_activity = []
            for run in runs:
                query_sku = run.run_metadata.get("query_sku") if run.run_metadata else None
                query_name = run.run_metadata.get("query_name") if run.run_metadata else None
                if not query_sku and run.query_product:
                    query_sku = run.query_product.sku
                if not query_name and run.query_product:
                    query_name = run.query_product.name

                recent_activity.append(
                    RecentDuplicateActivity(
                        run_id=run.id,
                        query_sku=query_sku,
                        query_name=query_name,
                        status=run.status,
                        total_candidates=run.total_candidates,
                        created_at=run.created_at,
                    )
                )

            return DuplicateStatsResponse(
                **dup_run_counts,
                **review_counts,
                recent_activity=recent_activity,
            )
        except DatabaseError as exc:
            logger.error(f"DashboardService.get_duplicate_stats failed: {exc}")
            raise

    def get_recent_activity(self, limit: int = 20) -> DashboardActivityResponse:
        """Return recent audit log records as a human-readable activity feed."""
        limit = max(1, min(limit, 100))
        try:
            logs = self.repo.get_recent_activity(limit=limit)
            items = [
                DashboardActivityItem(
                    id=log.id,
                    action=log.action,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    user_id=log.user_id,
                    description=log.description,
                    created_at=log.created_at,
                    metadata=log.log_metadata,
                )
                for log in logs
            ]
            return DashboardActivityResponse(items=items, total=len(items))
        except DatabaseError as exc:
            logger.error(f"DashboardService.get_recent_activity failed: {exc}")
            raise
