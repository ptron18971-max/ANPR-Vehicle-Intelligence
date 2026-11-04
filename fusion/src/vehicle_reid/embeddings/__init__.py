"""Vehicle Appearance Embedding Extraction Module."""

from vehicle_reid.embeddings.base import BaseEmbeddingExtractor
from vehicle_reid.embeddings.extractor import VehicleEmbeddingExtractor
from vehicle_reid.embeddings.preprocessor import VehicleImagePreprocessor

__all__ = [
    "BaseEmbeddingExtractor",
    "VehicleEmbeddingExtractor",
    "VehicleImagePreprocessor",
]
