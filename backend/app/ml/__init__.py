"""Machine Learning interface and model adapters package."""

from app.ml.base import BaseDuplicateModel
from app.ml.placeholder import PlaceholderDuplicateModel

__all__ = [
    "BaseDuplicateModel",
    "PlaceholderDuplicateModel",
]
