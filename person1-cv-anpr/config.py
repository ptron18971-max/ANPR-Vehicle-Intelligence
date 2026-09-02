"""Configuration settings"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

# Model paths
VEHICLE_MODEL = MODEL_DIR / "vehicle_model.pt"
PLATE_MODEL = MODEL_DIR / "plate_detection.pt"
COLOR_MODEL = MODEL_DIR / "color_model.pth"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "videos").mkdir(exist_ok=True)
(OUTPUT_DIR / "json").mkdir(exist_ok=True)
(OUTPUT_DIR / "crops").mkdir(exist_ok=True)

# Detection settings
VEHICLE_CONF = 0.25
PLATE_CONF = 0.25
IOU_THRESHOLD = 0.5

# Color classes
COLOR_CLASSES = [
    "beige", "black", "blue", "brown", "gold",
    "green", "grey", "orange", "pink", "purple",
    "red", "silver", "white", "yellow"
]

# Vehicle classes to track
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "motorbike"}

# OCR settings
PLATE_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
PLATE_RETRY_INTERVAL = 30  # frames

# Output settings
JSON_EVERY_N_FRAMES = 10
SAVE_CROPS = True

# Device
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {DEVICE}")