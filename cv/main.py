"""Main entry point for vehicle tracking"""

import sys
import os
from pathlib import Path
import json
import time
import cv2
import numpy as np
from tqdm import tqdm
from PIL import Image

# Import our modules
import config
from tracker import VehicleTracker, ColorPredictor, PlateDetector, OCRProcessor

def process_video(video_path, camera_id):
    """
    Main function to process video and generate observations
    
    Args:
        video_path: Path to input video
        camera_id: Camera identifier (e.g., "S01_c001")
    """
    
    print("\n" + "="*60)
    print("VEHICLE TRACKING SYSTEM")
    print("="*60)
    print(f"Video: {video_path}")
    print(f"Camera: {camera_id}")
    print(f"Device: {config.DEVICE}")
    print("="*60 + "\n")
    
    # Validate video
    if not os.path.exists(video_path):
        print(f"Error: Video not found: {video_path}")
        return
    
    # Create tracker
    tracker = VehicleTracker(camera_id)
    
    # Process video
    results = tracker.process(video_path)
    
    # Save results
    print("\nSaving results...")
    
        # Save JSON
    json_path = config.OUTPUT_DIR / "json" / f"{camera_id}_observations.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"? JSON saved: {json_path}")
    print(f"? Observations: {len(results)}")
    
    return results

if __name__ == "__main__":
    from pathlib import Path
    
    dataset_dir = Path(r"D:\test\dataset")
    print(f"Searching for videos in {dataset_dir}...")
    
    video_files = list(dataset_dir.rglob("vdo.avi"))
    
    if not video_files:
        print("No videos found in the dataset directory.")
    else:
        print(f"Found {len(video_files)} videos. Starting processing...")
        for video_path in video_files:
            parts = video_path.parts
            camera_folder = parts[-2]
            try:
                formatted_camera_id = f"C{int(camera_folder[1:]):02d}"
            except Exception:
                formatted_camera_id = camera_folder.upper()
            
            print(f"\nProcessing {video_path} for camera {formatted_camera_id}")
            process_video(str(video_path), formatted_camera_id)
