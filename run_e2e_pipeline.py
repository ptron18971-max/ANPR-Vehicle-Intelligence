import os
import sys
import subprocess
import glob
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.absolute()

def run_step(name, func_or_cmd, cwd=None):
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    if isinstance(func_or_cmd, list):
        result = subprocess.run(func_or_cmd, cwd=cwd or BASE_DIR)
        if result.returncode != 0:
            print(f"FAILED: {name}")
            sys.exit(1)
    else:
        try:
            func_or_cmd()
        except Exception as e:
            print(f"FAILED: {name}\n{e}")
            sys.exit(1)

def run_person2():
    contract_path = BASE_DIR / "docs" / "contracts" / "person2_to_person3.json"

    sys.path.append(str(BASE_DIR / "fusion" / "src"))
    from vehicle_reid.embeddings.extractor import VehicleEmbeddingExtractor
    from vehicle_reid.vector_store import FaissVectorStore
    from vehicle_reid.fusion import IdentityFusionEngine
    from vehicle_reid.pipeline import VehicleReIDPipeline

    extractor = VehicleEmbeddingExtractor()
    vector_store = FaissVectorStore(dimension=extractor.embedding_dim)
    fusion_engine = IdentityFusionEngine()
    pipeline = VehicleReIDPipeline(extractor, vector_store, fusion_engine, confidence_threshold=0.65)

    p1_output_dir = BASE_DIR / "output" / "json"
    p1_files = glob.glob(str(p1_output_dir / "*_observations.json"))

    if not p1_files:
        print(f"No Person 1 observation files found in {p1_output_dir}")
        sys.exit(1)

    print(f"Loaded {len(p1_files)} observation files from Person 1.")
    observations = []
    for f in p1_files:
        with open(f, 'r') as fp:
            data = json.load(fp)
            if isinstance(data, list): observations.extend(data)
            else: observations.append(data)

    for obs in observations:
        if "vehicle_crop_ref" in obs and "vehicle_crop" not in obs:
            obs["vehicle_crop"] = obs.pop("vehicle_crop_ref")
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = lambda x, **kwargs: x

    results = []
    print(f"Extracting embeddings and tracking Re-ID for {len(observations)} observations...")
    for obs in tqdm(observations, desc="Person 2 (Re-ID)"):
        results.append(pipeline.process_observation(obs))
    
    contract_path = BASE_DIR / "docs" / "contracts" / "person2_to_person3.json"
    os.makedirs(contract_path.parent, exist_ok=True)
    with open(contract_path, 'w') as f:
        json.dump([
            r.model_dump(mode="json") if hasattr(r, "model_dump")
            else r.dict() if hasattr(r, "dict")
            else r
            for r in results
        ], f, indent=2)
    print(f"[OK] Person 2 Output Saved: {contract_path}")

def run_person4():
    cwd = BASE_DIR / "intelligence"
    out_file = BASE_DIR / "docs" / "contracts" / "person4_to_person5.json"
    with open(out_file, "w") as f:
        result = subprocess.run([sys.executable, "pipeline.py", "--source", "real"], cwd=cwd, stdout=f)
    if result.returncode != 0:
        print("FAILED: PERSON 4")
        sys.exit(1)
    print(f"[OK] Person 4 Output Saved: {out_file}")

def run_person5_ingest():
    import requests
    
    try:
        requests.get("http://127.0.0.1:8000/health/db", timeout=2)
    except:
        print("ERROR: Person 5 backend is not running on http://127.0.0.1:8000")
        print("Please run `docker compose up -d` in backend/")
        sys.exit(1)
        
    print("Person 5 backend is responsive. Ingesting data...")
    
    p3_file = BASE_DIR / "docs" / "contracts" / "person3_to_person4.json"
    if p3_file.exists():
        with open(p3_file) as f: trajectories = json.load(f)
        for t in trajectories:
            res = requests.post("http://127.0.0.1:8000/trajectories", json=t)
            if res.status_code == 200: print(f"Ingested Trajectory for {t.get('vehicle_id')}")
            else: print(f"Failed to ingest trajectory: {res.text}")
    
    p4_file = BASE_DIR / "docs" / "contracts" / "person4_to_person5.json"
    if p4_file.exists():
        with open(p4_file) as f: p4_data = json.load(f)
        # Ingest the unified intelligence payload (alerts, predictions, analytics)
        res = requests.post("http://127.0.0.1:8000/intelligence", json=p4_data)
        if res.status_code == 200:
            print("Successfully ingested Person 4 Intelligence payload.")
        else:
            print(f"Failed to ingest intelligence: {res.text}")
    print("[OK] Person 5 Ingestion Complete.")

if __name__ == "__main__":
    print("Starting City-Wide Vehicle Intelligence E2E Pipeline")
    # run_step("PERSON 1: CV & ANPR", [sys.executable, "main.py"], cwd=BASE_DIR / "cv")
    run_step("PERSON 2: RE-ID FUSION", run_person2)
    run_step("PERSON 3: TRAJECTORY ENGINE", [sys.executable, "pipeline.py"], cwd=BASE_DIR / "graph" / "src")
    run_step("PERSON 4: INTELLIGENCE", run_person4)
    run_step("PERSON 5: DATABASE INGESTION", run_person5_ingest)
    print("\n[SUCCESS] E2E Pipeline Completed!")
