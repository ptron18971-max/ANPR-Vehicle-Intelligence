from analytics.congestion import congested_camera_hours
from analytics.od_matrix import most_common_routes, origin_destination_counts
from analytics.traffic_density import busiest_cameras, vehicles_per_camera_per_hour
from analytics.travel_time import average_speed_kmh, edge_stats, expected_range


def test_vehicles_per_camera_per_hour(normal_trajectory):
    density = vehicles_per_camera_per_hour([normal_trajectory])
    assert density["A"]["2026-08-26T10:00:00"] == 1
    assert density["B"]["2026-08-26T10:00:00"] == 1


def test_busiest_cameras(normal_trajectory, slow_trajectory):
    result = busiest_cameras([normal_trajectory, slow_trajectory])
    assert dict(result)["A"] == 2


def test_congestion_flags_high_volume(normal_trajectory):
    many = [normal_trajectory] * 11  # same camera/hour bucket, above default threshold of 10
    flagged = congested_camera_hours(many)
    assert any(c["camera"] == "A" and c["count"] == 11 for c in flagged)


def test_congestion_ignores_low_volume(normal_trajectory):
    assert congested_camera_hours([normal_trajectory]) == []


def test_edge_stats(normal_trajectory):
    stats = edge_stats([normal_trajectory])
    assert stats[("A", "B")]["avg"] == 150
    assert stats[("A", "B")]["n"] == 1


def test_expected_range_known_edge(graph):
    assert expected_range(graph, "A", "B") == (100, 200)


def test_expected_range_unknown_edge(graph):
    assert expected_range(graph, "A", "C") is None


def test_average_speed(graph, normal_trajectory):
    speeds = average_speed_kmh(graph, [normal_trajectory])
    # 2.0 km in 150s = 48 km/h
    assert speeds[("A", "B")] == 48.0


def test_origin_destination_counts(normal_trajectory):
    counts = origin_destination_counts([normal_trajectory])
    assert counts[("A", "B")] == 1


def test_most_common_routes(normal_trajectory):
    routes = most_common_routes([normal_trajectory, normal_trajectory])
    assert routes[0] == (("A", "B"), 2)
