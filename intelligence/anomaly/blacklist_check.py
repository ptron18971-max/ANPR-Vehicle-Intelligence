"""Flag a trajectory if its vehicle_id is on a watchlist. Independent of
route/timing anomalies — this is a direct lookup, not a statistical
signal. Watchlist source (stolen-vehicle list, flagged plates, etc.) is
Person 5's to wire up; this module just does the check.
"""


def check_trajectory(trajectory_record, watchlist):
    """watchlist: set/list of vehicle_id strings. Returns a list with at
    most one anomaly dict (empty if not on the watchlist).
    """
    vehicle_id = trajectory_record["vehicle_id"]
    if vehicle_id not in watchlist:
        return []
    last_seen = trajectory_record["trajectory"][-1]
    return [{
        "vehicle_id": vehicle_id,
        "camera": last_seen["camera"],
        "time": last_seen["time"],
        "reason": f"Vehicle {vehicle_id} matched watchlist, last seen at {last_seen['camera']}",
    }]
