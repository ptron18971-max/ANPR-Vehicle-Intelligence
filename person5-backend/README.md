# Person 5 — Backend + Data Engineer

Owns: API layer (FastAPI), PostgreSQL + PostGIS schema, event ingestion,
WebSocket live updates, auth, deployment (Docker).

Consumes: Person 2 identities, Person 3 trajectories, Person 4 alerts
(`docs/contracts/person4_to_person5.json`).
Serves: REST/WebSocket APIs to Person 6 frontend.



# Person 5 — Backend + Data Engineering

Backend for the City-Wide Vehicle Intelligence Platform. Owns the database, API layer, event ingestion, and real-time updates connecting all AI subsystems (Persons 1–4) to the frontend (Person 6).

## Stack

- **FastAPI** — REST + WebSocket API
- **PostgreSQL + PostGIS** — primary database
- **Redis** — caching / pub-sub (reserved for future use)
- **Docker Compose** — runs the full stack

## Running the Backend

```bash
cd person5-backend
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
| GET | `/vehicles` | List canonical vehicle identities |

### Ingestion (from Persons 1–4)

| Method | Route | Consumer | Purpose |
|---|---|---|---|
| POST | `/observations` | Person 1 | Submit a raw camera detection. Broadcasts live via WebSocket. |
| POST | `/identities` | Person 2 | Submit a cross-camera identity fusion result |
| POST | `/trajectories` | Person 3 | Submit a full reconstructed trajectory (with nested observations + transitions) |
| POST | `/events` | Person 4 | Submit an intelligence event / alert |

### Serving (to Person 6)

| Method | Route | Purpose |
|---|---|---|
| GET | `/trajectories/{vehicle_id}` | Get all trajectories for a vehicle, with nested observations and transitions |
| GET | `/alerts` | List all intelligence events / alerts |

### Real-Time

| Route | Purpose |
|---|---|
| `ws://.../ws/live` | WebSocket — receives a live push every time a new observation is created |

## Database Schema

8 tables, defined in `db/schema.sql`:
`camera`, `vehicles`, `observation`, `vehicle_identity_links`, `trajectory`, `trajectory_observation`, `trajectory_transition`, `intelligence_events`.

`CameraEdge` intentionally excluded — Person 3 maintains the camera graph as a JSON config + NetworkX on their side.

## Open Items

- **Auth** — not yet implemented, pending confirmation on whether V1 requires it
- **Real payload validation** — endpoints match the team's agreed contracts; may need small adjustments once Persons 1–4's real pipelines are producing live data
- **Traffic analytics / OD matrix** — not yet built, pending Person 4 confirming output shape