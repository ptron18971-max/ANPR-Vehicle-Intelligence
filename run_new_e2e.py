import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()


def run_step(name, func_or_cmd, cwd=None):
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    if isinstance(func_or_cmd, list):
        result = subprocess.run(func_or_cmd, cwd=cwd or BASE_DIR)
        if result.returncode != 0:
            raise RuntimeError(f"{name} failed with exit code {result.returncode}")
        return
    func_or_cmd()


def run_person2():
    """Normalize raw camera bundles into the Person 3 contract."""
    contract_path = BASE_DIR / "docs" / "contracts" / "person2_to_person3.json"
    input_dir = BASE_DIR / "output" / "json"
    input_files = sorted(input_dir.glob("*_observations.json"))
    if not input_files:
        raise RuntimeError(f"No observation files found in {input_dir}")

    by_vehicle_camera = {}
    raw_timestamps = []
    for input_file in input_files:
        data = json.loads(input_file.read_text())
        camera_id = data["camera_id"].replace("CAM_", "C")
        for frame in data.get("frames", []):
            timestamp = float(frame["timestamp"])
            raw_timestamps.append(timestamp)
            for source in frame.get("vehicles", []):
                raw_id = str(source.get("global_vehicle_id") or source["local_track_id"])
                key = (raw_id, camera_id)
                current = by_vehicle_camera.get(key)
                if current is None or timestamp < current["raw_timestamp"]:
                    by_vehicle_camera[key] = {
                        "raw_id": raw_id,
                        "raw_timestamp": timestamp,
                        "camera_id": camera_id,
                        "plate_text": source.get("plate_text"),
                    }

    raw_ids = sorted({item["raw_id"] for item in by_vehicle_camera.values()})
    if len(raw_ids) != 70:
        raise RuntimeError(f"Expected 70 vehicles in {input_dir}, found {len(raw_ids)}")
    vehicle_ids = {raw_id: f"VEH_{index:04d}" for index, raw_id in enumerate(raw_ids, 1)}

    base_time = datetime(2026, 8, 25, 9, 0, 0)
    start_timestamp = min(raw_timestamps)
    observations = []
    for item in sorted(by_vehicle_camera.values(), key=lambda value: (value["raw_id"], value["raw_timestamp"])):
        timestamp = base_time + timedelta(seconds=item["raw_timestamp"] - start_timestamp)
        observations.append({
            "vehicle_id": vehicle_ids[item["raw_id"]],
            "camera_id": item["camera_id"],
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "plate_text": item["plate_text"],
            "identity_confidence": 1.0,
            "appearance_confidence": 1.0,
            "supporting_evidence": {
                "match_strategy": "source_global_vehicle_id",
                "matched_against_id": item["raw_id"],
            },
        })

    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(observations, indent=2))
    print(f"[OK] Normalized {len(vehicle_ids)} vehicles and {len(observations)} map observations from {len(input_files)} files.")
    print(f"[OK] Output saved to {contract_path}")


def run_person4():
    cwd = BASE_DIR / "intelligence"
    output_file = BASE_DIR / "docs" / "contracts" / "person4_to_person5.json"
    with output_file.open("w") as output:
        result = subprocess.run([sys.executable, "pipeline.py", "--source", "real"], cwd=cwd, stdout=output)
    if result.returncode != 0:
        raise RuntimeError("Person 4 failed")


def run_person5_ingest():
    import requests

    requests.get("http://127.0.0.1:8000/health/db", timeout=2).raise_for_status()
    trajectory_file = BASE_DIR / "docs" / "contracts" / "person3_to_person4.json"
    for trajectory in json.loads(trajectory_file.read_text()):
        requests.post("http://127.0.0.1:8000/trajectories", json=trajectory).raise_for_status()

    intelligence_file = BASE_DIR / "docs" / "contracts" / "person4_to_person5.json"
    requests.post("http://127.0.0.1:8000/intelligence", json=json.loads(intelligence_file.read_text())).raise_for_status()
    print("[OK] Person 5 ingestion complete.")


if __name__ == "__main__":
    print("Starting City-Wide Vehicle Intelligence E2E Pipeline")
    run_step("PERSON 2: NORMALIZE REPLACEMENT DATA", run_person2)
    run_step("PERSON 3: TRAJECTORY ENGINE", [sys.executable, "pipeline.py"], cwd=BASE_DIR / "graph" / "src")
    run_step("PERSON 4: INTELLIGENCE", run_person4)
    run_step("PERSON 5: DATABASE INGESTION", run_person5_ingest)
    print("\n[SUCCESS] E2E Pipeline Completed!")
