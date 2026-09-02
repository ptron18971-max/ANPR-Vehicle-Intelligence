# City-Wide Vehicle Intelligence Platform — Person 2 Subsystem
## Vehicle Re-ID & Multi-Modal Identity Fusion Engine

This repository hosts the implementation of **Person 2 (Vehicle Re-ID + Identity Fusion)** in the City-Wide Vehicle Intelligence Platform team structure.

---

## 🎯 Role Objective
Determines whether observations from disparate cameras belong to the same physical vehicle. 
License plate recognition is treated as **one source of evidence** rather than ground truth. We fuse **deep visual appearance embeddings**, **attribute matching**, and **fuzzy OCR matching** to construct a continuous canonical `vehicle_id` with calibrated confidence scores.

---

## 📦 Data Contracts

### 1. Input (`Person 1 → Person 2`): `VehicleObservation`
```json
{
  "camera_id": "C04",
  "timestamp": "2026-08-27T01:30:00Z",
  "local_track_id": "trk_104",
  "plate_text": "KA01AB1234",
  "plate_confidence": 0.87,
  "vehicle_type": "sedan",
  "vehicle_color": "white",
  "vehicle_crop": "path/to/crop.jpg",
  "bbox": [120, 340, 450, 680]
}
```

### 2. Output (`Person 2 → Person 3`): `CanonicalVehicleIdentity`
```json
{
  "vehicle_id": "VEH_8421",
  "camera_id": "C04",
  "timestamp": "2026-08-27T01:30:00Z",
  "plate_text": "KA01AB1234",
  "identity_confidence": 0.93,
  "appearance_confidence": 0.91,
  "supporting_evidence": {
    "appearance_similarity": 0.91,
    "plate_match_score": 0.95,
    "attribute_match_score": 1.0,
    "matched_against_id": "VEH_8421",
    "match_strategy": "multimodal_fusion"
  }
}
```

---

## 🛠️ Architecture

```
src/vehicle_reid/
├── schemas.py                 # Pydantic data contracts (P1 -> P2, P2 -> P3)
├── embeddings/                # Deep vehicle visual feature extraction
│   ├── base.py                # Abstract BaseExtractor interface & metrics
│   ├── preprocessor.py        # Image transforms, CLAHE & crop quality scoring
│   ├── backbones.py           # ReID networks (GeM pooling, BNNeck, timm backbones)
│   └── extractor.py           # High-level batch & single embedding extractor
├── indexer/                   # FAISS / vector index of active vehicle tracks (Upcoming)
├── ocr_matcher/               # Fuzzy Levenshtein + OCR substitution matrix (Upcoming)
└── fusion/                    # Multi-modal identity fusion & confidence scoring (Upcoming)
```

---

## 🚀 Setup & Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Or install in editable development mode
pip install -e ".[dev]"

# 3. Run test suite
pytest -v
```

Test Change.
