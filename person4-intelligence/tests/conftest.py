"""Shared fixtures: a small fixed camera graph and fixed trajectories,
so unit tests are deterministic (unlike the random mock_data generator,
which is for exploratory/manual use).
"""
import pytest

GRAPH = {
    "cameras": [
        {"camera_id": "A", "lat": 0.0, "lon": 0.0},
        {"camera_id": "B", "lat": 0.0, "lon": 0.0},
        {"camera_id": "C", "lat": 0.0, "lon": 0.0},
    ],
    "edges": [
        {"from": "A", "to": "B", "distance_km": 2.0, "expected_time_seconds_min": 100, "expected_time_seconds_max": 200, "historical_probability": 0.8},
        {"from": "B", "to": "C", "distance_km": 1.0, "expected_time_seconds_min": 50, "expected_time_seconds_max": 100, "historical_probability": 0.1},
    ],
}


@pytest.fixture
def graph():
    return GRAPH


@pytest.fixture
def normal_trajectory():
    return {
        "vehicle_id": "VEH_TEST_1",
        "trajectory": [
            {"camera": "A", "time": "2026-08-26T10:00:00", "confidence": 0.95},
            {"camera": "B", "time": "2026-08-26T10:02:30", "confidence": 0.95},  # 150s, within 100-200
        ],
        "total_distance_km": 2.0,
        "duration_seconds": 150,
    }


@pytest.fixture
def slow_trajectory():
    return {
        "vehicle_id": "VEH_TEST_2",
        "trajectory": [
            {"camera": "A", "time": "2026-08-26T10:00:00", "confidence": 0.95},
            {"camera": "B", "time": "2026-08-26T10:10:00", "confidence": 0.95},  # 600s, 3x the 200s max
        ],
        "total_distance_km": 2.0,
        "duration_seconds": 600,
    }


@pytest.fixture
def unknown_jump_trajectory():
    return {
        "vehicle_id": "VEH_TEST_3",
        "trajectory": [
            {"camera": "A", "time": "2026-08-26T10:00:00", "confidence": 0.95},
            {"camera": "C", "time": "2026-08-26T10:02:00", "confidence": 0.95},  # A->C not in graph
        ],
        "total_distance_km": 3.0,
        "duration_seconds": 120,
    }
