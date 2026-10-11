"""
Tests for Stage 9: Dashboard Backend APIs.

Verifies all 4 dashboard endpoints:
  - GET /api/dashboard/overview
  - GET /api/dashboard/products
  - GET /api/dashboard/duplicates
  - GET /api/dashboard/activity
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
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


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/dashboard/overview
# ---------------------------------------------------------------------------

class TestDashboardOverview:

    def test_overview_returns_all_fields(self, client):
        """GET /api/dashboard/overview returns all required statistics fields."""
        mock_response = DashboardOverviewResponse(
            total_products=85000,
            active_products=84200,
            inactive_products=800,
            total_duplicate_checks=120,
            confirmed_duplicates=35,
            rejected_duplicates=15,
            pending_duplicates=70,
            total_bulk_uploads=12,
            successful_uploads=10,
            failed_uploads=2,
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            MockServiceClass.return_value.get_overview.return_value = mock_response

            resp = client.get("/api/dashboard/overview")
            assert resp.status_code == 200
            data = resp.json()

            # All required top-level fields must be present
            assert data["total_products"] == 85000
            assert data["active_products"] == 84200
            assert data["inactive_products"] == 800
            assert data["total_duplicate_checks"] == 120
            assert data["confirmed_duplicates"] == 35
            assert data["rejected_duplicates"] == 15
            assert data["pending_duplicates"] == 70
            assert data["total_bulk_uploads"] == 12
            assert data["successful_uploads"] == 10
            assert data["failed_uploads"] == 2

    def test_overview_schema_completeness(self, client):
        """All required overview schema keys are present in the response."""
        mock_response = DashboardOverviewResponse(
            total_products=0,
            active_products=0,
            inactive_products=0,
            total_duplicate_checks=0,
            confirmed_duplicates=0,
            rejected_duplicates=0,
            pending_duplicates=0,
            total_bulk_uploads=0,
            successful_uploads=0,
            failed_uploads=0,
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            MockServiceClass.return_value.get_overview.return_value = mock_response

            resp = client.get("/api/dashboard/overview")
            assert resp.status_code == 200
            data = resp.json()

            required_keys = {
                "total_products", "active_products", "inactive_products",
                "total_duplicate_checks", "confirmed_duplicates", "rejected_duplicates",
                "pending_duplicates", "total_bulk_uploads", "successful_uploads", "failed_uploads",
            }
            assert required_keys.issubset(data.keys())


# ---------------------------------------------------------------------------
# /api/dashboard/products
# ---------------------------------------------------------------------------

class TestDashboardProducts:

    def test_products_endpoint_returns_stats(self, client):
        """GET /api/dashboard/products returns category and brand breakdowns."""
        mock_response = ProductStatsResponse(
            total_products=85000,
            active_products=84200,
            inactive_products=800,
            by_category=[
                CategoryCount(category="Electronics", count=30000),
                CategoryCount(category="Tools", count=25000),
            ],
            by_brand=[
                BrandCount(brand="Bosch", count=12000),
                BrandCount(brand="Logitech", count=8000),
            ],
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            MockServiceClass.return_value.get_product_stats.return_value = mock_response

            resp = client.get("/api/dashboard/products")
            assert resp.status_code == 200
            data = resp.json()

            assert data["total_products"] == 85000
            assert data["active_products"] == 84200
            assert len(data["by_category"]) == 2
            assert data["by_category"][0]["category"] == "Electronics"
            assert data["by_category"][0]["count"] == 30000
            assert len(data["by_brand"]) == 2
            assert data["by_brand"][0]["brand"] == "Bosch"

    def test_products_query_params_passed(self, client):
        """category_limit and brand_limit query params are forwarded to service."""
        mock_response = ProductStatsResponse(
            total_products=0,
            active_products=0,
            inactive_products=0,
            by_category=[],
            by_brand=[],
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            mock_inst = MockServiceClass.return_value
            mock_inst.get_product_stats.return_value = mock_response

            resp = client.get("/api/dashboard/products?category_limit=5&brand_limit=3")
            assert resp.status_code == 200

            call_kwargs = mock_inst.get_product_stats.call_args.kwargs
            assert call_kwargs["category_limit"] == 5
            assert call_kwargs["brand_limit"] == 3


# ---------------------------------------------------------------------------
# /api/dashboard/duplicates
# ---------------------------------------------------------------------------

class TestDashboardDuplicates:

    def test_duplicates_endpoint_returns_stats(self, client):
        """GET /api/dashboard/duplicates returns counts and recent activity."""
        now = datetime.now(timezone.utc)
        mock_response = DuplicateStatsResponse(
            total_duplicate_checks=120,
            confirmed_duplicates=35,
            rejected_duplicates=15,
            pending_duplicates=70,
            recent_activity=[
                RecentDuplicateActivity(
                    run_id=1,
                    query_sku="ELEC-001",
                    query_name="Wireless Mouse",
                    status="MODEL_UNAVAILABLE",
                    total_candidates=5,
                    created_at=now,
                )
            ],
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            MockServiceClass.return_value.get_duplicate_stats.return_value = mock_response

            resp = client.get("/api/dashboard/duplicates")
            assert resp.status_code == 200
            data = resp.json()

            assert data["total_duplicate_checks"] == 120
            assert data["confirmed_duplicates"] == 35
            assert data["rejected_duplicates"] == 15
            assert data["pending_duplicates"] == 70
            assert len(data["recent_activity"]) == 1
            assert data["recent_activity"][0]["run_id"] == 1
            assert data["recent_activity"][0]["query_sku"] == "ELEC-001"
            assert data["recent_activity"][0]["status"] == "MODEL_UNAVAILABLE"

    def test_duplicates_activity_limit_param(self, client):
        """activity_limit param is forwarded to service correctly."""
        mock_response = DuplicateStatsResponse(
            total_duplicate_checks=0,
            confirmed_duplicates=0,
            rejected_duplicates=0,
            pending_duplicates=0,
            recent_activity=[],
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            mock_inst = MockServiceClass.return_value
            mock_inst.get_duplicate_stats.return_value = mock_response

            resp = client.get("/api/dashboard/duplicates?activity_limit=5")
            assert resp.status_code == 200

            call_kwargs = mock_inst.get_duplicate_stats.call_args.kwargs
            assert call_kwargs["activity_limit"] == 5


# ---------------------------------------------------------------------------
# /api/dashboard/activity
# ---------------------------------------------------------------------------

class TestDashboardActivity:

    def test_activity_endpoint_returns_recent_events(self, client):
        """GET /api/dashboard/activity returns latest audit log entries."""
        now = datetime.now(timezone.utc)
        mock_response = DashboardActivityResponse(
            items=[
                DashboardActivityItem(
                    id=10,
                    action="PRODUCT_CREATED",
                    entity_type="PRODUCT",
                    entity_id=200,
                    user_id="admin",
                    description="Created product 'Drill Bit Set' (SKU: TOOL-500)",
                    created_at=now,
                    metadata={"sku": "TOOL-500"},
                ),
                DashboardActivityItem(
                    id=9,
                    action="DUPLICATE_CONFIRMED",
                    entity_type="DUPLICATE",
                    entity_id=55,
                    user_id="reviewer_1",
                    description="Duplicate match ID 55 was confirmed by reviewer_1",
                    created_at=now,
                    metadata={"decision": "CONFIRMED"},
                ),
            ],
            total=2,
        )

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            MockServiceClass.return_value.get_recent_activity.return_value = mock_response

            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            data = resp.json()

            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["action"] == "PRODUCT_CREATED"
            assert data["items"][1]["action"] == "DUPLICATE_CONFIRMED"

    def test_activity_limit_param(self, client):
        """limit query param is forwarded to service correctly."""
        mock_response = DashboardActivityResponse(items=[], total=0)

        with patch("app.routers.dashboard.DashboardService") as MockServiceClass:
            mock_inst = MockServiceClass.return_value
            mock_inst.get_recent_activity.return_value = mock_response

            resp = client.get("/api/dashboard/activity?limit=5")
            assert resp.status_code == 200

            call_kwargs = mock_inst.get_recent_activity.call_args.kwargs
            assert call_kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# DashboardService Unit Tests
# ---------------------------------------------------------------------------

class TestDashboardServiceUnit:

    def test_service_get_overview_combines_all_repos(self):
        """DashboardService.get_overview assembles data from all repository methods."""
        mock_db = MagicMock()
        from app.services.dashboard_service import DashboardService
        from app.repositories.dashboard_repository import DashboardRepository

        with patch.object(DashboardRepository, "get_product_counts", return_value={"total_products": 100, "active_products": 90, "inactive_products": 10}), \
             patch.object(DashboardRepository, "get_duplicate_run_counts", return_value={"total_duplicate_checks": 5}), \
             patch.object(DashboardRepository, "get_review_counts", return_value={"confirmed_duplicates": 2, "rejected_duplicates": 1, "pending_duplicates": 2}), \
             patch.object(DashboardRepository, "get_bulk_upload_counts", return_value={"total_bulk_uploads": 3, "successful_uploads": 2, "failed_uploads": 1}):

            service = DashboardService(db=mock_db)
            result = service.get_overview()

            assert result.total_products == 100
            assert result.active_products == 90
            assert result.inactive_products == 10
            assert result.total_duplicate_checks == 5
            assert result.confirmed_duplicates == 2
            assert result.rejected_duplicates == 1
            assert result.pending_duplicates == 2
            assert result.total_bulk_uploads == 3
            assert result.successful_uploads == 2
            assert result.failed_uploads == 1

    def test_service_activity_limit_capped(self):
        """DashboardService.get_recent_activity clamps limit to 1-100."""
        mock_db = MagicMock()
        from app.services.dashboard_service import DashboardService
        from app.repositories.dashboard_repository import DashboardRepository

        with patch.object(DashboardRepository, "get_recent_activity", return_value=[]) as mock_repo:
            service = DashboardService(db=mock_db)
            service.get_recent_activity(limit=500)  # Over max
            called_limit = mock_repo.call_args.kwargs["limit"]
            assert called_limit == 100

            service.get_recent_activity(limit=0)  # Under min
            called_limit = mock_repo.call_args.kwargs["limit"]
            assert called_limit == 1
