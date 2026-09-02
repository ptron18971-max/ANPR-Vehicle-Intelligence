"""Vehicle tracking implementation"""

import os
import cv2
import time
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm
from collections import defaultdict

# EasyOCR compatibility with newer Pillow versions
if not hasattr(Image, "ANTIALIAS"):
    resampling = getattr(Image, "Resampling", None)
    if resampling is not None and hasattr(resampling, "LANCZOS"):
        Image.ANTIALIAS = resampling.LANCZOS
    else:
        Image.ANTIALIAS = Image.LANCZOS

from ultralytics import YOLO
import timm
import torch.nn.functional as F
from torchvision import transforms

import config

# ============================================================
# COLOR PREDICTOR
# ============================================================

class ColorPredictor:
    """Vehicle color classification"""
    
    def __init__(self):
        self.device = config.DEVICE
        self.classes = config.COLOR_CLASSES
        self.num_classes = len(self.classes)
        
        # Load model
        checkpoint = torch.load(config.COLOR_MODEL, map_location=self.device)
        
        self.model = timm.create_model(
            "efficientnet_b4",
            pretrained=False,
            num_classes=self.num_classes,
            drop_rate=0.2
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Image transform
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
        
        print(f"✓ Color model loaded ({self.num_classes} classes)")
    
    @torch.no_grad()
    def predict(self, vehicle_crop):
        """Predict vehicle color"""
        if vehicle_crop is None or vehicle_crop.size == 0:
            return "unknown", 0.0
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        
        # Transform
        tensor = self.transform(pil_img)
        tensor = tensor.unsqueeze(0).to(self.device)
        
        # Predict
        logits = self.model(tensor)
        probs = F.softmax(logits, dim=1)
        confidence, index = torch.max(probs, dim=1)
        
        return self.classes[index.item()], float(confidence.item())

# ============================================================
# PLATE DETECTOR
# ============================================================

class PlateDetector:
    """License plate detection"""
    
    def __init__(self):
        self.device = config.DEVICE
        self.model = YOLO(config.PLATE_MODEL)
        self.conf = config.PLATE_CONF
        
        print("✓ Plate detector loaded")
    
    def detect(self, vehicle_crop):
        """Detect plate in vehicle crop"""
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None
        
        results = self.model(vehicle_crop, device=self.device, verbose=False)
        
        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                # Get highest confidence plate
                best = max(boxes, key=lambda b: float(b.conf[0]))
                
                x1, y1, x2, y2 = best.xyxy[0].cpu().numpy().astype(int)
                conf = float(best.conf[0])
                
                # Clamp coordinates
                h, w = vehicle_crop.shape[:2]
                x1 = max(0, min(x1, w-1))
                y1 = max(0, min(y1, h-1))
                x2 = max(0, min(x2, w))
                y2 = max(0, min(y2, h))
                
                if x2 > x1 and y2 > y1:
                    plate_crop = vehicle_crop[y1:y2, x1:x2]
                    return {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf,
                        'crop': plate_crop
                    }
        
        return None

# ============================================================
# OCR PROCESSOR
# ============================================================

class OCRProcessor:
    """License plate text reading"""
    
    def __init__(self):
        import easyocr
        self.device = config.DEVICE
        self.reader = easyocr.Reader(
            ["en"],
            gpu=(self.device == "cuda"),
            verbose=False
        )
        self.allowlist = config.PLATE_ALLOWLIST
        print("✓ OCR loaded")
    
    def read(self, plate_crop):
        """Read text from plate"""
        if plate_crop is None or plate_crop.size == 0:
            return "", 0.0
        
        # Preprocess
        plate = cv2.resize(plate_crop, None, fx=3, fy=3, 
                          interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 50, 50)
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        
        # OCR
        results = self.reader.readtext(
            rgb,
            detail=1,
            paragraph=False,
            allowlist=self.allowlist,
            text_threshold=0.4,
            low_text=0.2,
            link_threshold=0.2
        )
        
        texts = []
        scores = []
        
        for detection in results:
            bbox, text, confidence = detection
            text = text.upper()
            text = "".join(c for c in text if c in self.allowlist)
            if text:
                texts.append(text)
                scores.append(float(confidence))
        
        if not texts:
            return "", 0.0
        
        return "".join(texts), float(np.mean(scores))

# ============================================================
# MAIN TRACKER
# ============================================================

class VehicleTracker:
    """Main vehicle tracking class"""
    
    def __init__(self, camera_id):
        self.camera_id = camera_id
        
        # Load models
        print("\nLoading models...")
        self.vehicle_model = YOLO(config.VEHICLE_MODEL)
        self.plate_detector = PlateDetector()
        self.color_predictor = ColorPredictor()
        self.ocr_processor = OCRProcessor()
        
        # Track metadata
        self.track_metadata = {}
        self.observation_id = 1
        self.frame_number = 0
        
        # Vehicle classes
        self.vehicle_classes = config.VEHICLE_CLASSES
        
        print("\nAll models loaded successfully!\n")
    
    def is_vehicle(self, class_name):
        """Check if class is a vehicle"""
        return class_name.lower() in self.vehicle_classes
    
    def process(self, video_path):
        """Process video and generate observations"""
        
        start_time = time.time()
        observations = []
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"Video info:")
        print(f"  Frames: {total_frames}")
        print(f"  Size: {width}x{height}")
        print(f"  FPS: {fps:.2f}")
        print()
        
        # Setup output video
        video_name = Path(video_path).stem
        output_video = config.OUTPUT_DIR / "videos" / f"{video_name}_tracked.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
        
        # Progress bar
        progress = tqdm(total=total_frames, desc="Processing")
        
        # Process frames
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            self.frame_number += 1
            timestamp = self.frame_number / fps
            
            # Detect and track vehicles
            results = self.vehicle_model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                conf=config.VEHICLE_CONF,
                iou=config.IOU_THRESHOLD,
                verbose=False,
                device=config.DEVICE
            )
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy().astype(int)
                    confs = result.boxes.conf.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy().astype(int)
                    
                    # Check if tracking is available
                    if result.boxes.is_track:
                        track_ids = result.boxes.id.cpu().numpy().astype(int)
                    else:
                        track_ids = np.arange(len(boxes))
                    
                    # Process each detection
                    for box, conf, cls_id, track_id in zip(boxes, confs, classes, track_ids):
                        class_name = result.names[int(cls_id)]
                        
                        if not self.is_vehicle(class_name):
                            continue
                        
                        track_id = int(track_id)
                        x1, y1, x2, y2 = box
                        
                        # Clamp
                        x1 = max(0, min(x1, width-1))
                        y1 = max(0, min(y1, height-1))
                        x2 = max(0, min(x2, width))
                        y2 = max(0, min(y2, height))
                        
                        if x2 <= x1 or y2 <= y1:
                            continue
                        
                        # Get vehicle crop
                        vehicle_crop = frame[y1:y2, x1:x2]
                        if vehicle_crop.size == 0:
                            continue
                        
                        # Get or create metadata
                        if track_id not in self.track_metadata:
                            # New track - get color
                            color, color_conf = self.color_predictor.predict(vehicle_crop)
                            
                            # Save crop
                            crop_path = None
                            if config.SAVE_CROPS:
                                crop_name = f"{self.camera_id}_track_{track_id}.jpg"
                                crop_path = config.OUTPUT_DIR / "crops" / crop_name
                                cv2.imwrite(str(crop_path), vehicle_crop)
                            
                            self.track_metadata[track_id] = {
                                'plate_text': '',
                                'plate_confidence': 0.0,
                                'vehicle_color': color,
                                'color_confidence': color_conf,
                                'vehicle_type': class_name,
                                'last_plate_attempt': self.frame_number,
                                'first_seen_frame': self.frame_number,
                                'vehicle_crop_ref': str(crop_path) if crop_path else ''
                            }
                        
                        metadata = self.track_metadata[track_id]
                        
                        # Try plate detection
                        if not metadata['plate_text']:
                            should_try = (
                                self.frame_number == metadata['first_seen_frame'] or
                                self.frame_number - metadata['last_plate_attempt'] >= config.PLATE_RETRY_INTERVAL
                            )
                            
                            if should_try:
                                metadata['last_plate_attempt'] = self.frame_number
                                plate_result = self.plate_detector.detect(vehicle_crop)
                                
                                if plate_result:
                                    plate_text, ocr_conf = self.ocr_processor.read(plate_result['crop'])
                                    if plate_text:
                                        metadata['plate_text'] = plate_text
                                        metadata['plate_confidence'] = ocr_conf
                        
                        # Create observation
                        if self.frame_number % config.JSON_EVERY_N_FRAMES == 0:
                            observation = {
                                'observation_id': self.observation_id,
                                'camera_id': self.camera_id,
                                'timestamp': round(timestamp, 3),
                                'local_track_id': str(track_id),
                                'plate_text': metadata.get('plate_text', ''),
                                'plate_confidence': float(metadata.get('plate_confidence', 0.0)),
                                'detection_confidence': round(float(conf), 4),
                                'vehicle_type': class_name,
                                'vehicle_color': metadata.get('vehicle_color', 'unknown'),
                                'vehicle_crop_ref': metadata.get('vehicle_crop_ref', ''),
                                'bbox': [int(x1), int(y1), int(x2), int(y2)]
                            }
                            observations.append(observation)
                            self.observation_id += 1
                        
                        # Draw on frame
                        label = f"{class_name} | ID {track_id}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.putText(frame, label, (x1, max(25, y1-8)),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 0, 0), 2)
            
            # Write frame
            writer.write(frame)
            progress.update(1)
        
        # Cleanup
        cap.release()
        writer.release()
        progress.close()
        
        elapsed = time.time() - start_time
        
        # Create observations JSON structure
        observations_json = {
            'camera_id': self.camera_id,
            'video': {
                'source': video_path,
                'fps': fps,
                'width': width,
                'height': height,
                'total_frames': total_frames
            },
            'observations': observations
        }
        
        return {
            'video_path': str(output_video),
            'observations': observations_json,
            'track_count': len(self.track_metadata),
            'elapsed_time': elapsed
        }