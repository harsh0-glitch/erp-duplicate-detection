from typing import Any, Dict, List, Optional, Tuple
from app.ml.base import BaseDuplicateModel


class PlaceholderDuplicateModel(BaseDuplicateModel):
    """Temporary placeholder for development while the ML model is being trained.
    
    This class explicitly indicates that no trained ML model is currently loaded.
    It does NOT generate fake similarity scores or invented predictions.
    
    When your ML team completes the model, create a new class implementing
    BaseDuplicateModel (e.g. `TrainedDuplicateModel`) and swap it in.
    """

    def __init__(self, version: str = "model-under-development"):
        self.version = version

    def is_available(self) -> bool:
        """Indicates the model is under development and not ready for inference."""
        return False

    def get_model_version(self) -> str:
        return self.version

    def predict(
        self,
        query_product: Dict[str, Any],
        candidate_pool: List[Dict[str, Any]],
        threshold: float = 0.80,
        top_k: int = 5,
    ) -> Tuple[bool, Optional[float], List[Dict[str, Any]]]:
        """Placeholder does not run inference; returns empty matches."""
        return False, None, []
