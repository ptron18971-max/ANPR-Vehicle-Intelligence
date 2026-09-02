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
        json.dump(results['observations'], f, indent=2)
    
    print(f"✓ JSON saved: {json_path}")
    print(f"✓ Video saved: {results['video_path']}")
    print(f"✓ Observations: {len(results['observations'])}")
    print(f"✓ Tracks: {results['track_count']}")
    
    return results

if __name__ == "__main__":
    # Example usage
    video_path = r"D:\SIH\AICity22_Track1_MTMC_Tracking\train\S01\c001\vdo.avi"
    camera_id = "S01_c001"
    
    process_video(video_path, camera_id)