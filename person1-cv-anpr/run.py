"""Simple runner script"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import process_video

if __name__ == "__main__":
    # Example - modify these paths as needed
    video_path = r"D:\SIH\AICity22_Track1_MTMC_Tracking\train\S01\c001\vdo.avi"
    camera_id = "S01_c001"
    
    # Process video
    process_video(video_path, camera_id)