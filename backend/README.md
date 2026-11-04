# Person 5 — Backend + Data Engineering

Backend for the City-Wide Vehicle Intelligence Platform. Owns the database, API layer, event ingestion, and real-time updates connecting all AI subsystems (Persons 1–4) to the frontend (Person 6).

## Stack

- **FastAPI** — REST + WebSocket API
- **PostgreSQL + PostGIS** — primary database
- **Redis** — provisioned for future caching/pub-sub (not yet used in app logic)
- **Docker Compose** — runs the full stack, including the FastAPI app itself

## Running the Backend

```bash
cd backend
docker compose up -d --build
```

This starts three containers: `vehicle_platform_db` (Postgres+PostGIS), `vehicle_platform_redis`, and `vehicle_platform_backend` (FastAPI app).

Check it's running:
```
http://127.0.0.1:8000/health/db
```
Interactive API docs (test any endpoint from the browser):
```
http://127.0.0.1:8000/docs
```

## Seeding Test Data

```bash
Get-Content db/seed_cameras.sql | docker exec -i vehicle_platform_db psql -U postgres -d vehicle_platform
Get-Content db/seed.sql | docker exec -i vehicle_platform_db psql -U postgres -d vehicle_platform
```

Note: `docker compose down -v` wipes the database volume — re-run both seed commands after any `-v` reset.

For the 120-vehicle demo dataset (12 graph-unreachable trajectories, 12
blacklist alerts, and otherwise graph-valid routes), generate and load
`db/mock_seed.sql` instead. This fixture truncates the existing camera and
vehicle data before loading:

```bash
python db/generate_mock_data.py
Get-Content db/mock_seed.sql | docker exec -i vehicle_platform_db psql -U postgres -d vehicle_platform
```

## API Reference

### Health

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | App liveness check |
| GET | `/health/db` | Confirms DB connectivity |

### Cameras & Vehicles

| Method | Route | Purpose |
|---|---|---|
| GET | `/cameras` | List all cameras with lat/lng, status, road segment |
| GET | `/vehicles` | List canonical vehicle identities, last-seen camera, and distinct `cameras_seen` |

### Ingestion (from Persons 1–4)

| Method | Route | Consumer | Purpose |
|---|---|---|---|
| POST | `/observations` | Person 1 | Submit a raw camera detection. Broadcasts live via WebSocket. |
| POST | `/identities` | Person 2 | Submit a cross-camera identity fusion result. **No `observation_id` required** — matched server-side via `camera_id` + `timestamp` + `plate_text` against the `observation` table. Returns 404 if no match is found. |
| POST | `/trajectories` | Person 3 | Submit a full reconstructed trajectory: `trajectory_status`, observations (sequence numbers auto-generated from array order), transitions, and optional `route_geometry` polyline points. |
| POST | `/events` | Person 4 | Submit an intelligence event / alert |

### Serving (to Person 6)

| Method | Route | Purpose |
|---|---|---|
| GET | `/trajectories/{vehicle_id}` | Get all trajectories for a vehicle, with nested observations, transitions, and route geometry |
| GET | `/alerts` | List stored intelligence events plus route and travel-time anomalies evaluated against `docs/contracts/camera_graph.json` |

### Real-Time

| Route | Purpose |
|---|---|
| `ws://.../ws/live` | WebSocket — receives a live push every time a new observation is created |

Graph-derived alerts are calculated from stored trajectory transitions when
`GET /alerts` is requested. Transitions whose cameras are not present in the
shared constraint graph are left unassessed; a missing graph entry is not
treated as an anomaly.

## Database Schema

9 tables, defined in `db/schema.sql`:
`camera`, `vehicles`, `observation`, `vehicle_identity_links`, `trajectory` (now includes `trajectory_status`: VALID/RECOVERED/INVALID_TIME/UNREACHABLE), `trajectory_observation`, `trajectory_transition`, `trajectory_route_geometry` (road polyline points per transition), `intelligence_events`.

`CameraEdge` intentionally excluded — Person 3 maintains the camera graph as a JSON config + NetworkX on their side.

## Integration Notes (Real Contracts)

Endpoints were updated to match Persons 2–4's actual data contracts, not just the original planning doc:

