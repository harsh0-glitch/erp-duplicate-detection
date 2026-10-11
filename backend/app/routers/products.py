from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/products", tags=["Products"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)


# ---------------------------------------------------------------------------
# POST /api/products — Create a product
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a new product record. SKU must be unique across the catalog.",
)
def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    return service.create_product(payload)


# ---------------------------------------------------------------------------
# GET /api/products — List / search / filter products
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products with pagination and optional filters",
    description=(
        "Returns a paginated list of products. Supports optional filters: "
        "`search` (multi-field text), `sku` (exact), `brand`, `category`, "
        "`subcategory`, `is_active`. Default page_size=20, max page_size=100."
    ),
)
def list_products(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    search: Optional[str] = Query(None, description="Search across name, brand, category, description"),
    sku: Optional[str] = Query(None, description="Filter by exact SKU"),
    brand: Optional[str] = Query(None, description="Filter by brand (partial match)"),
    category: Optional[str] = Query(None, description="Filter by category (partial match)"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: ProductService = Depends(get_product_service),
):
    return service.list_products(
        page=page,
        page_size=page_size,
        search=search,
        sku=sku,
        brand=brand,
        category=category,
        subcategory=subcategory,
        is_active=is_active,
    )


# ---------------------------------------------------------------------------
# GET /api/products/{product_id} — Get a single product
# ---------------------------------------------------------------------------
@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    description="Retrieve a single product by its unique database ID.",
)
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    return service.get_product(product_id)


# ---------------------------------------------------------------------------
# PATCH /api/products/{product_id} — Partial update
# ---------------------------------------------------------------------------
@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Partially update a product",
    description="Update one or more fields of an existing product. Only provided fields are updated.",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    return service.update_product(product_id, payload)


# ---------------------------------------------------------------------------
# DELETE /api/products/{product_id} — Soft delete (deactivate)
# ---------------------------------------------------------------------------
@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Deactivate a product (soft delete)",
    description=(
        "Sets `is_active=False` on the product (soft delete). "
        "The product record and all historical duplicate-detection references are preserved. "
        "Use PATCH to reactivate a product by setting is_active=true."
    ),
)
def deactivate_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    return service.deactivate_product(product_id)
