from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from app.database import get_db

app = FastAPI(title="Vehicle Intelligence Platform - Backend")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class SupportingEvidence(BaseModel):
    appearance_similarity: Optional[float] = None
    plate_match_score: Optional[float] = None
    attribute_match_score: Optional[float] = None
    matched_against_id: Optional[str] = None
    match_strategy: Optional[str] = None


class IdentityIn(BaseModel):
    """Matches Person 2's actual CanonicalVehicleIdentity output.
    No observation_id is sent — we look it up via camera_id + timestamp + plate_text."""
    vehicle_id: str
    camera_id: str
    timestamp: datetime
    plate_text: Optional[str] = None
    identity_confidence: Optional[float] = None
    appearance_confidence: Optional[float] = None
    supporting_evidence: Optional[dict] = None


class TrajectoryObservationIn(BaseModel):
    """Matches Person 3's flat observation shape. sequence_number is
    derived server-side from array order, not sent by Person 3."""
    camera_id: str
    timestamp: Optional[datetime] = None
    status: str  # CONFIRMED / INFERRED
    confidence: Optional[float] = None
    source_observation_id: Optional[str] = None


class TrajectoryTransitionIn(BaseModel):
    from_camera_id: str
    to_camera_id: str
    from_timestamp: Optional[datetime] = None
    to_timestamp: Optional[datetime] = None
    travel_time_sec: Optional[float] = None
    distance_meters: Optional[float] = None
    confidence: Optional[float] = None
    status: str  # CONFIRMED / INFERRED


class RoutePoint(BaseModel):
    lat: float
    lon: float


class RouteGeometrySegment(BaseModel):
    from_camera_id: str
    to_camera_id: str
    distance_meters: Optional[float] = None
    points: List[RoutePoint]


class TrajectoryIn(BaseModel):
    """Matches Person 3's real person3_to_person4.json contract."""
    vehicle_id: str
    trajectory_status: Optional[str] = None  # VALID / RECOVERED / INVALID_TIME / UNREACHABLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    distance_meters: Optional[float] = None
    duration_sec: Optional[float] = None
    trajectory_confidence: Optional[float] = None
    observations: List[TrajectoryObservationIn]
    transitions: List[TrajectoryTransitionIn]
    route_geometry: Optional[List[RouteGeometrySegment]] = None


class EventIn(BaseModel):
    vehicle_id: str
    event_type: str
    severity: str
    confidence: Optional[float] = None
    reason: Optional[str] = None
    camera_range: Optional[List[str]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


class IntelligencePayloadIn(BaseModel):
    alerts: List[EventIn] = Field(default_factory=list)
    predictions: Dict[str, Any] = Field(default_factory=dict)
    analytics: Dict[str, Any] = Field(default_factory=dict)


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
    # Person 2 doesn't send our internal observation_id — look it up
    # via the fields they do send (camera_id + timestamp + plate_text).
    match = db.execute(
        text("""
            SELECT observation_id FROM observation
            WHERE camera_id = :camera_id
              AND timestamp = :timestamp
              AND (plate_text = :plate_text OR (:plate_text IS NULL AND plate_text IS NULL))
            ORDER BY timestamp DESC
            LIMIT 1
        """),
        {
            "camera_id": identity.camera_id,
            "timestamp": identity.timestamp,
            "plate_text": identity.plate_text,
        }
    ).scalar()

    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"No matching observation found for camera_id={identity.camera_id}, "
                   f"timestamp={identity.timestamp}, plate_text={identity.plate_text}"
        )

    result = db.execute(
        text("""
            INSERT INTO vehicle_identity_links (
                vehicle_id, observation_id, identity_confidence,
                appearance_confidence, supporting_evidence
            ) VALUES (
                :vehicle_id, :observation_id, :identity_confidence,
                :appearance_confidence, :supporting_evidence
            )
            RETURNING id
        """),
        {
            "vehicle_id": identity.vehicle_id,
            "observation_id": match,
            "identity_confidence": identity.identity_confidence,
            "appearance_confidence": identity.appearance_confidence,
            "supporting_evidence": json.dumps(identity.supporting_evidence) if identity.supporting_evidence else None,
        }
    )
    db.commit()
    new_id = result.scalar()
    return {"id": str(new_id), "observation_id": str(match), "status": "created"}


# ---------- Trajectories (Person 3 -> Person 4 / Person 5) ----------

