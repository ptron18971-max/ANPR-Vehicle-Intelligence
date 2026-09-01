"""Base abstract interface for vehicle feature extraction."""

from abc import ABC, abstractmethod
from typing import Any, List, Union
import numpy as np


class BaseEmbeddingExtractor(ABC):
    """Abstract interface for extracting vehicle visual appearance embeddings."""

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of the output embedding vector."""
        pass

    @property
    @abstractmethod
    def device(self) -> str:
        """Target device (cpu, cuda, mps)."""
        pass

    @abstractmethod
    def extract(self, image: Any) -> np.ndarray:
        """Extract a single normalized embedding vector from a vehicle crop.

        Args:
            image: Vehicle crop as np.ndarray (RGB/BGR), PIL.Image, or file path.

        Returns:
            np.ndarray: 1D float32 array of shape (embedding_dim,) with unit L2 norm.
        """
        pass

    @abstractmethod
    def extract_batch(self, images: List[Any], batch_size: int = 32) -> np.ndarray:
        """Extract normalized embedding vectors for a batch of vehicle crops.

        Args:
            images: List of vehicle crops.
            batch_size: Batch size for model inference.

        Returns:
            np.ndarray: 2D float32 array of shape (N, embedding_dim) where each row has unit L2 norm.
        """
        pass

    @staticmethod
    def compute_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two unit-normalized embeddings.

        Args:
            emb1: 1D array of shape (D,)
            emb2: 1D array of shape (D,)

        Returns:
            float: Cosine similarity in range [-1.0, 1.0], clamped to [0.0, 1.0] for Re-ID.
        """
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 < 1e-7 or norm2 < 1e-7:
            return 0.0
        sim = float(np.dot(emb1, emb2) / (norm1 * norm2))
        return max(0.0, min(1.0, (sim + 1.0) / 2.0))

    @staticmethod
    def compute_distance_matrix(queries: np.ndarray, gallery: np.ndarray) -> np.ndarray:
        """Compute pairwise cosine distance matrix between queries and gallery.

        Args:
            queries: 2D array of shape (N, D)
            gallery: 2D array of shape (M, D)

        Returns:
            np.ndarray: Pairwise cosine distance matrix of shape (N, M) in range [0.0, 2.0].
        """
        # Ensure 2D
        if queries.ndim == 1:
            queries = queries.reshape(1, -1)
        if gallery.ndim == 1:
            gallery = gallery.reshape(1, -1)

        # Assuming L2 normalized vectors, Cosine Distance = 1.0 - (Q @ G.T)
        sim_matrix = np.matmul(queries, gallery.T)
        dist_matrix = 1.0 - sim_matrix
        return np.clip(dist_matrix, 0.0, 2.0)
