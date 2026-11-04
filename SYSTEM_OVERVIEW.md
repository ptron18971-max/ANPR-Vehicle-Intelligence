# System Overview

This document explains how the City-Wide Vehicle Intelligence Platform is
organized, how data moves through it, and what the important files are for.
It describes the code currently in this repository; it is not a claim that
every stage is deployed as a single always-on service.

## 1. What the system does

The platform is a multi-camera vehicle monitoring and traffic intelligence
prototype. Its processing stages can:

1. Detect and track vehicles in camera video, read license plates, and
   estimate vehicle attributes.
2. Compare observations from different cameras and assign canonical vehicle
   identities.
3. Reconstruct camera-to-camera trajectories, including plausible missing
   intermediate observations.
4. Calculate route predictions and traffic analytics, and detect route,
   travel-time, or watchlist anomalies.
5. Store results behind an API and present them in an operator dashboard.

The processing stages exchange JSON data through the files in
`docs/contracts/`. The backend also exposes HTTP endpoints and a WebSocket for
the dashboard and for ingestion clients.

## 2. Repository map

| Path | Responsibility |
|---|---|
| `cv/` | Video-based vehicle detection, tracking, plate OCR, and attributes |
| `fusion/` | Visual embeddings and multi-signal vehicle identity matching |
| `graph/` | Camera graph, trajectory reconstruction, and route geometry |
| `intelligence/` | Predictions, traffic analytics, anomaly checks, and alerts |
| `backend/` | FastAPI service, database access, schema, and Docker Compose stack |
| `frontend/` | React dashboard with backend-connected and synthetic-data modes |
| `docs/contracts/` | Shared stage-to-stage JSON contracts and camera graph |
| `output/` | `cv`'s generated tracked videos, crop images, and observation JSON |
| `run_e2e_pipeline.py` | Batch runner using the `fusion` pipeline on `cv` output |
| `run_new_e2e.py` | Alternate batch runner that normalizes existing `cv` output |

Generated contents in `output/`, database state, route cache, and similar
runtime data are not source code. Their presence or freshness depends on
whether the corresponding pipeline has been run.

## 3. End-to-end data flow

```text
Camera video
    |
    v
cv: detect + track + plate OCR + attributes
    |  output/json/*_observations.json
    v
fusion: appearance embeddings + plate/attribute fusion
    |  docs/contracts/person2_to_person3.json
    v
graph: graph-constrained trajectory reconstruction
    |  docs/contracts/person3_to_person4.json
    v
intelligence: anomalies + predictions + traffic analytics
    |  docs/contracts/person4_to_person5.json
    v
backend: FastAPI + PostgreSQL/PostGIS
    |  REST API + WebSocket
    v
frontend: operator dashboard
```

Each stage can also be run and inspected independently. The root E2E scripts
orchestrate selected batch steps, but they do not make the video processor,
backend, and frontend one monolithic process.

## 4. Workflow by stage

### Stage 1 — Video detection and ANPR (`cv`)

`cv/main.py` is the video-processing entry point. Its
`process_video(video_path, camera_id)` function creates a `VehicleTracker`,
processes the video, and saves observations under
`output/json/<camera_id>_observations.json`. Running `main.py` directly scans
for `vdo.avi` under a dataset directory configured in that file. The helper
`cv/run.py` is another example runner with a hardcoded video path;
edit that path before using it.

`cv/tracker.py` contains the processing components:

- `VehicleTracker` runs YOLO vehicle tracking and tracks per-camera local
  track IDs across frames.
- `PlateDetector` detects a plate within a vehicle crop.
- `OCRProcessor` reads plate characters with EasyOCR.
- `ColorPredictor` classifies vehicle color using the configured ONNX or
  PyTorch model.
- Vehicle crops and annotated output videos are written beneath `output/`
  when enabled.

`cv/config.py` defines model paths, detection thresholds, vehicle
classes, output folders, frame sampling, and CPU/CUDA selection.
`cv/requirements.txt` lists this stage's Python dependencies;
the model weights are in `cv/models/`.

The raw observation output is a JSON list of per-frame vehicle observations
for the requested camera, including local track IDs and attribute/crop
references. It is not automatically the same shape as the canonical `fusion`
output contract.

### Stage 2 — Cross-camera identity fusion (`fusion`)

The Python package is in `fusion/src/vehicle_reid/`.

- `schemas.py` validates `cv` observations and canonical identity results.
- `embeddings/preprocessor.py` prepares vehicle images and evaluates crop
  quality.
- `embeddings/backbones.py` provides the embedding network components.
- `embeddings/extractor.py` exposes embedding extraction for individual
  observations and batches.
- `vector_store.py` indexes embeddings and searches for similar prior
  vehicles.
- `fusion.py` combines appearance similarity, fuzzy plate similarity, and
  vehicle type/color agreement into identity evidence and confidence.
- `pipeline.py` validates an observation, finds candidate matches, assigns
  an existing or new `vehicle_id`, and adds the embedding and metadata to the
  vector store.
- `context.py` and `diagnostics.py` provide pipeline context and diagnostic
  helpers.

