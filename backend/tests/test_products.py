"""
Test suite for the Product API endpoints (Stage 4).

Uses FastAPI TestClient with a mocked database session so that no
real Supabase connection is needed during automated tests.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def _make_product(**kwargs) -> MagicMock:
    """Build a mock Product ORM object with sensible defaults."""
    defaults = dict(
        id=1,
        sku="SKU-001",
        name="Test Product",
        description="A test product",
        brand="TestBrand",
        category="Electronics",
        subcategory="Gadgets",
        unit="pcs",
        attributes={"color": "blue", "weight_kg": 0.5},
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_service():
    """Patch ProductService so tests never hit the real database."""
    with patch("app.routers.products.ProductService") as MockService:
        yield MockService.return_value


# ---------------------------------------------------------------------------
# POST /api/products — Create
# ---------------------------------------------------------------------------

def test_create_product_success(client, mock_service):
    product = _make_product()
    mock_service.create_product.return_value = _product_response(product)

    resp = client.post("/api/products", json={
        "sku": "SKU-001",
        "name": "Test Product",
        "description": "A test product",
        "brand": "TestBrand",
        "category": "Electronics",
        "subcategory": "Gadgets",
        "unit": "pcs",
        "attributes": {"color": "blue"},
        "is_active": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku"] == "SKU-001"
    assert data["name"] == "Test Product"
    assert "id" in data
    assert "created_at" in data


def test_create_product_duplicate_sku(client, mock_service):
    from fastapi import HTTPException, status
    mock_service.create_product.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A product with SKU 'SKU-001' already exists.",
    )
    resp = client.post("/api/products", json={
        "sku": "SKU-001",
        "name": "Duplicate Product",
        "attributes": {},
    })
    assert resp.status_code == 409
    assert "SKU-001" in resp.json()["error"]


def test_create_product_missing_required_field(client, mock_service):
    # Missing `name` — Pydantic validation should reject at 422
    resp = client.post("/api/products", json={"sku": "SKU-002"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/products/{product_id} — Get by ID
# ---------------------------------------------------------------------------

def test_get_product_success(client, mock_service):
    product = _make_product()
    mock_service.get_product.return_value = _product_response(product)

    resp = client.get("/api/products/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1
    assert resp.json()["sku"] == "SKU-001"


def test_get_product_not_found(client, mock_service):
    from fastapi import HTTPException, status
    mock_service.get_product.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product with ID 999 not found.",
    )
    resp = client.get("/api/products/999")
    assert resp.status_code == 404
    assert "999" in resp.json()["error"]


# ---------------------------------------------------------------------------
# GET /api/products — List / paginate / filter
# ---------------------------------------------------------------------------

def test_list_products_default(client, mock_service):
    mock_service.list_products.return_value = _make_list_response([_make_product()])
    resp = client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 1


def test_list_products_pagination(client, mock_service):
    products = [_make_product(id=i, sku=f"SKU-{i:03d}") for i in range(1, 6)]
    mock_service.list_products.return_value = _make_list_response(products, page=2, page_size=5, total=25)
    resp = client.get("/api/products?page=2&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["page_size"] == 5
    assert data["pagination"]["total"] == 25
    assert data["pagination"]["has_prev"] is True


def test_list_products_search_filter(client, mock_service):
    mock_service.list_products.return_value = _make_list_response([_make_product(brand="TestBrand")])
    resp = client.get("/api/products?search=Test&brand=TestBrand&is_active=true")
    assert resp.status_code == 200
    # Verify the service was called with correct filter args
    call_kwargs = mock_service.list_products.call_args.kwargs
    assert call_kwargs["search"] == "Test"
    assert call_kwargs["brand"] == "TestBrand"
    assert call_kwargs["is_active"] is True


def test_list_products_page_size_exceeds_max(client, mock_service):
    # page_size > 100 should be rejected by Query validation (422)
    resp = client.get("/api/products?page_size=500")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/products/{product_id} — Update
# ---------------------------------------------------------------------------

def test_update_product_success(client, mock_service):
    updated = _make_product(name="Updated Name", brand="NewBrand")
    mock_service.update_product.return_value = _product_response(updated)

    resp = client.patch("/api/products/1", json={"name": "Updated Name", "brand": "NewBrand"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["brand"] == "NewBrand"


def test_update_product_duplicate_sku(client, mock_service):
    from fastapi import HTTPException, status
    mock_service.update_product.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A product with SKU 'SKU-999' already exists.",
    )
    resp = client.patch("/api/products/1", json={"sku": "SKU-999"})
    assert resp.status_code == 409


def test_update_product_not_found(client, mock_service):
    from fastapi import HTTPException, status
    mock_service.update_product.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product with ID 999 not found.",
    )
    resp = client.patch("/api/products/999", json={"name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/products/{product_id} — Deactivate (soft delete)
# ---------------------------------------------------------------------------

def test_deactivate_product_success(client, mock_service):
    deactivated = _make_product(is_active=False)
    mock_service.deactivate_product.return_value = _product_response(deactivated)

    resp = client.delete("/api/products/1")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_deactivate_product_not_found(client, mock_service):
    from fastapi import HTTPException, status
    mock_service.deactivate_product.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product with ID 999 not found.",
    )
    resp = client.delete("/api/products/999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from app.schemas.product import ProductListResponse, ProductPaginationMeta, ProductResponse
import math


def _product_response(product: MagicMock) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        brand=product.brand,
        category=product.category,
        subcategory=product.subcategory,
        unit=product.unit,
        attributes=product.attributes,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _make_list_response(
    products: list,
    page: int = 1,
    page_size: int = 20,
    total: int = None,
) -> ProductListResponse:
    total = total if total is not None else len(products)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return ProductListResponse(
        items=[_product_response(p) for p in products],
        pagination=ProductPaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
