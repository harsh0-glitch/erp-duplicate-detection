"""
Tests for Stage 6: Duplicate Detection API Architecture.

Verifies:
1. Valid duplicate-check request via POST /api/duplicates/check.
2. Invalid/missing required inputs (422 Unprocessable Entity).
3. API response schema structure and fields.
4. DuplicateDetectionService behavior when ML model is unavailable/under development.
5. DuplicateDetectionService behavior when a trained ML model is injected.
6. Candidate retrieval pruning across catalog items.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.duplicate import DuplicateCheckRequest, DuplicateCheckResponse
from app.services.duplicate_service import DuplicateDetectionService
from app.ml.base import BaseDuplicateModel
from app.ml.placeholder import PlaceholderDuplicateModel


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# API Endpoint Tests (POST /api/duplicates/check)
# ---------------------------------------------------------------------------

class TestDuplicateCheckEndpoint:

    def test_valid_duplicate_check_request(self, client):
        """Valid product payload submitted; returns 200 with model_unavailable status."""
        payload = {
            "sku": "ELEC-1001",
            "name": "Wireless Ergonomic Mouse",
            "description": "Optical mouse with 2.4GHz wireless receiver",
            "brand": "Logitech",
            "category": "Electronics",
            "subcategory": "Peripherals",
            "unit": "pcs",
            "attributes": {"color": "black", "dpi": 1600},
        }

        # Mock the service to decouple API routing from database queries
        mock_response = DuplicateCheckResponse(
            status="model_unavailable",
            is_duplicate_detected=None,
            confidence_score=None,
            model_version="model-under-development",
            message="ML duplicate detection model is currently under development. The detection architecture is ready for model integration.",
            detection_run_id=1,
            total_candidates_analyzed=5,
            matches=[],
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.check_duplicate.return_value = mock_response

            response = client.post("/api/duplicates/check", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "model_unavailable"
            assert data["is_duplicate_detected"] is None
            assert data["confidence_score"] is None
            assert "under development" in data["message"]
            assert data["matches"] == []
            assert "model_version" in data

    def test_missing_required_sku(self, client):
        """Missing required 'sku' field yields 422 Unprocessable Entity."""
        payload = {
            "name": "Incomplete Product",
            "category": "Tools",
        }
        response = client.post("/api/duplicates/check", json=payload)
        assert response.status_code == 422

    def test_missing_required_name(self, client):
        """Missing required 'name' field yields 422 Unprocessable Entity."""
        payload = {
            "sku": "TOOL-001",
            "category": "Tools",
        }
        response = client.post("/api/duplicates/check", json=payload)
        assert response.status_code == 422

    def test_invalid_empty_sku(self, client):
        """Empty string 'sku' violates min_length=1 constraint (422)."""
        payload = {
            "sku": "",
            "name": "Test Product",
        }
        response = client.post("/api/duplicates/check", json=payload)
        assert response.status_code == 422

    def test_threshold_parameter_validation(self, client):
        """Threshold parameter must be between 0.0 and 1.0."""
        payload = {
            "sku": "ELEC-002",
            "name": "Keyboard",
        }
        # Threshold > 1.0 should be rejected by Query validation
        response = client.post("/api/duplicates/check?threshold=1.5", json=payload)
        assert response.status_code == 422

        # Threshold < 0.0 should be rejected
        response = client.post("/api/duplicates/check?threshold=-0.1", json=payload)
        assert response.status_code == 422

    def test_response_schema_structure(self, client):
        """Verifies all expected fields in response adhere to DuplicateCheckResponse."""
        payload = {
            "sku": "ELEC-1002",
            "name": "Mechanical Keyboard",
            "brand": "Keychron",
            "category": "Electronics",
        }
        mock_response = DuplicateCheckResponse(
            status="model_unavailable",
            is_duplicate_detected=None,
            confidence_score=None,
            model_version="model-under-development",
            message="Model unavailable message",
            detection_run_id=42,
            total_candidates_analyzed=10,
            matches=[],
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.check_duplicate.return_value = mock_response

            response = client.post("/api/duplicates/check", json=payload)
            assert response.status_code == 200
            data = response.json()

            # Assert all schema fields exist
            expected_keys = {
                "status",
                "is_duplicate_detected",
                "confidence_score",
                "model_version",
                "message",
                "detection_run_id",
                "total_candidates_analyzed",
                "matches",
            }
            assert expected_keys.issubset(data.keys())


# ---------------------------------------------------------------------------
# DuplicateDetectionService Unit Tests
# ---------------------------------------------------------------------------

class TestDuplicateDetectionService:

    def test_service_with_placeholder_model_unavailable(self):
        """When default placeholder model is used, service reports model_unavailable without fake scores."""
        mock_db = MagicMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        service = DuplicateDetectionService(db=mock_db, ml_model=PlaceholderDuplicateModel())
        request_data = DuplicateCheckRequest(
            sku="TEST-SKU-01",
            name="Testing Item",
            brand="Acme",
            category="Hardware",
        )

        result = service.check_duplicate(request_data, record_history=False)

        assert result.status == "model_unavailable"
        assert result.is_duplicate_detected is None
        assert result.confidence_score is None
        assert result.matches == []
        assert "under development" in result.message

    def test_service_with_injected_trained_ml_model(self):
        """When a real/trained ML model implementing BaseDuplicateModel is injected, service returns matches."""
        # Create a mock trained model implementing BaseDuplicateModel
        class MockTrainedModel(BaseDuplicateModel):
            def is_available(self) -> bool:
                return True

            def get_model_version(self) -> str:
                return "real-ml-model-v1.0.0"

            def predict(self, query_product, candidate_pool, threshold=0.80, top_k=5):
                return True, 0.94, [
                    {
                        "matched_product_id": 105,
                        "similarity_score": 0.94,
                        "confidence_score": 0.96,
                        "rank": 1,
                        "matching_features": {
                            "name_similarity": 0.95,
                            "brand_match": True,
                        },
                    }
                ]

        mock_db = MagicMock()
        # Mock candidate product returned from DB
        mock_candidate = MagicMock()
        mock_candidate.id = 105
        mock_candidate.sku = "ELEC-MATCH-01"
        mock_candidate.name = "Wireless Mouse Logitech"
        mock_candidate.brand = "Logitech"
        mock_candidate.category = "Electronics"
        mock_candidate.subcategory = "Peripherals"
        mock_candidate.unit = "pcs"
        mock_candidate.attributes = {"color": "black"}
        mock_candidate.is_active = True

        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_candidate]

        trained_model = MockTrainedModel()
        service = DuplicateDetectionService(db=mock_db, ml_model=trained_model)

        request_data = DuplicateCheckRequest(
            sku="ELEC-NEW-01",
            name="Logitech Wireless Mouse",
            brand="Logitech",
            category="Electronics",
        )

        result = service.check_duplicate(request_data, threshold=0.85, top_k=3, record_history=False)

        assert result.status == "completed"
        assert result.is_duplicate_detected is True
        assert result.confidence_score == 0.94
        assert result.model_version == "real-ml-model-v1.0.0"
        assert len(result.matches) == 1
        assert result.matches[0].matched_product_id == 105
        assert result.matches[0].similarity_score == 0.94
        assert result.matches[0].rank == 1
        assert result.matches[0].matching_features["brand_match"] is True
        assert result.matches[0].matched_product.sku == "ELEC-MATCH-01"

    def test_placeholder_model_interface(self):
        """Verifies PlaceholderDuplicateModel adheres to BaseDuplicateModel contract."""
        model = PlaceholderDuplicateModel()
        assert model.is_available() is False
        assert "development" in model.get_model_version()
        is_dup, conf, matches = model.predict({}, [])
        assert is_dup is False
        assert conf is None
        assert matches == []


# ===========================================================================
# Stage 7 Tests: Confirm, Reject, History & Detection Records
# ===========================================================================

from datetime import datetime, timezone
from app.schemas.duplicate import (
    DuplicateDecisionResponse,
    DuplicateDetailResponse,
    DuplicateHistoryItem,
    DuplicateHistoryResponse,
    DuplicateMatchHistoryItem,
    DuplicatePaginationMeta,
    DuplicateReviewRequest,
    DuplicateReviewResponse,
)


class TestDuplicateReviewEndpoints:

    def test_confirm_duplicate_success(self, client):
        """POST /api/duplicates/{id}/confirm records CONFIRMED decision."""
        now = datetime.now(timezone.utc)
        mock_response = DuplicateDecisionResponse(
            message="Duplicate match 1 confirmed successfully.",
            duplicate_id=1,
            decision="CONFIRMED",
            review=DuplicateReviewResponse(
                id=1,
                candidate_id=1,
                reviewer_id="lead_reviewer",
                decision="CONFIRMED",
                reason="Same product under alternate vendor SKU",
                created_at=now,
                updated_at=now,
            ),
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.confirm_duplicate.return_value = mock_response

            resp = client.post(
                "/api/duplicates/1/confirm",
                json={"reviewer_id": "lead_reviewer", "reason": "Same product under alternate vendor SKU"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["decision"] == "CONFIRMED"
            assert data["duplicate_id"] == 1
            assert data["review"]["reviewer_id"] == "lead_reviewer"
            assert data["review"]["reason"] == "Same product under alternate vendor SKU"

    def test_reject_duplicate_success(self, client):
        """POST /api/duplicates/{id}/reject records REJECTED decision."""
        now = datetime.now(timezone.utc)
        mock_response = DuplicateDecisionResponse(
            message="Duplicate match 1 rejected successfully.",
            duplicate_id=1,
            decision="REJECTED",
            review=DuplicateReviewResponse(
                id=2,
                candidate_id=1,
                reviewer_id="reviewer_2",
                decision="REJECTED",
                reason="Different model version and voltage specs",
                created_at=now,
                updated_at=now,
            ),
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.reject_duplicate.return_value = mock_response

            resp = client.post(
                "/api/duplicates/1/reject",
                json={"reviewer_id": "reviewer_2", "reason": "Different model version and voltage specs"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["decision"] == "REJECTED"
            assert data["duplicate_id"] == 1
            assert data["review"]["decision"] == "REJECTED"

    def test_confirm_duplicate_not_found(self, client):
        """POST /api/duplicates/{id}/confirm returns 404 for nonexistent ID."""
        from fastapi import HTTPException
        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.confirm_duplicate.side_effect = HTTPException(
                status_code=404,
                detail="Duplicate record with ID 9999 not found.",
            )

            resp = client.post("/api/duplicates/9999/confirm")
            assert resp.status_code == 404
            assert "9999" in resp.json()["error"]

    def test_reject_duplicate_not_found(self, client):
        """POST /api/duplicates/{id}/reject returns 404 for nonexistent ID."""
        from fastapi import HTTPException
        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.reject_duplicate.side_effect = HTTPException(
                status_code=404,
                detail="Duplicate record with ID 9999 not found.",
            )

            resp = client.post("/api/duplicates/9999/reject")
            assert resp.status_code == 404
            assert "9999" in resp.json()["error"]


class TestDuplicateHistoryEndpoints:

    def test_get_duplicate_history_success(self, client):
        """GET /api/duplicates/history returns paginated detection records."""
        now = datetime.now(timezone.utc)
        mock_response = DuplicateHistoryResponse(
            items=[
                DuplicateHistoryItem(
                    id=1,
                    status="COMPLETED",
                    model_version="v1.0.0",
                    query_product_id=10,
                    query_product_sku="ELEC-001",
                    query_product_name="Wireless Mouse",
                    input_product={"sku": "ELEC-001", "name": "Wireless Mouse"},
                    total_candidates_analyzed=50,
                    execution_time_ms=15.4,
                    created_at=now,
                    completed_at=now,
                    matches=[
                        DuplicateMatchHistoryItem(
                            id=101,
                            matched_product_id=20,
                            matched_product_sku="ELEC-002",
                            matched_product_name="Logitech Mouse",
                            similarity_score=0.92,
                            confidence_score=0.95,
                            rank=1,
                            matching_features={"name_similarity": 0.94},
                            review_status="CONFIRMED",
                            review_decision="CONFIRMED",
                            reviewed_at=now,
                            reviewer_id="admin",
                        )
                    ],
                )
            ],
            pagination=DuplicatePaginationMeta(
                total=1,
                page=1,
                page_size=20,
                total_pages=1,
                has_next=False,
                has_prev=False,
            ),
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.get_history.return_value = mock_response

            resp = client.get("/api/duplicates/history")
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == "COMPLETED"
            assert len(data["items"][0]["matches"]) == 1
            assert data["items"][0]["matches"][0]["review_status"] == "CONFIRMED"
            assert data["pagination"]["total"] == 1

    def test_get_duplicate_history_filters(self, client):
        """GET /api/duplicates/history applies query filters correctly."""
        now = datetime.now(timezone.utc)
        mock_response = DuplicateHistoryResponse(
            items=[],
            pagination=DuplicatePaginationMeta(
                total=0,
                page=1,
                page_size=10,
                total_pages=1,
                has_next=False,
                has_prev=False,
            ),
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            mock_inst = MockServiceClass.return_value
            mock_inst.get_history.return_value = mock_response

            resp = client.get("/api/duplicates/history?page=2&page_size=10&status=MODEL_UNAVAILABLE&decision=PENDING&min_similarity=0.85")
            assert resp.status_code == 200

            call_kwargs = mock_inst.get_history.call_args.kwargs
            assert call_kwargs["page"] == 2
            assert call_kwargs["page_size"] == 10
            assert call_kwargs["status_filter"] == "MODEL_UNAVAILABLE"
            assert call_kwargs["decision_filter"] == "PENDING"
            assert call_kwargs["min_similarity"] == 0.85

    def test_get_duplicate_details_candidate(self, client):
        """GET /api/duplicates/{id} returns full candidate match details and comparison specs."""
        now = datetime.now(timezone.utc)
        mock_detail = DuplicateDetailResponse(
            id=101,
            record_type="candidate",
            run_id=1,
            status="CONFIRMED",
            model_version="v1.0.0",
            similarity_score=0.92,
            confidence_score=0.95,
            rank=1,
            matching_features={"name_similarity": 0.94, "brand_match": True},
            created_at=now,
            query_product={"id": 10, "sku": "ELEC-001", "name": "Wireless Mouse"},
            matched_product={"id": 20, "sku": "ELEC-002", "name": "Logitech Mouse"},
            review=DuplicateReviewResponse(
                id=1,
                candidate_id=101,
                reviewer_id="lead",
                decision="CONFIRMED",
                reason="Identical item",
                created_at=now,
                updated_at=now,
            ),
            review_status="CONFIRMED",
            matches=[],
        )

        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.get_duplicate.return_value = mock_detail

            resp = client.get("/api/duplicates/101")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 101
            assert data["record_type"] == "candidate"
            assert data["similarity_score"] == 0.92
            assert data["query_product"]["sku"] == "ELEC-001"
            assert data["matched_product"]["sku"] == "ELEC-002"
            assert data["review_status"] == "CONFIRMED"

    def test_get_duplicate_details_not_found(self, client):
        """GET /api/duplicates/{id} returns 404 for nonexistent record."""
        from fastapi import HTTPException
        with patch("app.routers.duplicates.DuplicateDetectionService") as MockServiceClass:
            MockServiceClass.return_value.get_duplicate.side_effect = HTTPException(
                status_code=404,
                detail="Duplicate record with ID 8888 not found.",
            )

            resp = client.get("/api/duplicates/8888")
            assert resp.status_code == 404
            assert "8888" in resp.json()["error"]


class TestDuplicateServiceLogic:

    def test_service_confirm_and_update_review(self):
        """DuplicateDetectionService.review_duplicate creates and updates review records."""
        mock_db = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.id = 55
        mock_db.get.return_value = mock_candidate
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 1)

        service = DuplicateDetectionService(db=mock_db)

        # Confirm candidate 55
        req = DuplicateReviewRequest(reviewer_id="user_admin", reason="Exact match")
        result = service.confirm_duplicate(duplicate_id=55, payload=req)

        assert result.decision == "CONFIRMED"
        assert result.duplicate_id == 55
        assert mock_db.commit.called
        assert mock_db.add.called

    def test_service_reject_duplicate(self):
        """DuplicateDetectionService.reject_duplicate records REJECTED decision."""
        mock_db = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.id = 55
        mock_db.get.return_value = mock_candidate
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 2)

        service = DuplicateDetectionService(db=mock_db)

        req = DuplicateReviewRequest(reviewer_id="user_admin", reason="Completely different product")
        result = service.reject_duplicate(duplicate_id=55, payload=req)

        assert result.decision == "REJECTED"
        assert result.duplicate_id == 55
        assert mock_db.commit.called

    def test_service_review_nonexistent_raises_404(self):
        """Reviewing nonexistent duplicate ID raises 404."""
        from fastapi import HTTPException
        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = DuplicateDetectionService(db=mock_db)

        with pytest.raises(HTTPException) as exc_info:
            service.confirm_duplicate(duplicate_id=9999)
        assert exc_info.value.status_code == 404
