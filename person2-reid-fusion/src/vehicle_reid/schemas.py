"""Data contracts for Person 2 (Vehicle Re-ID & Identity Fusion).

Specifies input contract from Person 1 (CV + ANPR) and output contract to Person 3 (Trajectory & Spatio-Temporal Graph).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field


class VehicleObservation(BaseModel):
    """Input contract from Person 1 (Computer Vision + ANPR/OCR)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    camera_id: str = Field(..., description="Unique ID of the observing camera")
    timestamp: Union[datetime, str, float] = Field(
        ..., description="Timestamp of observation (ISO string, datetime object, or unix epoch)"
    )
    local_track_id: Union[int, str] = Field(
        ..., description="Camera-local tracker ID while vehicle remains visible"
    )
    plate_text: Optional[str] = Field(
        default=None, description="OCR extracted license plate text (normalized)"
    )
    plate_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="OCR confidence score [0.0 - 1.0]"
    )
    vehicle_type: Optional[str] = Field(
        default=None, description="Vehicle category (e.g. car, sedan, suv, bus, truck, motorcycle)"
    )
    vehicle_color: Optional[str] = Field(
        default=None, description="Vehicle dominant color (e.g. white, black, red, silver, blue)"
    )
    vehicle_crop: Optional[Any] = Field(
        default=None,
        description="Vehicle image crop (numpy array, PIL Image, base64 str, or filepath)",
    )
    bbox: Optional[Union[List[float], Tuple[float, float, float, float]]] = Field(
        default=None, description="Bounding box [x1, y1, x2, y2] in original camera frame"
    )


class SupportingEvidence(BaseModel):
    """Detailed evidence behind an identity assignment decision."""

    appearance_similarity: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Cosine similarity of Re-ID visual embedding"
    )
    plate_match_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Fuzzy string similarity score for plate text"
    )
    attribute_match_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Type and color consistency score"
    )
    matched_against_id: Optional[str] = Field(
        default=None, description="Candidate canonical ID matched against (if matched)"
    )
    match_strategy: str = Field(
        default="multimodal_fusion",
        description="Strategy used (e.g. multimodal_fusion, plate_exact, appearance_only, new_registration)",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional debug/audit telemetry"
    )


class CanonicalVehicleIdentity(BaseModel):
    """Output contract to Person 3 (Spatio-Temporal Graph + Trajectory)."""

    vehicle_id: str = Field(
        ..., description="Canonical global unique identifier for the physical vehicle"
    )
    camera_id: str = Field(..., description="Camera ID where observation was recorded")
    timestamp: Union[datetime, str, float] = Field(
        ..., description="Observation timestamp"
    )
    plate_text: Optional[str] = Field(
        default=None, description="Best consolidated plate text"
    )
    identity_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall fused confidence that this is the canonical vehicle"
    )
    appearance_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Visual Re-ID embedding confidence / quality score"
    )
    supporting_evidence: SupportingEvidence = Field(
        ..., description="Multi-modal evidence explaining the identity decision"
    )
