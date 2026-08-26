"""Generate fake vehicle trajectories matching docs/contracts/person3_to_person4.json.

Lets Person 4 build prediction/analytics/anomaly logic before Person 3's
real trajectory service exists. Walks the camera graph, choosing edges
weighted by historical_probability, and stamps plausible timestamps.
"""
import json
import os
import random

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "contracts")
GRAPH_PATH = os.path.join(CONTRACTS_DIR, "camera_graph.json")


def load_camera_graph(path=GRAPH_PATH):
    with open(path) as f:
        return json.load(f)


def _edges_from(graph, camera_id):
    return [e for e in graph["edges"] if e["from"] == camera_id]


def generate_trajectory(graph, vehicle_id, start_camera=None, max_hops=4,
                         start_time_seconds=36000, anomaly=False):
    """Walk the camera graph from start_camera, return a trajectory dict
    matching the person3_to_person4 contract.

    anomaly=True occasionally injects an out-of-graph camera jump or an
    inflated travel time, for exercising the anomaly detectors.
    """
    cameras = [c["camera_id"] for c in graph["cameras"]]
    current = start_camera or random.choice(cameras)
    t = start_time_seconds
    trajectory = [{"camera": current, "time": _fmt_time(t), "confidence": round(random.uniform(0.85, 0.99), 2)}]
    total_distance = 0.0

    for _ in range(max_hops):
        edges = _edges_from(graph, current)
        if not edges:
            break
        weights = [e["historical_probability"] for e in edges]
        edge = random.choices(edges, weights=weights, k=1)[0]

        travel_time = random.randint(edge["expected_time_seconds_min"], edge["expected_time_seconds_max"])
        if anomaly and random.random() < 0.3:
            travel_time = int(travel_time * random.uniform(2.5, 4.0))

        t += travel_time
        current = edge["to"]
        total_distance += edge["distance_km"]
        trajectory.append({
            "camera": current,
            "time": _fmt_time(t),
            "confidence": round(random.uniform(0.80, 0.99), 2),
        })

    return {
        "vehicle_id": vehicle_id,
        "trajectory": trajectory,
        "total_distance_km": round(total_distance, 2),
        "duration_seconds": t - start_time_seconds,
    }


def _fmt_time(seconds_since_midnight):
    h = (seconds_since_midnight // 3600) % 24
    m = (seconds_since_midnight % 3600) // 60
    s = seconds_since_midnight % 60
    return f"2026-08-26T{h:02d}:{m:02d}:{s:02d}"


def generate_batch(n=20, anomaly_rate=0.15):
    graph = load_camera_graph()
    out = []
    for i in range(n):
        vehicle_id = f"VEH_{1000 + i}"
        is_anomaly = random.random() < anomaly_rate
        start = random.randint(6 * 3600, 20 * 3600)
        out.append(generate_trajectory(graph, vehicle_id, start_time_seconds=start, anomaly=is_anomaly))
    return out


if __name__ == "__main__":
    for record in generate_batch(5):
        print(json.dumps(record, indent=2))
