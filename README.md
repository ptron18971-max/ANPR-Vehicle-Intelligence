# City Vehicle Intelligence System

Multi-camera vehicle tracking, cross-camera identity fusion, trajectory
reconstruction, and traffic intelligence platform.

## Team structure

| Folder | Owner | Responsibility |
|---|---|---|
| `person1-cv-anpr/` | Person 1 | Vehicle detection, tracking, plate detection, OCR |
| `person2-reid-fusion/` | Person 2 | Vehicle re-identification, cross-camera identity fusion |
| `person3-trajectory-graph/` | Person 3 | Camera graph, trajectory reconstruction |
| `person4-intelligence/` | Person 4 | Route prediction, traffic analytics, anomaly detection |
| `person5-backend/` | Person 5 | APIs, database, event ingestion, deployment |
| `person6-frontend/` | Person 6 | GIS dashboard, operator interface |

## Data flow

```
Camera → Person1 (observation) → Person2 (identity) → Person3 (trajectory)
       → Person4 (intelligence) → Person5 (backend/API) → Person6 (frontend)
```

## Contracts

Shared JSON contracts between pipeline stages live in `docs/contracts/`.
Each person's module should validate against these shapes at their
input/output boundary so integration doesn't break silently.
