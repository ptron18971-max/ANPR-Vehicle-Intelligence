from alerts.alert_builder import build_alerts
from pipeline import run_intelligence_pipeline


def test_pipeline_produces_expected_shape(graph, normal_trajectory, slow_trajectory):
    result = run_intelligence_pipeline(graph, [normal_trajectory, slow_trajectory])
    assert set(result.keys()) == {"alerts", "predictions", "analytics"}
    assert "VEH_TEST_1" in result["predictions"]
    assert "VEH_TEST_2" in result["predictions"]


def test_pipeline_flags_slow_vehicle_alert(graph, normal_trajectory, slow_trajectory):
    result = run_intelligence_pipeline(graph, [normal_trajectory, slow_trajectory])
    alert_vehicle_ids = {a["vehicle_id"] for a in result["alerts"]}
    assert "VEH_TEST_2" in alert_vehicle_ids
    assert "VEH_TEST_1" not in alert_vehicle_ids


def test_pipeline_applies_watchlist(graph, normal_trajectory):
    result = run_intelligence_pipeline(graph, [normal_trajectory], watchlist={"VEH_TEST_1"})
    alert_types = {a["alert_type"] for a in result["alerts"]}
    assert "BLACKLIST_MATCH" in alert_types


def test_alert_contract_shape(graph, slow_trajectory):
    from anomaly.travel_time_anomaly import check_trajectory as check_tt
    anomalies = check_tt(graph, slow_trajectory)
    alerts = build_alerts(anomalies, [], [])
    for alert in alerts:
        assert {"vehicle_id", "alert_type", "severity", "confidence", "reason"} <= alert.keys()
