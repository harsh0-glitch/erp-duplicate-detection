import math
import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.exceptions import DatabaseError, DuplicateSKUError

logger = logging.getLogger(__name__)


class ProductRepository:
    """Data access layer for Product operations against Supabase PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Fetch a single product by its primary key. Returns None if not found."""
        try:
            stmt = select(Product).where(Product.id == product_id)
            return self.db.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.error(f"DB error fetching product id={product_id}: {exc}")
            raise DatabaseError() from exc

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Fetch a single product by SKU. Returns None if not found."""
        try:
            stmt = select(Product).where(Product.sku == sku)
            return self.db.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.error(f"DB error fetching product sku={sku}: {exc}")
            raise DatabaseError() from exc

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
    ) -> Tuple[List[Product], int]:
        """Return a paginated, optionally filtered list of products.

        Returns a tuple of (items, total_count) to allow pagination metadata
        to be computed without an extra round-trip query.
        """
        try:
            stmt = select(Product)

            # --- Filters ---
            if is_active is not None:
                stmt = stmt.where(Product.is_active == is_active)

            if sku is not None:
                # Exact match – hits the unique index on products.sku
                stmt = stmt.where(Product.sku == sku)

            if brand is not None:
                stmt = stmt.where(Product.brand.ilike(f"%{brand}%"))

            if category is not None:
                stmt = stmt.where(Product.category.ilike(f"%{category}%"))

            if subcategory is not None:
                stmt = stmt.where(Product.subcategory.ilike(f"%{subcategory}%"))

            if search is not None:
                # Multi-field case-insensitive text search across name, brand,
                # category, and description – uses indexed columns where possible.
                term = f"%{search}%"
                stmt = stmt.where(
                    or_(
                        Product.name.ilike(term),
                        Product.brand.ilike(term),
                        Product.category.ilike(term),
                        Product.description.ilike(term),
                    )
                )

            # --- Count before pagination (same filters) ---
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = self.db.execute(count_stmt).scalar_one()

            # --- Pagination ---
            offset = (page - 1) * page_size
            stmt = stmt.order_by(Product.id).offset(offset).limit(page_size)

            items = list(self.db.execute(stmt).scalars().all())
            return items, total

        except SQLAlchemyError as exc:
            logger.error(f"DB error listing products: {exc}")
            raise DatabaseError() from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create(self, payload: ProductCreate) -> Product:
        """Insert a new product. Raises DuplicateSKUError on unique constraint violation."""
        try:
            product = Product(**payload.model_dump())
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            return product
        except IntegrityError as exc:
            self.db.rollback()
            # Unique constraint on products.sku
            if "sku" in str(exc.orig).lower() or "unique" in str(exc.orig).lower():
                raise DuplicateSKUError(payload.sku) from exc
            logger.error(f"Integrity error creating product: {exc}")
            raise DatabaseError() from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"DB error creating product: {exc}")
            raise DatabaseError() from exc

    def update(self, product: Product, payload: ProductUpdate) -> Product:
        """Apply a partial update to an existing product."""
        try:
            update_data = payload.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(product, field, value)
            self.db.commit()
            self.db.refresh(product)
            return product
        except IntegrityError as exc:
            self.db.rollback()
            sku = payload.sku or ""
            if "sku" in str(exc.orig).lower() or "unique" in str(exc.orig).lower():
                raise DuplicateSKUError(sku) from exc
            logger.error(f"Integrity error updating product id={product.id}: {exc}")
            raise DatabaseError() from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"DB error updating product id={product.id}: {exc}")
            raise DatabaseError() from exc

    def deactivate(self, product: Product) -> Product:
        """Soft-delete: set is_active=False. Preserves all FK references."""
        try:
            product.is_active = False
            self.db.commit()
            self.db.refresh(product)
            return product
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"DB error deactivating product id={product.id}: {exc}")
            raise DatabaseError() from exc
