import math
import logging
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.product_repository import ProductRepository
from app.services.audit_service import AuditService
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductPaginationMeta,
    ProductResponse,
    ProductUpdate,
)
from app.utils.exceptions import DatabaseError, DuplicateSKUError, ProductNotFoundError

logger = logging.getLogger(__name__)

# Maximum page_size we allow to prevent runaway queries against 85k records
MAX_PAGE_SIZE = 100


class ProductService:
    """Business logic layer for Product management."""

    def __init__(self, db: Session):
        self.repo = ProductRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_product_or_404(self, product_id: int):
        """Fetch product or raise a 404 HTTPException."""
        product = self.repo.get_by_id(product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found.",
            )
        return product

    def _handle_sku_conflict(self, exc: DuplicateSKUError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with SKU '{exc.sku}' already exists.",
        )

    def _handle_db_error(self, exc: DatabaseError):
        logger.error(f"Database error in ProductService: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred. Please try again later.",
        )

    # ------------------------------------------------------------------
    # Service Methods
    # ------------------------------------------------------------------

    def create_product(self, payload: ProductCreate) -> ProductResponse:
        """Create a new product after validating SKU uniqueness."""
        # Check uniqueness before hitting the DB constraint for a clear error message
        existing = self.repo.get_by_sku(payload.sku)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with SKU '{payload.sku}' already exists.",
            )
        try:
            product = self.repo.create(payload)
            self.audit.log_product_created(product)
            return ProductResponse.model_validate(product)
        except DuplicateSKUError as exc:
            self._handle_sku_conflict(exc)
        except DatabaseError as exc:
            self._handle_db_error(exc)

    def get_product(self, product_id: int) -> ProductResponse:
        """Return a single product by ID."""
        try:
            product = self._get_product_or_404(product_id)
            return ProductResponse.model_validate(product)
        except HTTPException:
            raise
        except DatabaseError as exc:
            self._handle_db_error(exc)

    def list_products(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sku: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> ProductListResponse:
        """Return a paginated, filtered product list."""
        # Sanitize page & page_size
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        try:
            items, total = self.repo.list_products(
                page=page,
                page_size=page_size,
                search=search,
                sku=sku,
                brand=brand,
                category=category,
                subcategory=subcategory,
                is_active=is_active,
            )
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            return ProductListResponse(
                items=[ProductResponse.model_validate(p) for p in items],
                pagination=ProductPaginationMeta(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    has_next=page < total_pages,
                    has_prev=page > 1,
                ),
            )
        except DatabaseError as exc:
            self._handle_db_error(exc)

    def update_product(self, product_id: int, payload: ProductUpdate) -> ProductResponse:
        """Apply a partial update to an existing product."""
        try:
            product = self._get_product_or_404(product_id)
            # If SKU is being changed, verify it doesn't clash with another product
            if payload.sku is not None and payload.sku != product.sku:
                existing = self.repo.get_by_sku(payload.sku)
                if existing is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"A product with SKU '{payload.sku}' already exists.",
                    )

            # Capture old values of requested fields for audit diff
            update_data = payload.model_dump(exclude_unset=True)
            old_dict = {k: getattr(product, k) for k in update_data.keys()}

            updated = self.repo.update(product, payload)
            new_dict = {k: getattr(updated, k) for k in update_data.keys()}

            self.audit.log_product_updated(product_id, old_dict, new_dict)
            return ProductResponse.model_validate(updated)
        except HTTPException:
            raise
        except DuplicateSKUError as exc:
            self._handle_sku_conflict(exc)
        except DatabaseError as exc:
            self._handle_db_error(exc)

    def deactivate_product(self, product_id: int) -> ProductResponse:
        """Soft-delete a product (sets is_active=False).
        Preserves all historical duplicate-detection records linked via FK.
        """
        try:
            product = self._get_product_or_404(product_id)
            deactivated = self.repo.deactivate(product)
            self.audit.log_product_deactivated(deactivated)
            return ProductResponse.model_validate(deactivated)
        except HTTPException:
            raise
        except DatabaseError as exc:
            self._handle_db_error(exc)
