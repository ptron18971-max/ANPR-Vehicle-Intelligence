# src/vehicle_reid/diagnostics.py
import json
import logging
from typing import Dict, Any

class FalseMatchLogger:
    def __init__(self, log_path: str = "false_match_diagnostics.jsonl"):
        self.logger = logging.getLogger("FalseMatchLogger")
        self.log_path = log_path

    def log_suspicious_association(
        self, 
        query_obs: Dict[str, Any], 
        candidate_meta: Dict[str, Any], 
        fusion_metrics: Dict[str, Any],
        reason: str
    ) -> None:
        """
        Captures near-misses, conflicting OCR vs visual evidence, or context violations.
        """
        entry = {
            "reason": reason,
            "query_camera": query_obs.get("camera_id"),
            "query_plate": query_obs.get("plate_text"),
            "candidate_camera": candidate_meta.get("camera_id"),
            "candidate_plate": candidate_meta.get("plate_text"),
            "metrics": fusion_metrics
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")