# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: city traffic control room operators in Bengaluru — trained ops staff monitoring a live multi-camera ANPR network, tracking specific vehicles across the city, and triaging real-time anomaly alerts (restricted-zone re-entry, unusual dwell, plate-confidence issues).

Secondary (current, near-term): SIH hackathon evaluators judging the working prototype. Both audiences are live at once — the product must read as a genuine operational tool to Bengaluru traffic control *and* demonstrate technical depth to judges.

## Product Purpose

A city-wide vehicle intelligence platform: multi-camera detection, cross-camera identity fusion, trajectory reconstruction, and traffic anomaly intelligence, surfaced to operators through a real-time GIS dashboard. Success means an operator can find a vehicle, see its route across the camera network with visible confidence, and act on alerts they trust — not a black box.

## Positioning

Confidence-scored, explainable cross-camera tracking. Every hop in a reconstructed trajectory carries an explicit CONFIRMED / INFERRED / UNCERTAIN tier plus a numeric confidence score, so operators see *why* the system believes a vehicle went where it says, not just a plate-match claim. A neighboring "plate matching" product could not truthfully copy this — the trust comes from showing the seams, not hiding them.

## Operating Context

Six-stage pipeline, each stage owned by a different team member, contracts shared via `docs/contracts/`:

```
Camera → Person1 (detection/OCR) → Person2 (re-id / cross-camera identity fusion)
       → Person3 (trajectory graph reconstruction) → Person4 (route prediction / anomaly intelligence)
       → Person5 (backend: FastAPI + PostgreSQL/PostGIS, WebSocket live push)
       → Person6 (frontend: GIS operator dashboard)
```

Frontend is a control-room-style dashboard: live map (MapLibre GL, CARTO dark basemap), vehicle/camera/alert tables, a real-time detection stream over WebSocket, and a trajectory drill-down drawer. Operators work under time pressure triaging alerts, not casually browsing.

## Capabilities and Constraints

- Backend: FastAPI REST + WebSocket (`ws://.../ws/live`), PostgreSQL + PostGIS, Redis provisioned but unused.
- Served endpoints: `/cameras`, `/vehicles`, `/trajectories/{vehicle_id}`, `/alerts`; ingestion endpoints (`/observations`, `/identities`, `/trajectories`, `/events`) feed from Persons 1–4.
- Terminology (durable, do not rename casually): hop/transition status `CONFIRMED` / `INFERRED` / anything else treated as `UNCERTAIN`; `trajectory_status` `VALID` / `RECOVERED` / `INVALID_TIME` / `UNREACHABLE`; alert `severity` `LOW` / `MEDIUM` / `HIGH`.
- No citywide-aggregate analytics endpoints exist yet (traffic density heatmap, citywide segment speed, route/OD density). The frontend must keep showing these as "not yet available" rather than fabricating numbers, until Person4/5 ship the aggregate endpoints.
- Real-time is a hard expectation: the live detection feed and alert delivery must read as immediate, not batched.

## Brand Commitments

Product name: "City Vehicle Intelligence System" (whole platform) / "Vehicle Intelligence Platform" (frontend surface, tagged "City Traffic Operations").

## Evidence on Hand

Bengaluru is the real target deployment city. All current camera positions, vehicle records, plates, and alerts are synthetic/seeded (`backend/db/seed*.sql`) — there is no live camera integration yet and no real incidents, case studies, or press. Future work must not present seed data as real deployment history, and must not invent a different city, a live camera count, or a go-live date.

## Product Principles

1. Explainability over black-box confidence — every tracked hop and trajectory shows its confidence and tier; never collapse that into a single opaque "match" state.
2. No fabricated analytics — surface only what the real pipeline supports; a missing capability is labeled "not yet available," never simulated with placeholder numbers.
3. Real-time responsiveness is a product requirement, not a nice-to-have — live feed and alerts must feel immediate.
4. Design for two live audiences at once — Bengaluru ops credibility and hackathon technical-depth signal both have to land from the same build.
5. Respect the pipeline contract — the six stages integrate through `docs/contracts/`; frontend and backend changes must not silently drift from those shapes.
