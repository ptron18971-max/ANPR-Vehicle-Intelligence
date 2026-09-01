"""Tests for vehicle observation and canonical identity schemas."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from vehicle_reid.schemas import (
    VehicleObservation,
    CanonicalVehicleIdentity,
    SupportingEvidence,
)


def test_vehicle_observation_valid():
    obs = VehicleObservation(
        camera_id="C04",
        timestamp="2026-08-27T01:30:00Z",
        local_track_id=104,
        plate_text="KA01AB1234",
        plate_confidence=0.87,
        vehicle_type="sedan",
        vehicle_color="white",
        bbox=[100, 200, 300, 400],
    )
    assert obs.camera_id == "C04"
    assert obs.plate_confidence == 0.87
    assert obs.vehicle_color == "white"


def test_vehicle_observation_invalid_confidence():
    with pytest.raises(ValidationError):
        VehicleObservation(
            camera_id="C01",
            timestamp="2026-08-27T01:30:00Z",
            local_track_id=1,
            plate_confidence=1.5,  # Exceeds 1.0
        )


def test_canonical_identity_valid():
    evidence = SupportingEvidence(
        appearance_similarity=0.92,
        plate_match_score=0.95,
        attribute_match_score=1.0,
        matched_against_id="VEH_8421",
        match_strategy="multimodal_fusion",
    )
    identity = CanonicalVehicleIdentity(
        vehicle_id="VEH_8421",
        camera_id="C04",
        timestamp=datetime.utcnow(),
        plate_text="KA01AB1234",
        identity_confidence=0.93,
        appearance_confidence=0.91,
        supporting_evidence=evidence,
    )
    assert identity.vehicle_id == "VEH_8421"
    assert identity.identity_confidence == 0.93
    assert identity.supporting_evidence.appearance_similarity == 0.92
