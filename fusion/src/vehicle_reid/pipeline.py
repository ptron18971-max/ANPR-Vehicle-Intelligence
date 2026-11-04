from typing import Dict, Any
from vehicle_reid.embeddings.extractor import VehicleEmbeddingExtractor
from vehicle_reid.vector_store import FaissVectorStore
from vehicle_reid.fusion import IdentityFusionEngine
from vehicle_reid.schemas import VehicleObservation, CanonicalVehicleIdentity, SupportingEvidence


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
        self.sync_vehicle_counter()

    def sync_vehicle_counter(self) -> None:
        """Re-syncs the vehicle-ID counter from whatever is currently in vector_store.

        Call this after `vector_store.load(...)` (or any other point where the
        store's contents changed underneath the pipeline) so newly minted
        "VEH_<n>" IDs never collide with IDs already present in the store. It is
        also called automatically at construction time, which covers the case
        where an already-populated (e.g. pre-loaded) vector_store is passed in.
        """
        max_existing = self.vector_store.get_max_vehicle_number()
        if max_existing is not None:
            self._vehicle_counter = max(self._vehicle_counter, max_existing)

    def _generate_new_vehicle_id(self) -> str:
        self._vehicle_counter += 1
        return f"VEH_{self._vehicle_counter}"

    def process_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Raises:
            pydantic.ValidationError: If `observation` doesn't match the
                VehicleObservation contract (missing/invalid fields).
        """
        obs = VehicleObservation(**observation)

        embedding = self.extractor.extract(obs.vehicle_crop if hasattr(obs, 'vehicle_crop') else obs.get('vehicle_crop'))
        search_results = self.vector_store.search(query_embedding=embedding, top_k=5)
        obs_dict = obs.model_dump() if hasattr(obs, 'model_dump') else obs.dict() if hasattr(obs, 'dict') else obs

        best_match = None
        highest_confidence = 0.0

        for result in search_results:
            fusion_result = self.fusion_engine.fuse(result, obs_dict)
            if fusion_result["identity_confidence"] > highest_confidence:
                highest_confidence = fusion_result["identity_confidence"]
                best_match = fusion_result

        if best_match and highest_confidence >= self.confidence_threshold:
            canonical_vehicle_id = best_match["vehicle_id"]
            identity_confidence = highest_confidence
            appearance_confidence = best_match["appearance_confidence"]
            supporting_evidence = SupportingEvidence(**best_match["supporting_evidence"])
        else:
            canonical_vehicle_id = self._generate_new_vehicle_id()
            # No candidate cleared the threshold, so we have zero corroborating
            # evidence that this is a re-appearance of a known vehicle. This is
            # the least-certain outcome of the pipeline (it may be a genuinely
            # new vehicle, OR a missed re-identification) -- report it as such
            # (0.0) rather than as a confident match, so downstream consumers
            # (e.g. trajectory fusion) don't over-trust an unverified new identity.
            identity_confidence = 0.0
            appearance_confidence = 0.0
            supporting_evidence = SupportingEvidence(
                appearance_similarity=0.0,
                plate_match_score=0.0,
                attribute_match_score=0.0,
                matched_against_id=None,
                match_strategy="new_registration",
                details={"reason": "no candidate cleared the confidence threshold"},
            )

        metadata = {
            "vehicle_id": canonical_vehicle_id,
            "camera_id": obs.camera_id,
            "timestamp": obs.timestamp,
            "plate_text": obs.plate_text if hasattr(obs, 'plate_text') else obs.get('plate_text'),
            "vehicle_type": obs.vehicle_type,
            "vehicle_color": obs.vehicle_color,
        }
        self.vector_store.add(embedding, metadata)

        identity = CanonicalVehicleIdentity(
            vehicle_id=canonical_vehicle_id,
            camera_id=obs.camera_id,
            timestamp=obs.timestamp,
            plate_text=obs.plate_text if hasattr(obs, 'plate_text') else obs.get('plate_text'),
            identity_confidence=identity_confidence,
            appearance_confidence=appearance_confidence,
            supporting_evidence=supporting_evidence,
        )
        return identity.model_dump() if hasattr(identity, 'model_dump') else identity.dict() if hasattr(identity, 'dict') else identity