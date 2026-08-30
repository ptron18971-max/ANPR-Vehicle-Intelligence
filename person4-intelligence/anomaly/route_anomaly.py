"""Flag trajectory transitions that skip the known camera graph entirely,
or use an edge with very low historical probability.
"""
from config import RARE_EDGE_PROBABILITY_THRESHOLD


def _find_edge(graph, from_camera, to_camera):
    for e in graph["edges"]:
        if e["from"] == from_camera and e["to"] == to_camera:
            return e
    return None


def check_trajectory(graph, trajectory_record, rare_threshold=RARE_EDGE_PROBABILITY_THRESHOLD):
    """Return a list of anomaly dicts for transitions that either aren't
    in the camera graph at all, or are graph edges with low historical
    probability.
    """
    anomalies = []
    obs = trajectory_record["trajectory"]
    for i in range(len(obs) - 1):
        a, b = obs[i], obs[i + 1]
        edge = _find_edge(graph, a["camera"], b["camera"])
        if edge is None:
            anomalies.append({
                "vehicle_id": trajectory_record["vehicle_id"],
                "from_camera": a["camera"],
                "to_camera": b["camera"],
                "reason": f"No known route from {a['camera']} to {b['camera']} — unexpected camera jump",
            })
        elif edge["historical_probability"] is not None and edge["historical_probability"] < rare_threshold:
            anomalies.append({
                "vehicle_id": trajectory_record["vehicle_id"],
                "from_camera": a["camera"],
                "to_camera": b["camera"],
                "reason": f"Rare route {a['camera']} to {b['camera']} (historical probability {edge['historical_probability']})",
            })
    return anomalies
