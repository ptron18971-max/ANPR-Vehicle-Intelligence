"""Translate Person 3's real contract files into the shapes pipeline.py
already consumes (originally built against mock_data/trajectory_generator.py).

Person 3's real output uses different field names and units than the
mock contract, and marks some trajectories as unreconstructable — this
module is the single place that difference is resolved.
"""
import json

DROPPED_STATUSES = {"UNREACHABLE", "INVALID_TIME"}


def load_camera_graph(path):
    with open(path) as f:
        data = json.load(f)

    return {
        "edges": [
            {
                "from": e["from_camera"],
                "to": e["to_camera"],
                "distance_km": e["distance_meters"] / 1000,
                "expected_time_seconds_min": e["min_travel_time_sec"],
                "expected_time_seconds_max": e["max_travel_time_sec"],
                "historical_probability": e["historical_probability"],
            }
            for e in data["edges"]
        ]
    }


def load_trajectories(path):
    with open(path) as f:
        records = json.load(f)

    trajectories = []
    for record in records:
        if record["trajectory_status"] in DROPPED_STATUSES:
            continue

        distance_meters = record["distance_meters"]
        trajectories.append({
            "vehicle_id": record["vehicle_id"],
            "trajectory": [
                {"camera": obs["camera_id"], "time": obs["timestamp"], "confidence": obs["confidence"]}
                for obs in record["observations"]
            ],
            "total_distance_km": distance_meters / 1000 if distance_meters is not None else None,
            "duration_seconds": record["duration_sec"],
        })
    return trajectories
