# src/vehicle_reid/context.py
import math
from datetime import datetime
from typing import Dict, Any, Optional

class ContextualVerifier:
    def __init__(self, max_speed_kmh: float = 180.0):
        self.max_speed_kmh = max_speed_kmh  # Maximum reasonable vehicle speed limit threshold

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parses ISO format timestamps."""
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    def evaluate_spatiotemporal_plausibility(
        self, 
        current_observation: Dict[str, Any], 
        candidate_metadata: Dict[str, Any],
        camera_graph: Optional[Dict[str, Dict[str, float]]] = None
    ) -> float:
        """
        Evaluates physical feasibility based on camera topology and travel time.
        Returns a context score between 0.0 (impossible) and 1.0 (highly plausible).
        """
        curr_cam = current_observation.get("camera_id")
        cand_cam = candidate_metadata.get("camera_id")

        # Same camera observation
        if curr_cam == cand_cam:
            return 1.0

        curr_time = self._parse_timestamp(current_observation["timestamp"])
        cand_time = self._parse_timestamp(candidate_metadata["timestamp"])

        time_delta_seconds = abs((curr_time - cand_time).total_seconds())

        if time_delta_seconds <= 0:
            return 0.0  # Vehicle cannot be in two different cameras at the exact same second

        # Check topological camera graph distance from Person 3 if provided
        if camera_graph and curr_cam in camera_graph and cand_cam in camera_graph[curr_cam]:
            distance_meters = camera_graph[curr_cam][cand_cam]
            required_speed_kmh = (distance_meters / 1000.0) / (time_delta_seconds / 3600.0)

            if required_speed_kmh > self.max_speed_kmh:
                return 0.0  # Physically impossible speed (false association)
            
            # Normal speed profile score decay
            return max(0.2, 1.0 - (required_speed_kmh / self.max_speed_kmh))

        # Default fallback if distance matrix isn't explicitly passed: generic time window penalty
        if time_delta_seconds > 86400:  # 24 hours
            return 0.2

        return 0.8