- **Person 2** sends `camera_id` + `timestamp` + `plate_text` instead of an internal `observation_id` — the backend resolves this via lookup.
- **Person 3** sends a flat observation array with no `sequence_number` — the backend derives it from array order. Person 3's contract also includes `trajectory_status` and `route_geometry` (actual road polylines from Google Maps/OSRM), both now stored.
- **Person 4** alert `event_type` values are uppercase (`TRAJECTORY_ANOMALY`, `ROUTE_ANOMALY`, `BLACKLIST_MATCH`) — stored as-is, no constraint enforced on this field.

## Open Items

- **Auth** — not yet implemented, pending confirmation on whether V1 requires it
- **Traffic analytics / OD matrix** — Person 4's `pipeline.py` produces this, but the output shape isn't contract-frozen yet; no storage/endpoint built on Person 5's side yet
- **Redis** — provisioned but not yet used; current WebSocket broadcast is in-memory, single-instance only

## Sample Test Payloads

Run these in order via `http://127.0.0.1:8000/docs` — later steps depend on IDs returned by earlier ones.

**1-4. `GET /health`, `/health/db`, `/cameras`, `/vehicles`** — no body needed.

**5. `POST /observations`**
```json
{
  "camera_id": "C01",
  "timestamp": "2026-08-25T09:00:00Z",
  "local_track_id": "T_101",
  "plate_text": "KA01AB1234",
  "plate_confidence": 0.91,
  "detection_confidence": 0.95,
  "vehicle_type": "car",
  "vehicle_color": "white",
  "bbox": [100, 200, 300, 400]
}
```

**6. `POST /identities`** (no `observation_id` needed — matched via camera/timestamp/plate)
```json
{
  "vehicle_id": "VEH_8421",
  "camera_id": "C01",
  "timestamp": "2026-08-25T09:00:00Z",
  "plate_text": "KA01AB1234",
  "identity_confidence": 0.93,
  "appearance_confidence": 0.89,
  "supporting_evidence": {
    "appearance_similarity": 0.91,
    "plate_match_score": 0.95,
    "attribute_match_score": 1.0,
    "match_strategy": "multimodal_fusion"
  }
}
```

**7. `POST /trajectories`**
```json
{
  "vehicle_id": "VEH_8421",
  "trajectory_status": "VALID",
  "start_time": "2026-08-25T09:00:00Z",
  "end_time": "2026-08-25T09:45:00Z",
  "distance_meters": 3200,
  "duration_sec": 2700,
  "trajectory_confidence": 0.9,
  "observations": [
    {"camera_id": "C01", "timestamp": "2026-08-25T09:00:00Z", "status": "CONFIRMED", "confidence": 0.93},
    {"camera_id": "C02", "timestamp": "2026-08-25T09:20:00Z", "status": "CONFIRMED", "confidence": 0.88},
    {"camera_id": "C04", "timestamp": "2026-08-25T09:45:00Z", "status": "INFERRED", "confidence": 0.6}
  ],
  "transitions": [
    {
      "from_camera_id": "C01",
      "to_camera_id": "C02",
      "from_timestamp": "2026-08-25T09:00:00Z",
      "to_timestamp": "2026-08-25T09:20:00Z",
      "travel_time_sec": 180,
      "distance_meters": 1100,
      "confidence": 0.9,
      "status": "CONFIRMED"
    },
    {
      "from_camera_id": "C02",
      "to_camera_id": "C04",
      "from_timestamp": "2026-08-25T09:20:00Z",
      "to_timestamp": "2026-08-25T09:45:00Z",
      "travel_time_sec": 220,
      "distance_meters": 2100,
      "confidence": 0.65,
      "status": "INFERRED"
    }
  ],
  "route_geometry": [
    {
      "from_camera_id": "C01",
      "to_camera_id": "C02",
      "distance_meters": 1100,
      "points": [
        {"lat": 12.9716, "lon": 77.5946},
        {"lat": 12.9735, "lon": 77.5975},
        {"lat": 12.9760, "lon": 77.6010}
      ]
    }
  ]
}
```

**8. `GET /trajectories/{vehicle_id}`** — enter `VEH_8421`

**9. `POST /events`**
```json
{
  "vehicle_id": "VEH_8421",
  "event_type": "BLACKLIST_MATCH",
  "severity": "HIGH",
  "confidence": 1.0,
  "reason": "Vehicle plate matches watchlist entry",
  "camera_range": ["C01", "C02"],
  "time_range_start": "2026-08-25T09:00:00Z",
  "time_range_end": "2026-08-25T09:45:00Z"
}
```

**10. `GET /alerts`** — no body needed