import uuid
import numpy as np
from typing import Dict, Any, Optional
from vehicle_reid.embeddings.extractor import VehicleEmbeddingExtractor
from vehicle_reid.vector_store import FaissVectorStore
from vehicle_reid.fusion import IdentityFusionEngine

class VehicleReIDPipeline:
    def __init__(
        self,
        extractor: VehicleEmbeddingExtractor,
        vector_store: FaissVectorStore,
        fusion_engine: IdentityFusionEngine,
        confidence_threshold: float = 0.75
    ):
        self.extractor = extractor
        self.vector_store = vector_store
        self.fusion_engine = fusion_engine
        self.confidence_threshold = confidence_threshold
        self._vehicle_counter = 1000

    def _generate_new_vehicle_id(self) -> str:
        """Generates a unique canonical vehicle ID."""
        self._vehicle_counter += 1
        return f"VEH_{self._vehicle_counter}"

    def process_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the end-to-end Person 2 workflow:
        1. Extracts appearance embedding from vehicle crop.
        2. Queries FAISS for visually similar historic observations.
        3. Fuses appearance, OCR, and attribute evidence.
        4. Resolves canonical identity (matches existing or mints a new vehicle ID).
        5. Persists the observation into the vector store.
        """
        image_crop = observation.get("image_crop")
        camera_id = observation.get("camera_id")
        timestamp = observation.get("timestamp")
        plate_text = observation.get("plate_text")
        attributes = observation.get("attributes", {})

        # Step 1: Extract L2-normalized embedding
        embedding = self.extractor.extract(image_crop)

        # Step 2: Query FAISS vector store for top candidates
        search_results = self.vector_store.search(query_embedding=embedding, top_k=5)

        best_match = None
        highest_confidence = 0.0

        # Step 3: Evaluate candidates using the fusion engine
        for result in search_results:
            fusion_result = self.fusion_engine.fuse(result, observation)
            if fusion_result["identity_confidence"] > highest_confidence:
                highest_confidence = fusion_result["identity_confidence"]
                best_match = fusion_result

        # Step 4: Resolve identity based on confidence threshold
        if best_match and highest_confidence >= self.confidence_threshold:
            canonical_vehicle_id = best_match["vehicle_id"]
            identity_confidence = highest_confidence
            appearance_confidence = best_match["appearance_confidence"]
            supporting_evidence = best_match["supporting_evidence"]
        else:
            # Mint a new canonical vehicle ID if no strong match is found
            canonical_vehicle_id = self._generate_new_vehicle_id()
            identity_confidence = 1.0  # First observation of this new vehicle
            appearance_confidence = 1.0
            supporting_evidence = {
                "matched_vector_id": None,
                "camera_id": camera_id,
                "timestamp": timestamp
            }

        # Step 5: Save current observation metadata and embedding into the store for future matching
        metadata = {
            "vehicle_id": canonical_vehicle_id,
            "camera_id": camera_id,
            "timestamp": timestamp,
            "plate_text": plate_text,
            "attributes": attributes
        }
        self.vector_store.add(embedding, metadata)

        # Step 6: Return structured output matching the Person 2 -> Person 3 contract
        return {
            "vehicle_id": canonical_vehicle_id,
            "camera_id": camera_id,
            "timestamp": timestamp,
            "plate_text": plate_text,
            "identity_confidence": identity_confidence,
            "appearance_confidence": appearance_confidence,
            "supporting_evidence": supporting_evidence
        }