from datetime import datetime
from sqlalchemy import (
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """Product model designed for catalog scale (~85,000+ items).
    
    Includes indexed search fields, soft deletion flag (is_active),
    and JSONB attributes column for extensible ERP specifications.
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., pcs, box, kg
    attributes: Mapped[dict] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    detection_runs = relationship(
        "DuplicateDetectionRun",
        back_populates="query_product",
        foreign_keys="DuplicateDetectionRun.query_product_id",
    )

    __table_args__ = (
        # Composite index for category and brand filtering across 85k items
        Index("ix_products_category_brand", "category", "brand"),
        # GIN index for high-performance arbitrary JSONB attribute queries
        Index("ix_products_attributes_gin", "attributes", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name[:30]}')>"
