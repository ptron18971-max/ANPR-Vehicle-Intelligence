"""Flag trajectory transitions whose observed travel time deviates far
from the camera graph's expected range.
"""
from datetime import datetime

from analytics.travel_time import expected_range
from config import TRAVEL_TIME_DEVIATION_THRESHOLD


def check_trajectory(graph, trajectory_record, threshold=TRAVEL_TIME_DEVIATION_THRESHOLD):
    """Return a list of anomaly dicts, one per transition that exceeds
    threshold times the expected max travel time. Empty list means no
    anomaly found.
    """
    anomalies = []
    obs = trajectory_record["trajectory"]
    for i in range(len(obs) - 1):
        a, b = obs[i], obs[i + 1]
        rng = expected_range(graph, a["camera"], b["camera"])
        if rng is None:
            continue  # not a known edge — route_anomaly.py handles this case
        expected_min, expected_max = rng
        observed = (datetime.fromisoformat(b["time"]) - datetime.fromisoformat(a["time"])).total_seconds()
        if observed > expected_max * threshold:
            deviation_pct = (observed / expected_max - 1) * 100
            anomalies.append({
                "vehicle_id": trajectory_record["vehicle_id"],
                "from_camera": a["camera"],
                "to_camera": b["camera"],
                "observed_seconds": observed,
                "expected_max_seconds": expected_max,
                "deviation_pct": round(deviation_pct, 1),
                "reason": f"Travel time {observed / expected_max:.1f}x expected max ({a['camera']} to {b['camera']})",
            })
    return anomalies
