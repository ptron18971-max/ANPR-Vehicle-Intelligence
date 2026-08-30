import json

from pipeline import run_against_real_data


def _write_contracts(contracts_dir):
    (contracts_dir / "camera_graph.json").write_text(json.dumps({
        "edges": [
            {"from_camera": "C01", "to_camera": "C02", "distance_meters": 1000,
             "min_travel_time_sec": 100, "max_travel_time_sec": 200, "avg_travel_time_sec": 150,
             "historical_probability": None},
        ]
    }))
    (contracts_dir / "person3_to_person4.json").write_text(json.dumps([
        {
            "vehicle_id": "V001",
            "trajectory_status": "VALID",
            "observations": [
                {"camera_id": "C01", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.98},
                {"camera_id": "C02", "timestamp": "2026-08-27T09:02:00", "status": "CONFIRMED", "confidence": 0.93},
            ],
            "distance_meters": 1000,
            "duration_sec": 120,
        },
        {
            "vehicle_id": "V002",
            "trajectory_status": "UNREACHABLE",
            "observations": [
                {"camera_id": "C01", "timestamp": "2026-08-27T09:00:00", "status": "CONFIRMED", "confidence": 0.9},
            ],
            "distance_meters": None,
            "duration_sec": 10,
        },
    ]))


def test_run_against_real_data_uses_person3_contracts(tmp_path):
    _write_contracts(tmp_path)

    result = run_against_real_data(contracts_dir=tmp_path)

    assert set(result.keys()) == {"alerts", "predictions", "analytics"}
    assert "V001" in result["predictions"]
    assert "V002" not in result["predictions"]  # dropped: UNREACHABLE
