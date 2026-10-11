"""
Tests for Stage 5: CSV/Excel Bulk Upload API.

All tests mock the BulkUploadService so no real database or file I/O
is required during automated testing.
"""
import io
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.bulk_upload import BulkUploadInitResponse, BulkUploadJobResponse

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def _make_job_response(**kwargs) -> BulkUploadJobResponse:
    defaults = dict(
        id=1,
        filename="products.csv",
        file_type="csv",
        status="COMPLETED",
        total_rows=3,
        successful_rows=3,
        failed_rows=0,
        error_summary=[],
        created_at=NOW,
        completed_at=NOW,
    )
    defaults.update(kwargs)
    return BulkUploadJobResponse(**defaults)


def _make_init_response(**kwargs) -> BulkUploadInitResponse:
    defaults = dict(
        job_id=1,
        filename="products.csv",
        status="PENDING",
        message="Upload accepted.",
    )
    defaults.update(kwargs)
    return BulkUploadInitResponse(**defaults)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_service():
    with patch("app.routers.bulk_upload.BulkUploadService") as MockService:
        yield MockService.return_value


# ---------------------------------------------------------------------------
# Helper to build minimal CSV bytes
# ---------------------------------------------------------------------------

def _csv(rows: list[str], header: str = "sku,name,brand,category") -> bytes:
    lines = [header] + rows
    return "\n".join(lines).encode("utf-8")


def _xlsx(rows: list[dict]) -> bytes:
    import pandas as pd
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


# ===========================================================================
# POST /api/bulk-upload/products
# ===========================================================================

class TestUploadEndpoint:

    def test_valid_csv_upload_accepted(self, client, mock_service):
        """Valid CSV → 202 Accepted with job_id."""
        mock_service.create_upload_job.return_value = MagicMock(id=1, filename="products.csv")
        mock_service.process_upload.return_value = None  # BackgroundTask — void

        csv_bytes = _csv([
            "SKU-001,Widget A,Acme,Tools",
            "SKU-002,Widget B,Acme,Tools",
        ])
        resp = client.post(
            "/api/bulk-upload/products",
            files={"file": ("products.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "PENDING"

    def test_valid_xlsx_upload_accepted(self, client, mock_service):
        """Valid XLSX → 202 Accepted."""
        mock_service.create_upload_job.return_value = MagicMock(id=2, filename="products.xlsx")

        xlsx_bytes = _xlsx([
            {"sku": "SKU-001", "name": "Widget A"},
            {"sku": "SKU-002", "name": "Widget B"},
        ])
        resp = client.post(
            "/api/bulk-upload/products",
            files={"file": ("products.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 202
        assert resp.json()["status"] == "PENDING"

    def test_invalid_file_extension_rejected(self, client, mock_service):
        """Non-CSV/XLSX extension → 422."""
        resp = client.post(
            "/api/bulk-upload/products",
            files={"file": ("products.txt", b"sku,name\nA,B", "text/plain")},
        )
        assert resp.status_code == 422
        assert "Unsupported" in resp.json()["error"]

    def test_empty_file_rejected(self, client, mock_service):
        """Empty file → 422."""
        resp = client.post(
            "/api/bulk-upload/products",
            files={"file": ("products.csv", b"", "text/csv")},
        )
        assert resp.status_code == 422
        assert "empty" in resp.json()["error"].lower()

    def test_no_file_sent_rejected(self, client, mock_service):
        """Missing file field → 422 from FastAPI validation."""
        resp = client.post("/api/bulk-upload/products")
        assert resp.status_code == 422


# ===========================================================================
# File parser unit tests (no HTTP layer)
# ===========================================================================

class TestFileParser:

    def test_valid_csv_rows_parsed(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = _csv(
            ["SKU-001,Widget A,Acme,Tools", "SKU-002,Widget B,Brand,Cat"],
            header="sku,name,brand,category",
        )
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus=set()))
        valid = [(r, p) for r, p, e in results if e is None]
        assert len(valid) == 2
        assert valid[0][1]["sku"] == "SKU-001"

    def test_missing_required_column_detected(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_columns
        # CSV has no 'name' column
        csv_bytes = b"sku,brand\nSKU-001,Acme"
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        missing = validate_columns(list(df.columns))
        assert "name" in missing

    def test_missing_sku_value_produces_row_error(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = b"sku,name\n,Widget A"
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus=set()))
        _, parsed, error = results[0]
        assert parsed is None
        assert "sku" in error.lower()

    def test_duplicate_sku_within_file_detected(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = b"sku,name\nSKU-001,A\nSKU-001,B"
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus=set()))
        errors = [(r, e) for r, p, e in results if e is not None]
        assert len(errors) == 1
        assert "Duplicate SKU" in errors[0][1]

    def test_existing_db_sku_flagged(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = b"sku,name\nSKU-DB,Existing"
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus={"SKU-DB"}))
        _, parsed, error = results[0]
        assert parsed is None
        assert "already exists" in error

    def test_invalid_attributes_json_flagged(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = b'sku,name,attributes\nSKU-001,Widget,{not valid json}'
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus=set()))
        _, parsed, error = results[0]
        assert parsed is None
        assert "JSON" in error

    def test_mixed_valid_invalid_rows(self):
        from app.utils.file_parser import read_file_to_dataframe, validate_and_parse_rows
        csv_bytes = b"sku,name\nSKU-001,Good\n,Bad (no sku)\nSKU-003,Also Good"
        df = read_file_to_dataframe(csv_bytes, "test.csv")
        results = list(validate_and_parse_rows(df, existing_skus=set()))
        valid = [p for _, p, e in results if e is None]
        invalid = [e for _, p, e in results if e is not None]
        assert len(valid) == 2
        assert len(invalid) == 1


# ===========================================================================
# GET /api/bulk-upload/{job_id}
# ===========================================================================

class TestGetJobStatus:

    def test_get_existing_job(self, client, mock_service):
        mock_service.get_job.return_value = _make_job_response()
        resp = client.get("/api/bulk-upload/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["status"] == "COMPLETED"
        assert data["successful_rows"] == 3
        assert data["failed_rows"] == 0

    def test_get_job_not_found(self, client, mock_service):
        from fastapi import HTTPException
        mock_service.get_job.side_effect = HTTPException(status_code=404, detail="Upload job 999 not found.")
        resp = client.get("/api/bulk-upload/999")
        assert resp.status_code == 404

    def test_get_job_with_errors(self, client, mock_service):
        mock_service.get_job.return_value = _make_job_response(
            status="COMPLETED_WITH_ERRORS",
            total_rows=5,
            successful_rows=3,
            failed_rows=2,
            error_summary=[
                {"row": 2, "error": "'sku' is required"},
                {"row": 4, "error": "Duplicate SKU within file"},
            ],
        )
        resp = client.get("/api/bulk-upload/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED_WITH_ERRORS"
        assert len(data["error_summary"]) == 2
        assert data["failed_rows"] == 2
