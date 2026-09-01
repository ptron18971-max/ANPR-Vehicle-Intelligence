import numpy as np
import pytest
from unittest.mock import MagicMock
from vehicle_reid.pipeline import VehicleReIDPipeline

def test_pipeline_new_vehicle_minting():
    # Mock extractor to return a fixed 512-dim embedding
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = np.ones((512,), dtype=np.float32)

    # Mock vector store and fusion engine
    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = []
    
    mock_fusion_engine = MagicMock()

    pipeline = VehicleReIDPipeline(
        extractor=mock_extractor,
        vector_store=mock_vector_store,
        fusion_engine=mock_fusion_engine,
        confidence_threshold=0.75
    )

    observation = {
        "image_crop": np.zeros((100, 100, 3), dtype=np.uint8),
        "camera_id": "c_01",
        "timestamp": "2026-04-10T10:00:00Z",
        "plate_text": "KA01AB1234",
        "attributes": {"vehicle_type": "sedan", "vehicle_color": "white"}
    }

    result = pipeline.process_observation(observation)

    assert result["vehicle_id"].startswith("VEH_")
    assert result["camera_id"] == "c_01"
    assert result["plate_text"] == "KA01AB1234"
    assert result["identity_confidence"] == 1.0
    mock_vector_store.add.assert_called_once()