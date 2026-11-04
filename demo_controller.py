import os
import subprocess
import glob
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import shutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    path: str
    run_person1: bool = False

# We will mount the user's dataset path dynamically, but FastAPI requires a static mount point.
# A simple hack for the demo is to create a symlink to the dataset, or just read the path and serve files.
from fastapi.responses import FileResponse

DATASET_PATH = r"D:\synthetic_city_12_cameras"

@app.get("/videos/{video_id}")
async def get_video(video_id: str):
    # video_id e.g. CAM_01.mp4
    video_path = os.path.join(DATASET_PATH, video_id)
    if os.path.exists(video_path):
        return FileResponse(video_path)
    return {"error": "Video not found"}

@app.post("/process-dataset")
async def process_dataset(req: ProcessRequest):
    global DATASET_PATH
    DATASET_PATH = req.path
    if not os.path.exists(DATASET_PATH):
        return {"status": "error", "message": "Directory not found"}
        
    print(f"Processing dataset at {DATASET_PATH}")
    
    mp4_files = glob.glob(os.path.join(DATASET_PATH, "*.mp4"))
    
    # Optionally trigger Person 1 tracking script
    if req.run_person1:
        print("Triggering new vehicle tracking script for Person 1...")
        # Just an example of how we'd call it.
        # subprocess.run(["python", r"D:\vehicle_tracking\vehicle_tracking\run.py"], shell=True)
            
    # For demo, seed the db
    print("Executing backend seed pipeline...")
    subprocess.run(["python", "backend/seed_cams.py"], shell=True)
    subprocess.run(["python", "backend/seed_vehicles.py"], shell=True)
    
    return {"status": "success", "videos_processed": len(mp4_files)}

if __name__ == "__main__":
    print("Starting SIH Fullstack Controller on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