The package writes its canonical records to
`docs/contracts/person2_to_person3.json` when invoked by
`run_e2e_pipeline.py`. The vector store used by that runner is constructed
for the run; it is not a persistent cross-run identity database by default.

### Stage 3 — Trajectory reconstruction (`graph`)

`graph/src/pipeline.py` reads
`docs/contracts/person2_to_person3.json`, groups observations by
`vehicle_id`, reconstructs each vehicle's path, and writes
`docs/contracts/person3_to_person4.json`.

Core modules:

- `graph.py` loads the shared directed camera graph from
  `docs/contracts/camera_graph.json`.
- `trajectory.py` orders observations and reconstructs direct transitions
  or missing intermediate camera visits.
- `validator.py` checks whether observed transition times fit graph travel
  constraints.
- `pipeline.py` assigns trajectory status, observation/transition
  confidence, duration, distance, and optional route geometry, then exports
  the `intelligence` contract.
- `routing.py` enriches eligible camera transitions with road-route
  geometry. It supports OSRM by default and Google Routes when configured;
  route geometry enrichment is separate from the core graph-based
  reconstruction.
- `gis.py` maps camera IDs to coordinates and returns coordinates for
  routes and trajectories.
- `query.py` provides lookup helpers over the trajectory data.
- `validate_graph.py` checks graph data and `demo_route_selection.py`
  demonstrates route selection.

Trajectory records distinguish observed (`CONFIRMED`) camera observations
from reconstructed (`INFERRED`) ones. Trajectories are assigned statuses such
as `VALID`, `RECOVERED`, `INVALID_TIME`, or `UNREACHABLE`.

### Stage 4 — Traffic intelligence (`intelligence`)

`intelligence/pipeline.py` coordinates the intelligence stage. It can
run against mock-generated inputs or load the real `graph` graph and
trajectory contract. Its consolidated result contains `alerts`,
`predictions`, and `analytics`.

- `adapters/person3_contract.py` loads and adapts the `graph` graph and
  trajectory JSON for this stage.
- `prediction/route_predictor.py` predicts routes using the camera graph.
- `prediction/markov_predictor.py` builds a transition model from trajectory
  history and predicts likely next cameras.
- `anomaly/travel_time_anomaly.py` detects travel times outside expected
  bounds.
- `anomaly/route_anomaly.py` flags unexpected camera transitions.
- `anomaly/blacklist_check.py` checks trajectories against a watchlist.
- `alerts/alert_builder.py` converts anomaly findings into alert records.
- `analytics/traffic_density.py`, `congestion.py`, `od_matrix.py`, and
  `travel_time.py` calculate camera activity, congestion, origin-destination
  counts, route frequency, travel-time statistics, and speed summaries.
- `mock_data/trajectory_generator.py` and `config.py` support local testing
  and configuration.

When called by `run_e2e_pipeline.py` or `run_new_e2e.py`, the real-data mode
reads `graph` output and writes its JSON result to
`docs/contracts/person4_to_person5.json`.

### Stage 5 — API and persistence (`backend`)

`backend/app/main.py` defines the FastAPI application, request
schemas, HTTP routes, and `/ws/live` WebSocket. The API includes:

- Health: `GET /health` and `GET /health/db`
- Dashboard reads: `GET /cameras`, `GET /vehicles`,
  `GET /trajectories/{vehicle_id}`, and `GET /alerts`
- Stage ingestion: `POST /observations`, `POST /identities`,
  `POST /trajectories`, and `POST /events`
- Consolidated intelligence: `POST /intelligence`, plus prediction and
  analytics read endpoints under `/intelligence/...`

New observations are broadcast to connected WebSocket clients. The live
WebSocket is an in-memory broadcast mechanism; Redis is provisioned in the
stack but is not used for pub/sub in the current application code. `GET
/alerts` combines stored intelligence events with route and travel-time
anomalies evaluated from persisted trajectory transitions against
`docs/contracts/camera_graph.json`; camera pairs outside the graph are left
unassessed. `GET /vehicles` includes distinct `cameras_seen` values alongside
each vehicle's most recently observed camera.

`backend/app/database.py` loads database configuration and supplies
SQLAlchemy sessions. `backend/db/schema.sql` defines camera,
observation, vehicle, identity-link, trajectory, transition, route geometry,
event, prediction, and analytics tables. `seed_cameras.sql` and `seed.sql`
provide initial camera and sample vehicle data; `mock_seed.sql` and
`generate_mock_data.py` create the 120-vehicle demo set, including 12
graph-unreachable trajectories, 12 blacklist matches, and graph-valid routes
for the remaining vehicles.

`backend/Dockerfile` builds the API container.
`backend/docker-compose.yml` runs the backend with PostgreSQL/PostGIS
and Redis. `backend/.env.example` documents environment configuration.
The backend README provides the commands for starting the stack and seeding
data.

### Stage 6 — Dashboard (`frontend`)

The frontend is a React/TypeScript application built with Vite.
`frontend/src/main.tsx` mounts `App.tsx`. `App.tsx` coordinates data
loading, live/synthetic mode selection, filters, module panes, vehicle and
alert selection, and the synthetic simulation clock.

Data access:

