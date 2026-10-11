from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Base schema for Product fields."""
    sku: str = Field(..., min_length=1, max_length=100, description="Unique product SKU / code")
    name: str = Field(..., min_length=1, max_length=255, description="Product title / name")
    description: Optional[str] = Field(None, description="Detailed product description")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    category: Optional[str] = Field(None, max_length=100, description="Primary product category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Product subcategory")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measure (e.g., pcs, kg, box)")
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extensible JSONB attribute specifications (e.g., dimensions, weight, color)",
    )
    is_active: bool = Field(True, description="Active status of the product")


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating an existing product (all fields optional)."""
    sku: Optional[str] = Field(None, min_length=1, max_length=100, description="Unique product SKU")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product title")
    description: Optional[str] = Field(None, description="Detailed product description")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    category: Optional[str] = Field(None, max_length=100, description="Primary category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Subcategory")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measure")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Extensible JSONB attributes")
    is_active: Optional[bool] = Field(None, description="Active status")


class ProductResponse(ProductBase):
    """Schema for serialized product response."""
    id: int = Field(..., description="Unique product identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class ProductPaginationMeta(BaseModel):
    """Pagination metadata for list queries."""
    total: int = Field(..., description="Total matching items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total available pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")


class ProductListResponse(BaseModel):
    """Paginated response containing product items and metadata."""
    items: List[ProductResponse]
    pagination: ProductPaginationMeta
