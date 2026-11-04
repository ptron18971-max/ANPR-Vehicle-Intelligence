import numpy as np
import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError
from vehicle_reid.pipeline import VehicleReIDPipeline
from vehicle_reid.vector_store import FaissVectorStore


def _make_pipeline(mock_extractor, mock_vector_store, mock_fusion_engine, threshold=0.75):
    # A real (empty or freshly-constructed) FaissVectorStore returns None here;
    # MagicMock needs this set explicitly or arithmetic on the counter blows up.
    mock_vector_store.get_max_vehicle_number.return_value = None
    return VehicleReIDPipeline(
        extractor=mock_extractor,
        vector_store=mock_vector_store,
        fusion_engine=mock_fusion_engine,
        confidence_threshold=threshold,
    )


def test_pipeline_new_vehicle_minting():
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = np.ones((512,), dtype=np.float32)

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = []

    mock_fusion_engine = MagicMock()

    pipeline = _make_pipeline(mock_extractor, mock_vector_store, mock_fusion_engine)

    # Field names must match the VehicleObservation contract: vehicle_crop
    # (not image_crop), flat vehicle_type/vehicle_color (not a nested
    # "attributes" dict), and local_track_id is required.
    observation = {
        "camera_id": "c_01",
        "timestamp": "2026-04-10T10:00:00Z",
        "local_track_id": 42,
        "plate_text": "KA01AB1234",
        "vehicle_type": "sedan",
        "vehicle_color": "white",
        "vehicle_crop": np.zeros((100, 100, 3), dtype=np.uint8),
    }

    result = pipeline.process_observation(observation)

    assert result["vehicle_id"].startswith("VEH_")
    assert result["camera_id"] == "c_01"
    assert result["plate_text"] == "KA01AB1234"
    # New registrations carry zero corroborating evidence (no candidate cleared
    # the threshold), so confidence should reflect that uncertainty rather than
    # claiming a confident match. See Issue #4.
    assert result["identity_confidence"] == 0.0
    assert result["appearance_confidence"] == 0.0
    assert result["supporting_evidence"]["match_strategy"] == "new_registration"
    mock_vector_store.add.assert_called_once()


def test_pipeline_matches_existing_vehicle_above_threshold():
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = np.ones((512,), dtype=np.float32)

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {
            "vector_id": 7,
            "similarity_score": 0.95,
            "metadata": {
                "vehicle_id": "VEH_1001",
                "camera_id": "c_00",
                "timestamp": "2026-04-10T09:58:00Z",
                "plate_text": "KA01AB1234",
                "vehicle_type": "sedan",
                "vehicle_color": "white",
            },
        }
    ]

    mock_fusion_engine = MagicMock()
    mock_fusion_engine.fuse.return_value = {
        "vehicle_id": "VEH_1001",
        "identity_confidence": 0.91,
        "appearance_confidence": 0.97,
        "supporting_evidence": {
            "appearance_similarity": 0.97,
            "plate_match_score": 1.0,
            "attribute_match_score": 1.0,
            "matched_against_id": "VEH_1001",
            "match_strategy": "multimodal_fusion",
            "details": {"matched_vector_id": 7, "camera_id": "c_00", "timestamp": "2026-04-10T09:58:00Z"},
        },
    }

    pipeline = _make_pipeline(mock_extractor, mock_vector_store, mock_fusion_engine)

    observation = {
        "camera_id": "c_04",
        "timestamp": "2026-04-10T10:00:00Z",
        "local_track_id": 5,
        "plate_text": "KA01AB1234",
        "vehicle_type": "sedan",
        "vehicle_color": "white",
        "vehicle_crop": np.zeros((100, 100, 3), dtype=np.uint8),
    }

    result = pipeline.process_observation(observation)

    assert result["vehicle_id"] == "VEH_1001"
    assert result["identity_confidence"] == 0.91
    assert result["supporting_evidence"]["match_strategy"] == "multimodal_fusion"
    mock_vector_store.add.assert_called_once()


def test_pipeline_rejects_malformed_observation():
    mock_extractor = MagicMock()
    mock_vector_store = MagicMock()
    mock_fusion_engine = MagicMock()

    pipeline = _make_pipeline(mock_extractor, mock_vector_store, mock_fusion_engine)

    # Missing required fields (camera_id, timestamp, local_track_id) should
    # fail validation up front rather than proceeding with silently missing data.
    with pytest.raises(ValidationError):
        pipeline.process_observation({"plate_text": "KA01AB1234"})


def test_pipeline_syncs_vehicle_counter_from_preloaded_store():
    """Regression test for Issue #5: restarting/reloading must not re-mint
    a "VEH_<n>" ID that already exists in the (persisted) vector store."""
    real_store = FaissVectorStore(dimension=512)
    # Simulate a store that was already populated (e.g. via .load()) before
    # this pipeline instance was constructed, with the highest ID being VEH_1042.
    real_store.metadata_store = {
        0: {"vehicle_id": "VEH_1001", "camera_id": "c_00"},
        1: {"vehicle_id": "VEH_1042", "camera_id": "c_02"},
    }

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = np.ones((512,), dtype=np.float32)
    mock_fusion_engine = MagicMock()

    pipeline = VehicleReIDPipeline(
        extractor=mock_extractor,
        vector_store=real_store,
        fusion_engine=mock_fusion_engine,
    )

    assert pipeline._vehicle_counter == 1042

    observation = {
        "camera_id": "c_01",
        "timestamp": "2026-04-10T10:00:00Z",
        "local_track_id": 42,
        "plate_text": "KA01AB1234",
        "vehicle_type": "sedan",
        "vehicle_color": "white",
        "vehicle_crop": np.zeros((100, 100, 3), dtype=np.uint8),
    }
    # No candidates in the FAISS index yet (only metadata was seeded above),
    # so this mints a new ID -- it must continue from 1042, not restart at 1000.
    result = pipeline.process_observation(observation)
    assert result["vehicle_id"] == "VEH_1043"


def test_sync_vehicle_counter_can_be_called_after_load():
    """The public sync method should also work if called after vector_store.load()
    changes the store's contents post-construction."""
    real_store = FaissVectorStore(dimension=512)
    mock_extractor = MagicMock()
    mock_fusion_engine = MagicMock()

    pipeline = VehicleReIDPipeline(
        extractor=mock_extractor,
        vector_store=real_store,
        fusion_engine=mock_fusion_engine,
    )
    assert pipeline._vehicle_counter == 1000

    # Simulate vector_store.load(...) populating the store after construction.
    real_store.metadata_store = {5: {"vehicle_id": "VEH_2500"}}
    pipeline.sync_vehicle_counter()

    assert pipeline._vehicle_counter == 2500