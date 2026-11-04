"""Vehicles/hour and vehicles/minute per camera, from a batch of
trajectory records.
"""
from collections import defaultdict
from datetime import datetime


def _hour_bucket(iso_time):
    return datetime.fromisoformat(iso_time).replace(minute=0, second=0)


def vehicles_per_camera_per_hour(trajectories):
    """Return {camera_id: {hour_iso: count}}."""
    counts = defaultdict(lambda: defaultdict(int))
    for record in trajectories:
        for obs in record["trajectory"]:
            bucket = _hour_bucket(obs["time"]).isoformat()
            counts[obs["camera"]][bucket] += 1
    return {camera: dict(hours) for camera, hours in counts.items()}


def busiest_cameras(trajectories, top_k=5):
    """Return top_k (camera_id, total_observations) sorted descending."""
    totals = defaultdict(int)
    for record in trajectories:
        for obs in record["trajectory"]:
            totals[obs["camera"]] += 1
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
