"""Custom exception classes for the ERP Duplicate Detection System."""


class ProductNotFoundError(Exception):
    """Raised when a requested product does not exist."""
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product with ID {product_id} not found.")


class DuplicateSKUError(Exception):
    """Raised when a product SKU already exists in the database."""
    def __init__(self, sku: str):
        self.sku = sku
        super().__init__(f"A product with SKU '{sku}' already exists.")


class DatabaseError(Exception):
    """Raised for unexpected database errors."""
    def __init__(self, message: str = "An unexpected database error occurred."):
        super().__init__(message)
