from anomaly.blacklist_check import check_trajectory as check_blacklist
from anomaly.route_anomaly import check_trajectory as check_route_anomaly
from anomaly.travel_time_anomaly import check_trajectory as check_travel_time_anomaly


def test_travel_time_anomaly_flags_slow_transition(graph, slow_trajectory):
    result = check_travel_time_anomaly(graph, slow_trajectory)
    assert len(result) == 1
    assert result[0]["vehicle_id"] == "VEH_TEST_2"


def test_travel_time_anomaly_silent_on_normal(graph, normal_trajectory):
    assert check_travel_time_anomaly(graph, normal_trajectory) == []


def test_route_anomaly_flags_unknown_jump(graph, unknown_jump_trajectory):
    result = check_route_anomaly(graph, unknown_jump_trajectory)
    assert len(result) == 1
    assert "No known route" in result[0]["reason"]


def test_route_anomaly_flags_rare_edge(graph):
    trajectory = {
        "vehicle_id": "VEH_TEST_4",
        "trajectory": [
            {"camera": "B", "time": "2026-08-26T10:00:00", "confidence": 0.9},
            {"camera": "C", "time": "2026-08-26T10:01:00", "confidence": 0.9},
        ],
    }
    result = check_route_anomaly(graph, trajectory)  # B->C has historical_probability 0.1
    assert len(result) == 1
    assert "Rare route" in result[0]["reason"]


def test_route_anomaly_silent_on_common_edge(graph, normal_trajectory):
    assert check_route_anomaly(graph, normal_trajectory) == []


def test_blacklist_check_matches(normal_trajectory):
    result = check_blacklist(normal_trajectory, {"VEH_TEST_1"})
    assert len(result) == 1
    assert result[0]["vehicle_id"] == "VEH_TEST_1"


def test_blacklist_check_no_match(normal_trajectory):
    assert check_blacklist(normal_trajectory, {"OTHER"}) == []
