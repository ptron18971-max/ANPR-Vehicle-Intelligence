from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.database import get_db

app = FastAPI(title="Vehicle Intelligence Platform - Backend")


# ---------- Request Models ----------

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


class IdentityIn(BaseModel):
    vehicle_id: str
    observation_id: str
    embedding_ref: Optional[str] = None
    identity_confidence: Optional[float] = None
    appearance_confidence: Optional[float] = None
    supporting_evidence: Optional[dict] = None


class TrajectoryObservationIn(BaseModel):
    camera_id: str
    timestamp: Optional[datetime] = None
    sequence_number: int
    status: str  
    confidence: Optional[float] = None
    source_observation_id: Optional[str] = None


class TrajectoryTransitionIn(BaseModel):
    from_camera_id: str
    to_camera_id: str
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    travel_time_sec: Optional[int] = None
    distance_meters: Optional[float] = None
    confidence: Optional[float] = None
    status: str  


class TrajectoryIn(BaseModel):
    vehicle_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    distance_meters: Optional[float] = None
    duration_sec: Optional[int] = None
    trajectory_confidence: Optional[float] = None
    observations: List[TrajectoryObservationIn]
    transitions: List[TrajectoryTransitionIn]


class EventIn(BaseModel):
    vehicle_id: str
    event_type: str
    severity: str
    confidence: Optional[float] = None
    reason: Optional[str] = None
    camera_range: Optional[List[str]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


# ---------- WebSocket Connection Manager ----------

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


# ---------- Health ----------

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


# ---------- Cameras ----------

@app.get("/cameras")
def get_cameras(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT camera_id,
               ST_Y(location::geometry) AS latitude,
               ST_X(location::geometry) AS longitude,
               road_segment, status, installed_at
        FROM camera
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ---------- Vehicles ----------

@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT vehicle_id, plate_text, vehicle_type, vehicle_color, first_seen, last_seen
        FROM vehicles
        ORDER BY last_seen DESC
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ---------- Observations (Person 1 -> Person 2) ----------

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
        observation.model_dump()
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


# ---------- Identities (Person 2 -> Person 3) ----------

@app.post("/identities")
def create_identity(identity: IdentityIn, db: Session = Depends(get_db)):
    import json
    result = db.execute(
        text("""
            INSERT INTO vehicle_identity_links (
                vehicle_id, observation_id, embedding_ref,
                identity_confidence, appearance_confidence, supporting_evidence
            ) VALUES (
                :vehicle_id, :observation_id, :embedding_ref,
                :identity_confidence, :appearance_confidence, :supporting_evidence
            )
            RETURNING id
        """),
        {
            "vehicle_id": identity.vehicle_id,
            "observation_id": identity.observation_id,
            "embedding_ref": identity.embedding_ref,
            "identity_confidence": identity.identity_confidence,
            "appearance_confidence": identity.appearance_confidence,
            "supporting_evidence": json.dumps(identity.supporting_evidence) if identity.supporting_evidence else None,
        }
    )
    db.commit()
    new_id = result.scalar()
    return {"id": str(new_id), "status": "created"}


# ---------- Trajectories (Person 3 -> Person 4 / Person 5) ----------

@app.post("/trajectories")
def create_trajectory(trajectory: TrajectoryIn, db: Session = Depends(get_db)):
    duration_interval = f"{trajectory.duration_sec} seconds" if trajectory.duration_sec is not None else None

    result = db.execute(
        text("""
            INSERT INTO trajectory (
                vehicle_id, start_time, end_time, distance_meters,
                duration, trajectory_confidence
            ) VALUES (
                :vehicle_id, :start_time, :end_time, :distance_meters,
                :duration, :trajectory_confidence
            )
            RETURNING trajectory_id
        """),
        {
            "vehicle_id": trajectory.vehicle_id,
            "start_time": trajectory.start_time,
            "end_time": trajectory.end_time,
            "distance_meters": trajectory.distance_meters,
            "duration": duration_interval,
            "trajectory_confidence": trajectory.trajectory_confidence,
        }
    )
    trajectory_id = result.scalar()

    for obs in trajectory.observations:
        db.execute(
            text("""
                INSERT INTO trajectory_observation (
                    trajectory_id, camera_id, timestamp, sequence_number,
                    status, confidence, source_observation_id
                ) VALUES (
                    :trajectory_id, :camera_id, :timestamp, :sequence_number,
                    :status, :confidence, :source_observation_id
                )
            """),
            {"trajectory_id": trajectory_id, **obs.model_dump()}
        )

    for trans in trajectory.transitions:
        db.execute(
            text("""
                INSERT INTO trajectory_transition (
                    trajectory_id, from_camera_id, to_camera_id,
                    from_timestamp, to_timestamp, travel_time_sec,
                    distance_meters, confidence, status
                ) VALUES (
                    :trajectory_id, :from_camera_id, :to_camera_id,
                    :from_timestamp, :to_timestamp, :travel_time_sec,
                    :distance_meters, :confidence, :status
                )
            """),
            {"trajectory_id": trajectory_id, **trans.model_dump()}
        )

    db.commit()
    return {"trajectory_id": str(trajectory_id), "status": "created"}


@app.get("/trajectories/{vehicle_id}")
def get_trajectories(vehicle_id: str, db: Session = Depends(get_db)):
    trajectories = db.execute(
        text("""
            SELECT trajectory_id, vehicle_id, start_time, end_time,
                   distance_meters, duration, trajectory_confidence
            FROM trajectory
            WHERE vehicle_id = :vehicle_id
            ORDER BY start_time DESC
        """),
        {"vehicle_id": vehicle_id}
    ).mappings().all()

    output = []
    for traj in trajectories:
        traj_dict = dict(traj)
        traj_dict["trajectory_id"] = str(traj_dict["trajectory_id"])
        traj_dict["duration"] = str(traj_dict["duration"]) if traj_dict["duration"] else None

        observations = db.execute(
            text("""
                SELECT trajectory_observation_id, camera_id, timestamp,
                       sequence_number, status, confidence, source_observation_id
                FROM trajectory_observation
                WHERE trajectory_id = :trajectory_id
                ORDER BY sequence_number
            """),
            {"trajectory_id": traj["trajectory_id"]}
        ).mappings().all()

        transitions = db.execute(
            text("""
                SELECT transition_id, from_camera_id, to_camera_id,
                       from_timestamp, to_timestamp, travel_time_sec,
                       distance_meters, confidence, status
                FROM trajectory_transition
                WHERE trajectory_id = :trajectory_id
                ORDER BY from_timestamp
            """),
            {"trajectory_id": traj["trajectory_id"]}
        ).mappings().all()

        traj_dict["observations"] = [dict(o) for o in observations]
        traj_dict["transitions"] = [dict(t) for t in transitions]
        output.append(traj_dict)

    return output


# ---------- Intelligence Events / Alerts (Person 4 -> Person 5) ----------

@app.post("/events")
def create_event(event: EventIn, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            INSERT INTO intelligence_events (
                vehicle_id, event_type, severity, confidence, reason,
                camera_range, time_range_start, time_range_end
            ) VALUES (
                :vehicle_id, :event_type, :severity, :confidence, :reason,
                :camera_range, :time_range_start, :time_range_end
            )
            RETURNING event_id
        """),
        event.model_dump()
    )
    db.commit()
    new_id = result.scalar()
    return {"event_id": str(new_id), "status": "created"}


@app.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT event_id, vehicle_id, event_type, severity, confidence,
               reason, camera_range, time_range_start, time_range_end, created_at
        FROM intelligence_events
        ORDER BY created_at DESC
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ---------- WebSocket Live Feed ----------

@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)