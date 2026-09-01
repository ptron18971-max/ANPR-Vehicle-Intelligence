from typing import Dict, Any, Optional
import difflib


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

    def _calculate_ocr_match(self, query_plate: Optional[str], candidate_plate: Optional[str]) -> float:
        if not query_plate or not candidate_plate:
            return 0.5

        q_plate = query_plate.strip().upper()
        c_plate = candidate_plate.strip().upper()

        if q_plate == c_plate:
            return 1.0

        matcher = difflib.SequenceMatcher(None, q_plate, c_plate)
        return float(matcher.ratio())

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