- `src/api/client.ts` calls the backend REST endpoints and defines the API
  base URL and WebSocket URL.
- `src/api/synthetic.ts` loads the static files in
  `public/synthetic-json/` and converts camera observations into dashboard
  cameras, vehicles, alerts, trajectories, and feed entries.
- `src/hooks/useApiResource.ts` handles resource loading, errors, reloads,
  and optional polling.
- `src/hooks/useLiveFeed.ts` connects to `/ws/live` and reconnects when the
  socket is interrupted.
- `src/types.ts` defines the frontend's shared data types.

The primary UI is built from:

- `components/TopBar.tsx` — title, vehicle search, mode control, connection
  status, and tracked-vehicle count.
- `components/Dock.tsx`, `Workspace.tsx`, and `StatusBar.tsx` — module
  navigation and pane layout.
- `components/MapView.tsx` and `SyntheticMap.tsx` — live API map and
  synthetic map presentations.
- `components/VehicleTable.tsx`, `CameraTable.tsx`, `AlertsPanel.tsx`,
  `AnalyticsPanel.tsx`, and `LiveFeedPanel.tsx` — dashboard data panels.
- `components/TrajectoryPanel.tsx` — selected-vehicle trajectory detail.
- `components/FilterBar.tsx`, `SearchBar.tsx`, and `MapLegend.tsx` — search,
  filters, and map controls.
- `components/StatusStates.tsx`, `ConfidenceBar.tsx`, and
  `CollapsiblePanel.tsx` — shared presentation helpers.
- `lib/format.ts` and `lib/icons.tsx` — formatting and icon utilities.
- `index.css` — global theme and styles.

In synthetic mode the dashboard reads its bundled static data and simulates
feed timing; this mode does not represent a live camera connection and does
not require the backend. In live mode the frontend expects the backend at
`http://127.0.0.1:8000` and the WebSocket at
`ws://127.0.0.1:8000/ws/live`.

## 5. Shared contracts and runtime data

`docs/contracts/` is the main integration boundary between the batch
processing stages:

| File | Purpose |
|---|---|
| `camera_graph.json` | Directed camera connections and spatial/temporal route constraints used by `graph` and `intelligence` |
| `person2_to_person3.json` | Canonical vehicle observations consumed by `graph` |
| `person3_to_person4.json` | Reconstructed trajectories consumed by `intelligence` and optionally the backend |
| `person4_to_person5.json` | `intelligence` alerts, predictions, and analytics consumed by `backend` |

The JSON files are outputs or shared datasets, not executable modules. They
may be regenerated by pipeline runs. Confirm the source and intended schema
before overwriting any contract file.

`cv` observation files are written to `output/json/`. Its associated
annotated video and vehicle crops are written to `output/videos/` and
`output/crops/`. The frontend's synthetic source files instead live in
`frontend/public/synthetic-json/`.

## 6. Batch workflow runners

### `run_e2e_pipeline.py`

This runner orchestrates:

1. `fusion` Re-ID over `output/json/*_observations.json`.
2. `graph` trajectory reconstruction.
3. `intelligence` in real-data mode.
4. `backend` ingestion over HTTP.

The `cv` launch is currently commented out in this script. Therefore,
`cv` output must already exist before running it. `fusion` writes
`person2_to_person3.json`; `graph` writes `person3_to_person4.json`;
`intelligence` writes `person4_to_person5.json`. For ingestion, the `backend` API and database
must already be running and populated with the necessary camera rows. In
this runner, `fusion` writes the identity contract file for `graph`; the
runner does not POST `cv` observations or `fusion` identities to their
corresponding backend endpoints.

### `run_new_e2e.py`

This alternate runner does not execute `fusion`'s embedding/fusion pipeline.
Instead, it expects input files shaped as camera bundles with a `camera_id`
and `frames[].vehicles[]`, uses source vehicle IDs to normalize those records
into the Person 2-to-3 contract, and then runs `graph`, `intelligence`, and `backend` ingestion. `cv`'s current
`main.py` output is a flat list of
observations, so check/convert the input format before using this runner with
those files. Its current normalization code also expects 70 distinct source
vehicles; that is a dataset-specific assumption, not a general `fusion`
requirement.

These runners are batch integration utilities, not server startup commands.
For API and dashboard startup instructions, see
`backend/README.md` and `frontend/README.md`.

## 7. Typical local startup

For the backend-connected dashboard:

1. Start Docker Desktop.
2. In `backend/`, run `docker compose up -d --build`.
3. Check `http://127.0.0.1:8000/health/db` and, if necessary, apply the
   camera/sample seed SQL described in the backend README.
4. In another terminal, enter `frontend/`, run `npm install` once,
   then `npm run dev`.
5. Open the Vite URL printed in the terminal (normally
   `http://localhost:5173`).

For a synthetic-only dashboard preview, start only the frontend and switch
to Synthetic mode. Static synthetic files are served from the frontend's
`public/` directory.

Running the video-to-intelligence batch pipeline requires its Python
dependencies, local model files, input videos, contract data, and a running
backend for the final ingestion stage. Consult each module README and the
runner-specific notes above before executing it.
