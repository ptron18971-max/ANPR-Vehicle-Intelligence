"""Predict a vehicle's next likely camera from its trajectory so far and
the camera graph's historical edge probabilities.
"""


def predict_next(graph, current_camera, top_k=3):
    """Return up to top_k (camera_id, probability) tuples for where a
    vehicle at current_camera is likely to go next, ranked by
    historical_probability.
    """
    edges = [e for e in graph["edges"] if e["from"] == current_camera]
    ranked = sorted(edges, key=lambda e: e["historical_probability"], reverse=True)
    return [(e["to"], e["historical_probability"]) for e in ranked[:top_k]]


def predict_from_trajectory(graph, trajectory_record, top_k=3):
    """Convenience wrapper: predict next camera given a full trajectory
    record (person3_to_person4 contract shape).
    """
    last_camera = trajectory_record["trajectory"][-1]["camera"]
    return predict_next(graph, last_camera, top_k=top_k)
