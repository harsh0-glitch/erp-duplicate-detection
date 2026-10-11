"""
Tests for Stage 8: Audit & Activity Logging.

Verifies:
1. Audit log creation for major workflows (product CRUD, bulk upload, duplicate check & reviews).
2. Product update audit log captures only changed fields in old_values/new_values diff.
3. Bulk upload lifecycle audit logs (start, completion, failure).
4. Duplicate confirm and reject audit logs.
5. GET /api/audit-logs listing, filtering, and pagination.
6. GET /api/audit-logs/activity feed endpoint.
7. GET /api/audit-logs/{log_id} single record lookup and 404 handling.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.audit_log import AuditLog
from app.schemas.audit import (
    ActivityFeedResponse,
    ActivityItemResponse,
    AuditLogListResponse,
    AuditLogPaginationMeta,
    AuditLogResponse,
)
from app.services.audit_service import AuditAction, AuditEntityType, AuditService


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

class TestAuditLogsAPI:

    def test_list_audit_logs_success(self, client):
        """GET /api/audit-logs returns paginated list of audit records."""
        now = datetime.now(timezone.utc)
        mock_response = AuditLogListResponse(
            items=[
                AuditLogResponse(
                    id=1,
                    action=AuditAction.PRODUCT_CREATED,
                    entity_type=AuditEntityType.PRODUCT,
                    entity_id=10,
                    user_id="admin",
                    description="Created product 'Wireless Mouse' (SKU: ELEC-001)",
                    old_values=None,
                    new_values={"sku": "ELEC-001", "name": "Wireless Mouse"},
                    metadata={"sku": "ELEC-001"},
                    created_at=now,
                )
            ],
            pagination=AuditLogPaginationMeta(
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
                has_next=False,
                has_prev=False,
            ),
        )

        with patch("app.routers.audit_logs.AuditService") as MockServiceClass:
            MockServiceClass.return_value.list_audit_logs.return_value = mock_response

            resp = client.get("/api/audit-logs")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["action"] == "PRODUCT_CREATED"
            assert data["items"][0]["entity_id"] == 10
            assert data["pagination"]["total"] == 1

    def test_list_audit_logs_filtering(self, client):
        """GET /api/audit-logs passes query filters to service layer."""
        mock_response = AuditLogListResponse(
            items=[],
            pagination=AuditLogPaginationMeta(
                total=0,
                page=1,
                page_size=10,
                total_pages=1,
                has_next=False,
                has_prev=False,
            ),
        )

        with patch("app.routers.audit_logs.AuditService") as MockServiceClass:
            mock_inst = MockServiceClass.return_value
            mock_inst.list_audit_logs.return_value = mock_response

            resp = client.get(
                "/api/audit-logs?page=2&page_size=10&action=PRODUCT_UPDATED&entity_type=PRODUCT&entity_id=5&user_id=usr_1"
            )
            assert resp.status_code == 200

            call_kwargs = mock_inst.list_audit_logs.call_args.kwargs
            assert call_kwargs["page"] == 2
            assert call_kwargs["page_size"] == 10
            assert call_kwargs["action"] == "PRODUCT_UPDATED"
            assert call_kwargs["entity_type"] == "PRODUCT"
            assert call_kwargs["entity_id"] == 5
            assert call_kwargs["user_id"] == "usr_1"

    def test_get_activity_feed_endpoint(self, client):
        """GET /api/audit-logs/activity returns recent activity feed."""
        now = datetime.now(timezone.utc)
        mock_feed = ActivityFeedResponse(
            items=[
                ActivityItemResponse(
                    id=2,
                    action=AuditAction.DUPLICATE_CONFIRMED,
                    entity_type=AuditEntityType.DUPLICATE,
                    entity_id=101,
                    user_id="lead_reviewer",
                    description="Duplicate match ID 101 was confirmed by lead_reviewer",
                    created_at=now,
                    metadata={"candidate_id": 101, "decision": "CONFIRMED"},
                )
            ],
            total=1,
        )

        with patch("app.routers.audit_logs.AuditService") as MockServiceClass:
            MockServiceClass.return_value.get_activity_feed.return_value = mock_feed

            resp = client.get("/api/audit-logs/activity?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["action"] == "DUPLICATE_CONFIRMED"

    def test_get_single_audit_log_success(self, client):
        """GET /api/audit-logs/{id} returns single audit record."""
        now = datetime.now(timezone.utc)
        mock_log = AuditLogResponse(
            id=42,
            action=AuditAction.BULK_UPLOAD_STARTED,
            entity_type=AuditEntityType.BULK_UPLOAD,
            entity_id=7,
            user_id=None,
            description="Bulk upload started for file 'products.csv' (csv)",
            old_values=None,
            new_values=None,
            metadata={"job_id": 7, "filename": "products.csv"},
            created_at=now,
        )

        with patch("app.routers.audit_logs.AuditService") as MockServiceClass:
            MockServiceClass.return_value.get_audit_log.return_value = mock_log

            resp = client.get("/api/audit-logs/42")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 42
            assert data["action"] == "BULK_UPLOAD_STARTED"

    def test_get_single_audit_log_not_found(self, client):
        """GET /api/audit-logs/{id} returns 404 for nonexistent log ID."""
        from fastapi import HTTPException
        with patch("app.routers.audit_logs.AuditService") as MockServiceClass:
            MockServiceClass.return_value.get_audit_log.side_effect = HTTPException(
                status_code=404,
                detail="Audit log with ID 9999 not found.",
            )

            resp = client.get("/api/audit-logs/9999")
            assert resp.status_code == 404
            assert "9999" in resp.json()["error"]


# ---------------------------------------------------------------------------
# AuditService Unit Tests
# ---------------------------------------------------------------------------

class TestAuditServiceWorkflows:

    def test_audit_product_created(self):
        """Verify audit log creation for product creation."""
        mock_db = MagicMock()
        mock_product = MagicMock(
            id=15,
            sku="SKU-NEW-01",
            name="Mechanical Keyboard",
            brand="Keychron",
            category="Electronics",
            subcategory="Peripherals",
            unit="pcs",
            is_active=True,
        )

        service = AuditService(db=mock_db)
        service.log_product_created(mock_product, user_id="user_admin")

        assert mock_db.add.called
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.action == AuditAction.PRODUCT_CREATED
        assert log_obj.entity_type == AuditEntityType.PRODUCT
        assert log_obj.entity_id == 15
        assert log_obj.new_values["sku"] == "SKU-NEW-01"
        assert log_obj.old_values is None

    def test_audit_product_updated_diff_only(self):
        """Verify product update captures ONLY changed fields in old/new diff."""
        mock_db = MagicMock()
        service = AuditService(db=mock_db)

        old_dict = {
            "name": "Old Keyboard Name",
            "brand": "Keychron",
            "category": "Electronics",
        }
        new_dict = {
            "name": "New Keyboard Name",
            "brand": "Keychron",  # unchanged
            "category": "Computers",
        }

        service.log_product_updated(product_id=25, old_dict=old_dict, new_dict=new_dict, user_id="editor")

        assert mock_db.add.called
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.action == AuditAction.PRODUCT_UPDATED
        assert log_obj.entity_id == 25
        # Brand was unchanged, so brand must NOT be in old_values or new_values diff
        assert "brand" not in log_obj.old_values
        assert "brand" not in log_obj.new_values
        assert log_obj.old_values == {"name": "Old Keyboard Name", "category": "Electronics"}
        assert log_obj.new_values == {"name": "New Keyboard Name", "category": "Computers"}

    def test_audit_product_updated_no_changes(self):
        """If no values changed, audit log is not recorded."""
        mock_db = MagicMock()
        service = AuditService(db=mock_db)

        same_dict = {"name": "Identical", "brand": "BrandA"}
        result = service.log_product_updated(product_id=30, old_dict=same_dict, new_dict=same_dict)

        assert result is None
        assert not mock_db.add.called

    def test_audit_product_deactivated(self):
        """Verify product deactivation audit log."""
        mock_db = MagicMock()
        mock_product = MagicMock(id=50, sku="SKU-DEL", name="Discontinued Item")

        service = AuditService(db=mock_db)
        service.log_product_deactivated(mock_product, user_id="admin_del")

        assert mock_db.add.called
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.action == AuditAction.PRODUCT_DEACTIVATED
        assert log_obj.entity_id == 50
        assert log_obj.old_values == {"is_active": True}
        assert log_obj.new_values == {"is_active": False}

    def test_audit_bulk_upload_lifecycle(self):
        """Verify bulk upload start, completion, and failure audit records."""
        mock_db = MagicMock()
        service = AuditService(db=mock_db)

        # 1. Start
        service.log_bulk_upload_started(job_id=1, filename="catalog.csv", file_type="csv")
        start_log = mock_db.add.call_args[0][0]
        assert start_log.action == AuditAction.BULK_UPLOAD_STARTED
        assert start_log.log_metadata["filename"] == "catalog.csv"

        # 2. Completion
        service.log_bulk_upload_completed(
            job_id=1,
            filename="catalog.csv",
            total_rows=1000,
            successful_rows=1000,
            failed_rows=0,
            status="COMPLETED",
        )
        comp_log = mock_db.add.call_args[0][0]
        assert comp_log.action == AuditAction.BULK_UPLOAD_COMPLETED
        assert comp_log.log_metadata["successful_rows"] == 1000

        # 3. Failure
        service.log_bulk_upload_failed(job_id=2, filename="corrupt.csv", error_message="Empty file")
        fail_log = mock_db.add.call_args[0][0]
        assert fail_log.action == AuditAction.BULK_UPLOAD_FAILED
        assert "Empty file" in fail_log.description

    def test_audit_duplicate_review_confirm_and_reject(self):
        """Verify duplicate review confirmation and rejection audit records."""
        mock_db = MagicMock()
        service = AuditService(db=mock_db)

        # Confirm
        service.log_duplicate_review(
            candidate_id=200,
            decision="CONFIRMED",
            reason="Exact specification match",
            reviewer_id="reviewer_1",
        )
        conf_log = mock_db.add.call_args[0][0]
        assert conf_log.action == AuditAction.DUPLICATE_CONFIRMED
        assert conf_log.entity_id == 200
        assert conf_log.new_values["decision"] == "CONFIRMED"
        assert conf_log.user_id == "reviewer_1"

        # Reject
        service.log_duplicate_review(
            candidate_id=201,
            decision="REJECTED",
            reason="Completely different size",
            reviewer_id="reviewer_2",
        )
        rej_log = mock_db.add.call_args[0][0]
        assert rej_log.action == AuditAction.DUPLICATE_REJECTED
        assert rej_log.entity_id == 201
        assert rej_log.new_values["decision"] == "REJECTED"
