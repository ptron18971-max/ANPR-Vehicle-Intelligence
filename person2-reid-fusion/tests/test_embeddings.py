"""Tests for Vehicle Image Preprocessor and Embedding Extractor."""

import numpy as np
from PIL import Image
import pytest

from vehicle_reid.embeddings.preprocessor import VehicleImagePreprocessor
from vehicle_reid.embeddings.extractor import VehicleEmbeddingExtractor
from vehicle_reid.embeddings.base import BaseEmbeddingExtractor


def create_dummy_crop(color=(255, 0, 0), size=(150, 150)) -> Image.Image:
    """Helper to create dummy RGB image."""
    return Image.new("RGB", size, color=color)


def test_preprocessor_formats():
    preprocessor = VehicleImagePreprocessor(image_size=(256, 256))

    # Test PIL image
    pil_img = create_dummy_crop()
    arr, quality = preprocessor.preprocess_numpy(pil_img)
    assert arr.shape == (3, 256, 256)
    assert 0.0 <= quality <= 1.0

    # Test numpy array (H, W, 3)
    np_img = np.zeros((100, 100, 3), dtype=np.uint8)
    arr2, quality2 = preprocessor.preprocess_numpy(np_img)
    assert arr2.shape == (3, 256, 256)


def test_embedding_extractor_single_and_batch():
    extractor = VehicleEmbeddingExtractor(embedding_dim=256)
    assert extractor.embedding_dim == 256

    img1 = create_dummy_crop(color=(255, 0, 0))
    img2 = create_dummy_crop(color=(0, 255, 0))

    # Single extraction
    emb1, q1 = extractor.extract_with_quality(img1)
    assert emb1.shape == (256,)
    # Verify L2 normalization
    norm1 = np.linalg.norm(emb1)
    assert pytest.approx(norm1, rel=1e-3) == 1.0

    # Batch extraction
    batch_embs, qualities = extractor.extract_batch_with_quality([img1, img2])
    assert batch_embs.shape == (2, 256)
    assert len(qualities) == 2

    # Similarity & distance
    sim = BaseEmbeddingExtractor.compute_similarity(emb1, emb1)
    assert pytest.approx(sim, abs=1e-3) == 1.0

    dist_mat = BaseEmbeddingExtractor.compute_distance_matrix(batch_embs, batch_embs)
    assert dist_mat.shape == (2, 2)
    assert pytest.approx(dist_mat[0, 0], abs=1e-3) == 0.0
    assert pytest.approx(dist_mat[1, 1], abs=1e-3) == 0.0
