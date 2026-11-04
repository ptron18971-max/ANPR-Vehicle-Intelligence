"""Origin-destination matrix and most common full routes, from a batch
of trajectory records.
"""
from collections import Counter


def origin_destination_counts(trajectories):
    """Return {(origin_camera, destination_camera): count}."""
    counts = Counter()
    for record in trajectories:
        obs = record["trajectory"]
        if len(obs) < 2:
            continue
        origin = obs[0]["camera"]
        destination = obs[-1]["camera"]
        counts[(origin, destination)] += 1
    return dict(counts)


def most_common_routes(trajectories, top_k=5):
    """Return top_k (route_tuple, count) sorted descending, where
    route_tuple is the full ordered sequence of cameras visited.
    """
    counts = Counter()
    for record in trajectories:
        route = tuple(obs["camera"] for obs in record["trajectory"])
        counts[route] += 1
    return counts.most_common(top_k)
