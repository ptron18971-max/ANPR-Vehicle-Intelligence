# City Vehicle Intelligence System

Multi-camera vehicle tracking, cross-camera identity fusion, trajectory
reconstruction, and traffic intelligence platform.

## Team structure

| Folder | Owner | Responsibility |
|---|---|---|
| `cv/` | Person 1 | Vehicle detection, tracking, plate detection, OCR |
| `fusion/` | Person 2 | Vehicle re-identification, cross-camera identity fusion |
| `graph/` | Person 3 | Camera graph, trajectory reconstruction |
| `intelligence/` | Person 4 | Route prediction, traffic analytics, anomaly detection |
| `backend/` | Person 5 | APIs, database, event ingestion, deployment |
| `frontend/` | Person 6 | GIS dashboard, operator interface |

## Data flow

```
Camera → Person1 (observation) → Person2 (identity) → Person3 (trajectory)
       → Person4 (intelligence) → Person5 (backend/API) → Person6 (frontend)
```

## Contracts

Shared JSON contracts between pipeline stages live in `docs/contracts/`.
Each person's module should validate against these shapes at their
input/output boundary so integration doesn't break silently.
