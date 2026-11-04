"""Smoke test: run mock trajectories through prediction, analytics, and
anomaly detection, and check the alert output matches the contract
shape. Run from intelligence/ with: python -m tests.test_smoke
"""
from alerts.alert_builder import build_alerts
from analytics.od_matrix import most_common_routes, origin_destination_counts
from analytics.traffic_density import busiest_cameras
from analytics.travel_time import edge_stats
from anomaly.route_anomaly import check_trajectory as check_route_anomaly
from anomaly.travel_time_anomaly import check_trajectory as check_travel_time_anomaly
from mock_data.trajectory_generator import generate_batch, load_camera_graph
from prediction.route_predictor import predict_from_trajectory


def run():
    graph = load_camera_graph()
    trajectories = generate_batch(n=30, anomaly_rate=0.3)
    assert len(trajectories) == 30

    for record in trajectories:
        assert "vehicle_id" in record
        assert len(record["trajectory"]) >= 1

    predictions = predict_from_trajectory(graph, trajectories[0])
    print(f"Prediction for {trajectories[0]['vehicle_id']}: {predictions}")

    print("Busiest cameras:", busiest_cameras(trajectories))
    print("OD counts:", origin_destination_counts(trajectories))
    print("Most common routes:", most_common_routes(trajectories, top_k=3))
    print("Edge travel time stats:", edge_stats(trajectories))

    total_alerts = 0
    for record in trajectories:
        tt_anomalies = check_travel_time_anomaly(graph, record)
        route_anomalies = check_route_anomaly(graph, record)
        alerts = build_alerts(tt_anomalies, route_anomalies)
        for alert in alerts:
            assert {"vehicle_id", "event_type", "severity", "confidence", "reason"} <= alert.keys()
        total_alerts += len(alerts)

    print(f"Total alerts generated: {total_alerts}")
    print("Smoke test passed.")


if __name__ == "__main__":
    run()
