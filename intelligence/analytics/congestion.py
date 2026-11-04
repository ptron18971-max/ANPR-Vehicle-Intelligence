"""Flag cameras where observed vehicles/hour exceeds a configured
threshold. Built on top of traffic_density's per-hour buckets.
"""
from analytics.traffic_density import vehicles_per_camera_per_hour
from config import CONGESTION_VEHICLES_PER_HOUR


def congested_camera_hours(trajectories, threshold=CONGESTION_VEHICLES_PER_HOUR):
    """Return a list of {"camera", "hour", "count"} dicts for every
    camera-hour bucket at or above threshold.
    """
    density = vehicles_per_camera_per_hour(trajectories)
    congested = []
    for camera, hours in density.items():
        for hour, count in hours.items():
            if count >= threshold:
                congested.append({"camera": camera, "hour": hour, "count": count})
    return sorted(congested, key=lambda r: r["count"], reverse=True)
