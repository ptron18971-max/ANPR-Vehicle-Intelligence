# tests/evaluate_fusion.py
from typing import List, Dict, Any
from vehicle_reid.fusion import IdentityFusionEngine

def evaluate_fusion_strategy(ground_truth_pairs: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compares baseline plate-only matching against multi-evidence fusion.
    """
    fusion_engine = IdentityFusionEngine()
    
    plate_only_correct = 0
    fusion_correct = 0
    total = len(ground_truth_pairs)

    for item in ground_truth_pairs:
        obs = item["query"]
        candidate = item["candidate"]
        is_same_vehicle = item["is_match"]

        # 1. Baseline: Plate-only exact match
        plate_match = (obs.get("plate_text") == candidate.get("metadata", {}).get("plate_text"))
        if plate_match == is_same_vehicle:
            plate_only_correct += 1

        # 2. Richer Multi-Evidence Fusion
        fused = fusion_engine.fuse(candidate, obs)
        fusion_match = fused["identity_confidence"] >= 0.75
        if fusion_match == is_same_vehicle:
            fusion_correct += 1

    return {
        "plate_only_accuracy": round(plate_only_correct / total, 4) if total > 0 else 0.0,
        "fusion_accuracy": round(fusion_correct / total, 4) if total > 0 else 0.0
    }