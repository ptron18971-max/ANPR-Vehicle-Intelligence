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
        """
        Computes similarity between two license plates, handling partial reads 
        and minor character substitutions.
        """
        if not query_plate or not candidate_plate:
            return 0.5  # Neutral score if either plate is missing or unreadable

        q_plate = query_plate.strip().upper()
        c_plate = candidate_plate.strip().upper()

        if q_plate == c_plate:
            return 1.0

        # Use SequenceMatcher for fuzzy string comparison (handles OCR character confusions like 0 vs O, 1 vs I)
        matcher = difflib.SequenceMatcher(None, q_plate, c_plate)
        return float(matcher.ratio())

    def _calculate_attribute_match(self, query_attrs: Dict[str, Any], candidate_attrs: Dict[str, Any]) -> float:
        """
        Compares stable visual features like vehicle type and color.
        """
        if not query_attrs or not candidate_attrs:
            return 0.5

        matches = 0
        total_keys = 0

        for key in ["vehicle_type", "vehicle_color"]:
            if key in query_attrs and key in candidate_attrs:
                total_keys += 1
                if str(query_attrs[key]).strip().lower() == str(candidate_attrs[key]).strip().lower():
                    matches += 1

        if total_keys == 0:
            return 0.5

        return float(matches / total_keys)

    def fuse(
        self, 
        search_result: Dict[str, Any], 
        current_observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fuses visual appearance similarity from FAISS with OCR and attribute matching 
        to produce a final identity confidence score.
        """
        appearance_similarity = search_result.get("similarity_score", 0.0)
        # Normalize FAISS Inner Product score to [0, 1] range if needed (assuming L2-normalized embeddings, IP ranges from -1 to 1)
        appearance_score = max(0.0, min(1.0, (appearance_similarity + 1.0) / 2.0))

        candidate_metadata = search_result.get("metadata", {})
        
        ocr_score = self._calculate_ocr_match(
            current_observation.get("plate_text"),
            candidate_metadata.get("plate_text")
        )

        attribute_score = self._calculate_attribute_match(
            current_observation.get("attributes", {}),
            candidate_metadata.get("attributes", {})
        )

        # Weighted multi-evidence fusion
        final_confidence = (
            (self.appearance_weight * appearance_score) +
            (self.ocr_weight * ocr_score) +
            (self.attribute_weight * attribute_score)
        )

        # Determine if confidence clears the threshold to associate with an existing vehicle ID
        matched_vehicle_id = candidate_metadata.get("vehicle_id")

        return {
            "vehicle_id": matched_vehicle_id,
            "identity_confidence": round(float(final_confidence), 4),
            "appearance_confidence": round(float(appearance_score), 4),
            "ocr_confidence": round(float(ocr_score), 4),
            "attribute_confidence": round(float(attribute_score), 4),
            "supporting_evidence": {
                "matched_vector_id": search_result.get("vector_id"),
                "camera_id": candidate_metadata.get("camera_id"),
                "timestamp": candidate_metadata.get("timestamp")
            }
        }