"""Person 4's intelligence pipeline: run a batch of trajectories through
prediction, analytics, and anomaly detection, and produce one
consolidated result. This is the shape Person 5's backend will call
once it wires up the real service — for now it runs standalone against
mock data.
"""
import json
import os

from adapters.person3_contract import load_camera_graph as load_real_camera_graph
from adapters.person3_contract import load_trajectories as load_real_trajectories
from alerts.alert_builder import build_alerts
from analytics.congestion import congested_camera_hours
from analytics.od_matrix import most_common_routes, origin_destination_counts
from analytics.traffic_density import busiest_cameras
from analytics.travel_time import average_speed_kmh, edge_stats
from anomaly.blacklist_check import check_trajectory as check_blacklist
from anomaly.route_anomaly import check_trajectory as check_route_anomaly
from anomaly.travel_time_anomaly import check_trajectory as check_travel_time_anomaly
from mock_data.trajectory_generator import generate_batch, load_camera_graph
from prediction.markov_predictor import build_transition_model
from prediction.markov_predictor import predict_next as markov_predict_next
from prediction.route_predictor import predict_from_trajectory


def run_intelligence_pipeline(graph, trajectories, watchlist=()):
    """Run the full pipeline over a batch of trajectory records
    (person3_to_person4 contract shape). Returns a dict with alerts and
    analytics, ready to hand to Person 5's ingestion layer.
    """
    transition_model = build_transition_model(trajectories)

    alerts = []
    predictions = {}
    for record in trajectories:
        vehicle_id = record["vehicle_id"]
        tt_anomalies = check_travel_time_anomaly(graph, record)
        route_anomalies = check_route_anomaly(graph, record)
        blacklist_anomalies = check_blacklist(record, watchlist)
        alerts.extend(build_alerts(tt_anomalies, route_anomalies, blacklist_anomalies))

        last_camera = record["trajectory"][-1]["camera"]
        predictions[vehicle_id] = {
            "graph_based": predict_from_trajectory(graph, record),
            "history_based": markov_predict_next(transition_model, last_camera),
        }

    analytics = {
        "busiest_cameras": busiest_cameras(trajectories),
        "congested_camera_hours": congested_camera_hours(trajectories),
        "origin_destination_counts": {f"{o}->{d}": c for (o, d), c in origin_destination_counts(trajectories).items()},
        "most_common_routes": [{"route": list(route), "count": c} for route, c in most_common_routes(trajectories)],
        "edge_travel_time_stats": {f"{a}->{b}": stat for (a, b), stat in edge_stats(trajectories).items()},
        "average_speed_kmh": {f"{a}->{b}": speed for (a, b), speed in average_speed_kmh(graph, trajectories).items()},
    }

    return {
        "alerts": alerts,
        "predictions": predictions,
        "analytics": analytics,
    }


DEFAULT_CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "contracts")


def run_against_real_data(contracts_dir=DEFAULT_CONTRACTS_DIR, watchlist=()):
    """Run the pipeline against Person 3's real contract files instead of
    mock_data. Trajectories Person 3 marked UNREACHABLE/INVALID_TIME are
    dropped by the adapter before they reach prediction/analytics.
    """
    graph = load_real_camera_graph(os.path.join(contracts_dir, "camera_graph.json"))
    trajectories = load_real_trajectories(os.path.join(contracts_dir, "person3_to_person4.json"))
    return run_intelligence_pipeline(graph, trajectories, watchlist=watchlist)


if __name__ == "__main__":
    import sys

    if "--source" in sys.argv and sys.argv[sys.argv.index("--source") + 1] == "real":
        result = run_against_real_data(watchlist={"VEH_1005"})
    else:
        camera_graph = load_camera_graph()
        batch = generate_batch(n=30, anomaly_rate=0.3)
        result = run_intelligence_pipeline(camera_graph, batch, watchlist={"VEH_1005"})

    print(json.dumps(result, indent=2, default=str))
