from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db

app = FastAPI(title="Vehicle Intelligence Platform - Backend")


class ObservationIn(BaseModel):
    camera_id: str
    timestamp: datetime
    local_track_id: Optional[str] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    detection_confidence: Optional[float] = None
    vehicle_type: Optional[str] = None
    vehicle_color: Optional[str] = None
    vehicle_crop_ref: Optional[str] = None
    bbox: Optional[List[int]] = None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT vehicle_id, plate_text, vehicle_type, vehicle_color, first_seen, last_seen
        FROM vehicles
        ORDER BY last_seen DESC
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


@app.post("/observations")
async def create_observation(observation: ObservationIn, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            INSERT INTO observation (
                camera_id, timestamp, local_track_id, plate_text,
                plate_confidence, detection_confidence, vehicle_type,
                vehicle_color, vehicle_crop_ref, bbox
            ) VALUES (
                :camera_id, :timestamp, :local_track_id, :plate_text,
                :plate_confidence, :detection_confidence, :vehicle_type,
                :vehicle_color, :vehicle_crop_ref, :bbox
            )
            RETURNING observation_id
        """),
        {
            "camera_id": observation.camera_id,
            "timestamp": observation.timestamp,
            "local_track_id": observation.local_track_id,
            "plate_text": observation.plate_text,
            "plate_confidence": observation.plate_confidence,
            "detection_confidence": observation.detection_confidence,
            "vehicle_type": observation.vehicle_type,
            "vehicle_color": observation.vehicle_color,
            "vehicle_crop_ref": observation.vehicle_crop_ref,
            "bbox": observation.bbox,
        }
    )
    db.commit()
    new_id = result.scalar()

    await manager.broadcast({
        "event": "new_observation",
        "observation_id": str(new_id),
        "camera_id": observation.camera_id,
        "timestamp": observation.timestamp.isoformat(),
        "plate_text": observation.plate_text,
        "vehicle_type": observation.vehicle_type,
        "vehicle_color": observation.vehicle_color,
    })

    return {"observation_id": str(new_id), "status": "created"}


@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)