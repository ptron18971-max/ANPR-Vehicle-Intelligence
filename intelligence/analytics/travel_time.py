"""Empirical travel time stats per camera-pair, compared against the
camera graph's expected range.
"""
from collections import defaultdict
from datetime import datetime


def extract_edge_times(trajectories):
    """Return {(from_camera, to_camera): [observed_seconds, ...]} across
    all trajectories.
    """
    edge_times = defaultdict(list)
    for record in trajectories:
        obs = record["trajectory"]
        for i in range(len(obs) - 1):
            a, b = obs[i], obs[i + 1]
            t_a = datetime.fromisoformat(a["time"])
            t_b = datetime.fromisoformat(b["time"])
            edge_times[(a["camera"], b["camera"])].append((t_b - t_a).total_seconds())
    return edge_times


def edge_stats(trajectories):
    """Return {(from, to): {"avg": ..., "min": ..., "max": ..., "n": ...}}."""
    edge_times = extract_edge_times(trajectories)
    stats = {}
    for pair, times in edge_times.items():
        stats[pair] = {
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "n": len(times),
        }
    return stats


def expected_range(graph, from_camera, to_camera):
    """Look up the camera graph's expected (min, max) seconds for an edge,
    or None if the edge isn't in the graph.
    """
    for e in graph["edges"]:
        if e["from"] == from_camera and e["to"] == to_camera:
            return e["expected_time_seconds_min"], e["expected_time_seconds_max"]
    return None


def _edge_distance(graph, from_camera, to_camera):
    for e in graph["edges"]:
        if e["from"] == from_camera and e["to"] == to_camera:
            return e["distance_km"]
    return None


def average_speed_kmh(graph, trajectories):
    """Return {(from, to): avg_speed_kmh} for every observed edge that
    also exists in the camera graph (distance is only known there).
    """
    stats = edge_stats(trajectories)
    speeds = {}
    for pair, stat in stats.items():
        distance_km = _edge_distance(graph, *pair)
        if distance_km is None or stat["avg"] <= 0:
            continue
        speeds[pair] = round(distance_km / (stat["avg"] / 3600), 1)
    return speeds
