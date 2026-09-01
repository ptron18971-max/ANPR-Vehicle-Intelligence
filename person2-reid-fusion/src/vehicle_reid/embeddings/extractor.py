"""High-level Vehicle Embedding Extractor."""

import logging
from typing import Any, List, Optional, Tuple, Union
import numpy as np

from vehicle_reid.embeddings.base import BaseEmbeddingExtractor
from vehicle_reid.embeddings.preprocessor import VehicleImagePreprocessor
from vehicle_reid.embeddings.backbones import (
    HAS_TORCH,
    HAS_TIMM,
    VehicleReIDNet,
    MockEmbeddingBackbone,
)

if HAS_TORCH:
    import torch

logger = logging.getLogger(__name__)


class VehicleEmbeddingExtractor(BaseEmbeddingExtractor):
    """Deep visual embedding extractor for vehicle re-identification."""

    def __init__(
        self,
        model_name: str = "resnet50",
        embedding_dim: int = 512,
        weights_path: Optional[str] = None,
        device: Optional[str] = None,
        image_size: Tuple[int, int] = (256, 256),
        use_clahe: bool = False,
        use_gem: bool = True,
        pretrained: bool = True,
    ):
        """Initialize vehicle embedding extractor.

        Args:
            model_name: Backbone architecture name (e.g. 'resnet50', 'convnext_tiny', 'mobilenetv3_large_100').
            embedding_dim: Dimensionality of output embeddings (default 512).
            weights_path: Path to custom fine-tuned weights checkpoint (e.g. VeRi-776 / VehicleID).
            device: Compute device ('cuda', 'mps', 'cpu', or None for auto-selection).
            image_size: Target crop size (H, W). Default (256, 256).
            use_clahe: Whether to apply CLAHE contrast enhancement for low-light frames.
            use_gem: Whether to use Generalized Mean (GeM) pooling over standard average pooling.
            pretrained: Whether to load ImageNet/timm pretrained weights if custom checkpoint is not supplied.
        """
        self._embedding_dim = embedding_dim
        self._model_name = model_name
        self.preprocessor = VehicleImagePreprocessor(image_size=image_size, use_clahe=use_clahe)

        # Device selection
        if device is None:
            if HAS_TORCH:
                if torch.cuda.is_available():
                    self._device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self._device = "mps"
                else:
                    self._device = "cpu"
            else:
                self._device = "cpu"
        else:
            self._device = device

        # Model initialization
        if HAS_TORCH:
            try:
                self.model = VehicleReIDNet(
                    backbone_name=model_name,
                    embedding_dim=embedding_dim,
                    pretrained=pretrained,
                    use_gem=use_gem,
                )
                if weights_path:
                    logger.info(f"Loading custom Re-ID weights from {weights_path}")
                    state_dict = torch.load(weights_path, map_location="cpu")
                    self.model.load_state_dict(state_dict, strict=False)

                self.model.to(self._device)
                self.model.eval()
                self._use_mock = False
            except Exception as e:
                logger.warning(f"Could not initialize PyTorch model ({e}). Falling back to mock extractor.")
                self.model = MockEmbeddingBackbone(embedding_dim=embedding_dim)
                self._use_mock = True
        else:
            logger.warning("PyTorch not installed. Using MockEmbeddingBackbone.")
            self.model = MockEmbeddingBackbone(embedding_dim=embedding_dim)
            self._use_mock = True

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    @property
    def device(self) -> str:
        return self._device

    def extract(self, image: Any) -> np.ndarray:
        """Extract a single normalized L2 embedding vector from a vehicle crop.

        Args:
            image: Vehicle crop (numpy array, PIL.Image, file path, etc.).

        Returns:
            np.ndarray: 1D float32 array of shape (embedding_dim,) with unit norm.
        """
        emb, _ = self.extract_with_quality(image)
        return emb

    def extract_with_quality(self, image: Any) -> Tuple[np.ndarray, float]:
        """Extract embedding and estimate visual crop quality score.

        Returns:
            Tuple[np.ndarray, float]: (embedding_vector, quality_score [0.0 - 1.0])
        """
        if self._use_mock:
            pil_img = self.preprocessor.load_image(image)
            quality = self.preprocessor.estimate_quality(pil_img)
            emb = self.model.generate(np.array(pil_img))
            return emb, quality

        tensor, quality = self.preprocessor.preprocess_torch(image)
        tensor = tensor.unsqueeze(0).to(self._device)

        with torch.no_grad():
            emb_tensor = self.model(tensor)
            emb = emb_tensor.squeeze(0).cpu().numpy().astype(np.float32)

        return emb, quality

    def extract_batch(
        self, images: List[Any], batch_size: int = 32
    ) -> np.ndarray:
        """Extract normalized embedding vectors for a batch of vehicle crops.

        Args:
            images: List of vehicle crops.
            batch_size: Inference batch size.

        Returns:
            np.ndarray: 2D float32 array of shape (N, embedding_dim) with unit rows.
        """
        embeddings, _ = self.extract_batch_with_quality(images, batch_size=batch_size)
        return embeddings

    def extract_batch_with_quality(
        self, images: List[Any], batch_size: int = 32
    ) -> Tuple[np.ndarray, List[float]]:
        """Extract embeddings and quality scores for a batch of vehicle crops.

        Returns:
            Tuple[np.ndarray, List[float]]: (embeddings_matrix [N, D], list of quality scores)
        """
        if len(images) == 0:
            return np.empty((0, self.embedding_dim), dtype=np.float32), []

        if self._use_mock:
            embs = []
            quals = []
            for img in images:
                emb, q = self.extract_with_quality(img)
                embs.append(emb)
                quals.append(q)
            return np.vstack(embs), quals

        all_embeddings = []
        all_qualities = []

        for i in range(0, len(images), batch_size):
            batch_images = images[i : i + batch_size]
            tensors = []
            for img in batch_images:
                t, q = self.preprocessor.preprocess_torch(img)
                tensors.append(t)
                all_qualities.append(q)

            batch_tensor = torch.stack(tensors, dim=0).to(self._device)
            with torch.no_grad():
                out = self.model(batch_tensor)
                all_embeddings.append(out.cpu().numpy().astype(np.float32))

        return np.vstack(all_embeddings), all_qualities