@app.post("/trajectories")
def create_trajectory(trajectory: TrajectoryIn, db: Session = Depends(get_db)):
    duration_interval = f"{trajectory.duration_sec} seconds" if trajectory.duration_sec is not None else None

    result = db.execute(
        text("""
            INSERT INTO trajectory (
                vehicle_id, trajectory_status, start_time, end_time,
                distance_meters, duration, trajectory_confidence
            ) VALUES (
                :vehicle_id, :trajectory_status, :start_time, :end_time,
                :distance_meters, :duration, :trajectory_confidence
            )
            RETURNING trajectory_id
        """),
        {
            "vehicle_id": trajectory.vehicle_id,
            "trajectory_status": trajectory.trajectory_status,
            "start_time": trajectory.start_time,
            "end_time": trajectory.end_time,
            "distance_meters": trajectory.distance_meters,
            "duration": duration_interval,
            "trajectory_confidence": trajectory.trajectory_confidence,
        }
    )
    trajectory_id = result.scalar()

    # sequence_number derived from array order — Person 3 doesn't send it
    for i, obs in enumerate(trajectory.observations):
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
            {
                "trajectory_id": trajectory_id,
                "sequence_number": i + 1,
                **obs.model_dump(),
            }
        )

    transition_id_map = {}
    for trans in trajectory.transitions:
        result_t = db.execute(
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
                RETURNING transition_id
            """),
            {"trajectory_id": trajectory_id, **trans.model_dump()}
        )
        transition_id_map[(trans.from_camera_id, trans.to_camera_id)] = result_t.scalar()

    # Store route geometry polyline points, linked to their transition
    if trajectory.route_geometry:
        for segment in trajectory.route_geometry:
            transition_id = transition_id_map.get((segment.from_camera_id, segment.to_camera_id))
            for i, point in enumerate(segment.points):
                db.execute(
                    text("""
                        INSERT INTO trajectory_route_geometry (
                            transition_id, sequence_number, latitude, longitude
                        ) VALUES (
                            :transition_id, :sequence_number, :latitude, :longitude
                        )
                    """),
                    {
                        "transition_id": transition_id,
                        "sequence_number": i + 1,
                        "latitude": point.lat,
                        "longitude": point.lon,
                    }
                )

    db.commit()
    return {"trajectory_id": str(trajectory_id), "status": "created"}


@app.get("/trajectories/{vehicle_id}")
def get_trajectories(vehicle_id: str, db: Session = Depends(get_db)):
    trajectories = db.execute(
        text("""
            SELECT trajectory_id, vehicle_id, trajectory_status, start_time, end_time,
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

        transitions_out = []
        route_geometry_out = []
        for t in transitions:
            t_dict = dict(t)
            geometry = db.execute(
                text("""
                    SELECT latitude as lat, longitude as lon
                    FROM trajectory_route_geometry
                    WHERE transition_id = :transition_id
                    ORDER BY sequence_number
                """),
                {"transition_id": t["transition_id"]}
            ).mappings().all()

            # Reconstruct the top-level route_geometry segment for this transition
            if geometry:
                route_geometry_out.append({
                    "from_camera_id": t["from_camera_id"],
                    "to_camera_id": t["to_camera_id"],
                    "points": [dict(g) for g in geometry]
                })

            t_dict["transition_id"] = str(t_dict["transition_id"])
            transitions_out.append(t_dict)

        traj_dict["observations"] = [dict(o) for o in observations]
        traj_dict["transitions"] = transitions_out
        traj_dict["route_geometry"] = route_geometry_out
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


# ---------- Intelligence (Person 4 -> Person 5): alerts + predictions + analytics ----------

@app.post("/intelligence")
def ingest_intelligence(payload: IntelligencePayloadIn, db: Session = Depends(get_db)):
    # 1. Ingest Alerts
    for alert in payload.alerts:
        db.execute(
            text("""
                INSERT INTO intelligence_events (
                    vehicle_id, event_type, severity, confidence, reason,
                    camera_range, time_range_start, time_range_end
                ) VALUES (
                    :vehicle_id, :event_type, :severity, :confidence, :reason,
                    :camera_range, :time_range_start, :time_range_end
                )
            """),
            alert.model_dump()
        )

    # 2. Ingest Predictions
    for vehicle_id, preds in payload.predictions.items():
        db.execute(
            text("""
                INSERT INTO vehicle_predictions (vehicle_id, predictions)
                VALUES (:vehicle_id, :predictions)
                ON CONFLICT (vehicle_id) DO UPDATE
                SET predictions = EXCLUDED.predictions, updated_at = now()
            """),
            {"vehicle_id": vehicle_id, "predictions": json.dumps(preds)}
        )

    # 3. Ingest Analytics
    if payload.analytics:
        db.execute(
            text("""
                INSERT INTO system_analytics (data)
                VALUES (:data)
            """),
            {"data": json.dumps(payload.analytics)}
        )

    db.commit()
    return {
        "status": "success",
        "alerts_processed": len(payload.alerts),
        "predictions_processed": len(payload.predictions),
    }


@app.get("/intelligence/predictions/{vehicle_id}")
def get_predictions(vehicle_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("SELECT predictions, updated_at FROM vehicle_predictions WHERE vehicle_id = :vehicle_id"),
        {"vehicle_id": vehicle_id}
    ).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="No predictions found for this vehicle")
    return {"vehicle_id": vehicle_id, "predictions": result["predictions"], "updated_at": result["updated_at"]}


@app.get("/intelligence/analytics/latest")
def get_latest_analytics(db: Session = Depends(get_db)):
    result = db.execute(
        text("SELECT data, created_at FROM system_analytics ORDER BY created_at DESC LIMIT 1")
    ).mappings().first()
    if not result:
        return {"data": {}, "message": "No analytics available yet"}
    return {"data": result["data"], "created_at": result["created_at"]}
