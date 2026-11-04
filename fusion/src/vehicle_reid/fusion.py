from typing import Dict, Any, Optional
import re
from rapidfuzz import fuzz

# Classic OCR confusions for license-plate character recognition. Both plates
# are mapped through this table before comparison so that e.g. "O" and "0"
# (or "I"/"1", "S"/"5", "B"/"8", "Z"/"2") are treated as the same character
# rather than counted as an edit/typo -- this is the "handle character
# substitutions" requirement from the plate-matching spec.
_OCR_SUBSTITUTION_MAP = str.maketrans({
    "O": "0",
    "I": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
})


class IdentityFusionEngine:
    def __init__(
        self,
        appearance_weight: float = 0.5,
        ocr_weight: float = 0.3,
        attribute_weight: float = 0.2
    ):
        self.appearance_weight = appearance_weight
        self.ocr_weight = ocr_weight
        self.attribute_weight = attribute_weight

    @staticmethod
    def _normalize_plate(plate: str) -> str:
        """Uppercase, strip whitespace/punctuation, and canonicalize common OCR
        substitution errors so equivalent reads compare equal."""
        cleaned = re.sub(r"[^A-Z0-9]", "", plate.strip().upper())
        return cleaned.translate(_OCR_SUBSTITUTION_MAP)

    def _calculate_ocr_match(self, query_plate: Optional[str], candidate_plate: Optional[str]) -> float:
        if not query_plate or not candidate_plate:
            return 0.5

        q_plate = self._normalize_plate(query_plate)
        c_plate = self._normalize_plate(candidate_plate)

        if not q_plate or not c_plate:
            return 0.5

        if q_plate == c_plate:
            return 1.0

        # ratio(): standard edit-distance-based similarity for character-level
        # typos/misreads. partial_ratio(): best-matching substring, for partial
        # OCR reads where one string is a truncated/occluded version of the
        # other (e.g. a plate read missing its last digit due to glare).
        # Taking the max lets either failure mode score well without one
        # metric penalizing the other's best case.
        full_score = fuzz.ratio(q_plate, c_plate) / 100.0
        partial_score = fuzz.partial_ratio(q_plate, c_plate) / 100.0
        return float(max(full_score, partial_score))

    def _calculate_attribute_match(
        self,
        query_type: Optional[str],
        query_color: Optional[str],
        candidate_type: Optional[str],
        candidate_color: Optional[str],
    ) -> float:
        pairs = [(query_type, candidate_type), (query_color, candidate_color)]
        comparable = [(a, b) for a, b in pairs if a is not None and b is not None]

        if not comparable:
            return 0.5

        matches = sum(
            1 for a, b in comparable if str(a).strip().lower() == str(b).strip().lower()
        )
        return float(matches / len(comparable))

    def fuse(
        self,
        search_result: Dict[str, Any],
        current_observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        appearance_similarity = search_result.get("similarity_score", 0.0)
        appearance_score = max(0.0, min(1.0, (appearance_similarity + 1.0) / 2.0))

        candidate_metadata = search_result.get("metadata", {})

        ocr_score = self._calculate_ocr_match(
            current_observation.get("plate_text"),
            candidate_metadata.get("plate_text")
        )

        attribute_score = self._calculate_attribute_match(
            current_observation.get("vehicle_type"),
            current_observation.get("vehicle_color"),
            candidate_metadata.get("vehicle_type"),
            candidate_metadata.get("vehicle_color"),
        )

        final_confidence = (
            (self.appearance_weight * appearance_score) +
            (self.ocr_weight * ocr_score) +
            (self.attribute_weight * attribute_score)
        )

        matched_vehicle_id = candidate_metadata.get("vehicle_id")

        return {
            "vehicle_id": matched_vehicle_id,
            "identity_confidence": round(float(final_confidence), 4),
            "appearance_confidence": round(float(appearance_score), 4),
            "supporting_evidence": {
                "appearance_similarity": round(float(appearance_score), 4),
                "plate_match_score": round(float(ocr_score), 4),
                "attribute_match_score": round(float(attribute_score), 4),
                "matched_against_id": matched_vehicle_id,
                "match_strategy": "multimodal_fusion",
                "details": {
                    "matched_vector_id": search_result.get("vector_id"),
                    "camera_id": candidate_metadata.get("camera_id"),
                    "timestamp": candidate_metadata.get("timestamp"),
                }
            }
        }