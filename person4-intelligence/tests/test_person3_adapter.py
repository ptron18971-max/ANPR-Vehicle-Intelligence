"""Adapter that translates Person 3's real contract files (camera_graph.json,
person3_to_person4.json) into the shapes pipeline.py already consumes.
"""
import json

from adapters.person3_contract import load_camera_graph, load_trajectories


def test_load_camera_graph_maps_fields_and_units(tmp_path):
    path = tmp_path / "camera_graph.json"
    path.write_text(json.dumps({
        "edges": [
            {"from_camera": "C01", "to_camera": "C02", "distance_meters": 997,
             "min_travel_time_sec": 84, "avg_travel_time_sec": 194, "max_travel_time_sec": 380,
             "historical_probability": None},
            {"from_camera": "C02", "to_camera": "C03", "distance_meters": 1246,
             "min_travel_time_sec": 65, "avg_travel_time_sec": 157, "max_travel_time_sec": 375,
             "historical_probability": 0.4},
        ]
    }))

    graph = load_camera_graph(path)

    assert graph["edges"] == [
        {"from": "C01", "to": "C02", "distance_km": 0.997,
         "expected_time_seconds_min": 84, "expected_time_seconds_max": 380,
         "historical_probability": None},
        {"from": "C02", "to": "C03", "distance_km": 1.246,
         "expected_time_seconds_min": 65, "expected_time_seconds_max": 375,
         "historical_probability": 0.4},
    ]


def test_load_trajectories_maps_valid_record(tmp_path):
    path = tmp_path / "person3_to_person4.json"
    path.write_text(json.dumps([
        {
            "vehicle_id": "V001",
            "trajectory_status": "VALID",
            "camera_sequence": ["C29", "C30"],
            "observations": [
                {"camera_id": "C29", "timestamp": "2026-08-27T09:54:00", "status": "CONFIRMED", "confidence": 0.98},
                {"camera_id": "C30", "timestamp": "2026-08-27T09:56:35", "status": "CONFIRMED", "confidence": 0.93},
            ],
            "distance_meters": 997.0,
            "duration_sec": 155.0,
        }
    ]))

    trajectories = load_trajectories(path)

    assert trajectories == [{
        "vehicle_id": "V001",
        "trajectory": [
            {"camera": "C29", "time": "2026-08-27T09:54:00", "confidence": 0.98},
            {"camera": "C30", "time": "2026-08-27T09:56:35", "confidence": 0.93},
        ],
        "total_distance_km": 0.997,
        "duration_seconds": 155.0,
    }]


def test_load_trajectories_drops_unreachable_and_invalid_time(tmp_path):
    path = tmp_path / "person3_to_person4.json"
    path.write_text(json.dumps([
        {"vehicle_id": "V002", "trajectory_status": "UNREACHABLE",
         "observations": [{"camera_id": "C01", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.9}],
         "distance_meters": None, "duration_sec": 10},
        {"vehicle_id": "V003", "trajectory_status": "INVALID_TIME",
         "observations": [{"camera_id": "C01", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.9}],
         "distance_meters": None, "duration_sec": 5},
    ]))

    assert load_trajectories(path) == []


def test_load_trajectories_keeps_recovered_with_inferred_observations(tmp_path):
    path = tmp_path / "person3_to_person4.json"
    path.write_text(json.dumps([
        {
            "vehicle_id": "V004",
            "trajectory_status": "RECOVERED",
            "observations": [
                {"camera_id": "C10", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.9},
                {"camera_id": "C11", "timestamp": "2026-08-27T09:02:00", "status": "INFERRED", "confidence": 0.7},
                {"camera_id": "C12", "timestamp": "2026-08-27T09:05:00", "status": "CONFIRMED", "confidence": 0.85},
            ],
            "distance_meters": 2000,
            "duration_sec": 300,
        }
    ]))

    trajectories = load_trajectories(path)

    assert len(trajectories) == 1
    assert [obs["camera"] for obs in trajectories[0]["trajectory"]] == ["C10", "C11", "C12"]


def test_load_trajectories_passes_through_missing_distance(tmp_path):
    path = tmp_path / "person3_to_person4.json"
    path.write_text(json.dumps([
        {
            "vehicle_id": "V005",
            "trajectory_status": "VALID",
            "observations": [
                {"camera_id": "C01", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.9},
            ],
            "distance_meters": None,
            "duration_sec": 0,
        }
    ]))

    trajectories = load_trajectories(path)

    assert trajectories[0]["total_distance_km"] is None
