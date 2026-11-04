"""Data-driven next-camera prediction: learn transition frequencies from
a batch of historical trajectories instead of relying on the static
camera_graph.json probabilities. Complements route_predictor (graph-
based) — this one improves as more real Person 3 trajectories arrive.
"""
from collections import Counter, defaultdict


def build_transition_model(trajectories):
    """Return {camera_id: Counter({next_camera_id: count})} from
    observed consecutive camera pairs across all trajectories.
    """
    model = defaultdict(Counter)
    for record in trajectories:
        obs = record["trajectory"]
        for i in range(len(obs) - 1):
            model[obs[i]["camera"]][obs[i + 1]["camera"]] += 1
    return model


def predict_next(model, current_camera, top_k=3):
    """Return up to top_k (camera_id, probability) tuples, ranked by
    observed transition frequency from current_camera. Empty if
    current_camera was never observed transitioning onward.
    """
    counts = model.get(current_camera)
    if not counts:
        return []
    total = sum(counts.values())
    ranked = counts.most_common(top_k)
    return [(camera, round(count / total, 2)) for camera, count in ranked]
