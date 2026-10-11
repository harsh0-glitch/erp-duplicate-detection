from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseDuplicateModel(ABC):
    """Abstract Base Class for the Duplicate Detection ML Model.
    
    When the final ML model is ready, implement this interface and register it
    in the DuplicateDetectionService. No router, schema, or database changes
    will be required.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the ML model is loaded and ready for inference, False otherwise."""
        pass

    @abstractmethod
    def get_model_version(self) -> str:
        """Returns the model version identifier (e.g. 'erp-dup-v1.0.0')."""
        pass

    @abstractmethod
    def predict(
        self,
        query_product: Dict[str, Any],
        candidate_pool: List[Dict[str, Any]],
        threshold: float = 0.80,
        top_k: int = 5,
    ) -> Tuple[bool, Optional[float], List[Dict[str, Any]]]:
        """Perform duplicate detection between the query product and candidates.
        
        Args:
            query_product: Dict containing sku, name, brand, category, attributes, etc.
            candidate_pool: List of candidate product dicts retrieved from the catalog.
            threshold: Minimum similarity score to qualify as a duplicate.
            top_k: Maximum number of top matches to return.
            
        Returns:
            Tuple of:
            - is_duplicate (bool): True if at least one candidate exceeds threshold.
            - confidence_score (float | None): Overall determination confidence.
            - matches (list[dict]): Top matches, each containing:
                - 'matched_product_id': int
                - 'similarity_score': float (0.0 to 1.0)
                - 'confidence_score': float (optional)
                - 'matching_features': dict (breakdown of reasons/weights)
                - 'rank': int
        """
        pass
