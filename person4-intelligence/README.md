# Person 4 — Prediction + Traffic Intelligence

## What this module does

Sits above Person 3's trajectory reconstruction engine. Person 3 answers
"where did this vehicle go" (a sequence of camera + timestamp
observations). This module answers three further questions from that
same data:

1. **Where is it likely to go next?** (prediction)
2. **What does traffic look like right now?** (analytics — density,
   congestion, speed, common routes)
3. **Is anything unusual happening?** (anomaly detection — abnormal
   travel time, routes that skip the known camera network, watchlist
   matches)

Output of all three feeds into `pipeline.py`, which is the single
entry point Person 5's backend will eventually call.

## Status

Fully built and testable standalone against mock data. Not yet wired
to Person 3's real trajectory service or Person 5's backend — both
integration points are stubbed via contracts (see below) so this
module doesn't block on either.

## Data flow

```
Person 3 (real, not built yet)  ──┐
                                   ├─▶ trajectory batch (list of dicts,
mock_data/trajectory_generator.py─┘    person3_to_person4.json shape)
                                          │
                                          ▼
                                    pipeline.py
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              prediction/            analytics/              anomaly/
          route_predictor.py    traffic_density.py    travel_time_anomaly.py
          markov_predictor.py   congestion.py          route_anomaly.py
                                travel_time.py          blacklist_check.py
                                od_matrix.py                  │
                    │                     │                     ▼
                    │                     │              alerts/alert_builder.py
                    ▼                     ▼                     │
              predictions{}         analytics{}                 ▼
                    │                     │              alerts[] (person4_to_person5.json shape)
                    └──────────┬──────────┴──────────────────────┘
                               ▼
                     { alerts, predictions, analytics }
                               │
                               ▼
                    Person 5 backend (not built yet)
```

## Folder structure

```
person4-intelligence/
├── config.py                       # tunable thresholds, one place to recalibrate
├── pipeline.py                     # entry point — runs everything, returns one dict
├── requirements.txt
├── mock_data/
│   └── trajectory_generator.py     # fake trajectories, stand-in for Person 3
├── prediction/
│   ├── route_predictor.py          # next-camera + multi-hop path prediction from static graph
│   └── markov_predictor.py         # next-camera prediction learned from observed data
├── analytics/
│   ├── traffic_density.py          # vehicles/hour per camera
│   ├── congestion.py               # flags camera-hours above a volume threshold
│   ├── travel_time.py              # empirical travel time + speed per camera-pair
│   └── od_matrix.py                # origin-destination counts + common routes
├── anomaly/
│   ├── travel_time_anomaly.py      # flags abnormally slow transitions
│   ├── route_anomaly.py            # flags graph-skipping or rare transitions
│   └── blacklist_check.py          # flags watchlisted vehicle_ids
├── alerts/
│   └── alert_builder.py            # packages anomalies into the Person4→5 alert contract
└── tests/
    ├── conftest.py                 # shared fixed graph + trajectory fixtures
    ├── test_prediction.py
    ├── test_analytics.py
    ├── test_anomaly.py
    ├── test_pipeline.py
    └── test_smoke.py               # random-data integration check (run as a script, not pytest)
```

## Modules in detail

### `config.py`

All magic numbers in one place:

| Constant | Default | Meaning |
|---|---|---|
| `TRAVEL_TIME_DEVIATION_THRESHOLD` | `2.0` | Observed travel time must exceed this × the graph's expected max to trigger a travel-time anomaly |
| `RARE_EDGE_PROBABILITY_THRESHOLD` | `0.2` | A graph edge with `historical_probability` below this is flagged as a rare route |
| `CONGESTION_VEHICLES_PER_HOUR` | `10` | Vehicles/hour at one camera at/above this counts as congested |

Recalibrate these against real Person 3 data once it exists — current
values are guesses tuned to make the mock generator's injected
anomalies detectable.

### `mock_data/trajectory_generator.py`

Stand-in for Person 3. Walks `docs/contracts/camera_graph.json`,
choosing each next camera weighted by `historical_probability`, and
stamps timestamps using the edge's expected travel time range.
`anomaly=True` occasionally injects a 2.5–4x travel-time inflation, so
the anomaly detectors have something to catch.

- `load_camera_graph(path=...)` — loads the camera graph JSON
- `generate_trajectory(graph, vehicle_id, start_camera=None, max_hops=4, start_time_seconds=..., anomaly=False)` — one fake trajectory record
- `generate_batch(n=20, anomaly_rate=0.15)` — `n` fake trajectory records

**Swap-out point:** once Person 3's real service exists, replace calls
to `generate_batch()` with whatever fetches real trajectories (API
call, DB query, message queue) — everything downstream consumes the
same `person3_to_person4.json` shape either way.

### `prediction/route_predictor.py`

Graph-based prediction — uses the static `historical_probability`
values baked into `camera_graph.json`.

- `predict_next(graph, current_camera, top_k=3)` — ranked `(camera_id, probability)` list of likely next stops
- `predict_from_trajectory(graph, trajectory_record, top_k=3)` — convenience wrapper, reads the last camera off a trajectory
- `predict_path(graph, current_camera, hops=3, beam_width=3)` — beam search, returns most likely full future paths as `(path_tuple, joint_probability)`

### `prediction/markov_predictor.py`

Data-driven prediction — learns transition frequencies from an actual
batch of trajectories instead of the static graph file. This is the
one that improves as real data accumulates; `route_predictor.py`
doesn't.

- `build_transition_model(trajectories)` — `{camera_id: Counter({next_camera: count})}`
- `predict_next(model, current_camera, top_k=3)` — ranked `(camera_id, observed_probability)` list

`pipeline.py` runs both predictors side by side (`graph_based` and
`history_based`) so the two can be compared once real data exists.

### `analytics/traffic_density.py`

- `vehicles_per_camera_per_hour(trajectories)` — `{camera_id: {hour_iso: count}}`
- `busiest_cameras(trajectories, top_k=5)` — ranked `(camera_id, total_observations)`

### `analytics/congestion.py`

- `congested_camera_hours(trajectories, threshold=CONGESTION_VEHICLES_PER_HOUR)` — list of `{camera, hour, count}` for every camera-hour bucket at/above threshold, sorted by count descending

### `analytics/travel_time.py`

- `extract_edge_times(trajectories)` — raw observed seconds per `(from, to)` camera pair
- `edge_stats(trajectories)` — `{avg, min, max, n}` per camera pair
- `expected_range(graph, from_camera, to_camera)` — the graph's expected `(min, max)` seconds for an edge, or `None` if unknown
- `average_speed_kmh(graph, trajectories)` — average speed per camera pair, using the graph's `distance_km` and observed average travel time

### `analytics/od_matrix.py`

- `origin_destination_counts(trajectories)` — `{(origin, destination): count}`, first-camera to last-camera per trajectory
- `most_common_routes(trajectories, top_k=5)` — ranked full camera-sequence routes with counts

### `anomaly/travel_time_anomaly.py`

- `check_trajectory(graph, trajectory_record, threshold=TRAVEL_TIME_DEVIATION_THRESHOLD)` — per-transition anomaly dicts where observed time exceeds `threshold × expected_max`. Transitions on unknown edges are skipped here (that's `route_anomaly.py`'s job).

### `anomaly/route_anomaly.py`

- `check_trajectory(graph, trajectory_record, rare_threshold=RARE_EDGE_PROBABILITY_THRESHOLD)` — flags two cases: a transition with no matching edge in the graph at all ("unexpected camera jump"), or a known edge whose `historical_probability` is below `rare_threshold`.

### `anomaly/blacklist_check.py`

- `check_trajectory(trajectory_record, watchlist)` — direct lookup, not statistical. Returns a match if `vehicle_id` is in the given `watchlist` set. Watchlist source (stolen-vehicle list, flagged plates) is Person 5's to supply — this module just does the check.

### `alerts/alert_builder.py`

Converts anomaly dicts from the three detectors above into the
`docs/contracts/person4_to_person5.json` shape:

```json
{
  "vehicle_id": "VEH_8421",
  "alert_type": "TRAJECTORY_ANOMALY | ROUTE_ANOMALY | BLACKLIST_MATCH",
  "severity": "LOW | MEDIUM | HIGH",
  "confidence": 0.0-1.0,
  "reason": "human-readable string"
}
```

- `build_travel_time_alert(anomaly)` — severity scales with deviation % (`>=200%` → HIGH, `>=100%` → MEDIUM, else LOW)
- `build_route_alert(anomaly)` — fixed MEDIUM severity, 0.75 confidence
- `build_blacklist_alert(anomaly)` — fixed HIGH severity, 1.0 confidence
- `build_alerts(travel_time_anomalies, route_anomalies, blacklist_anomalies=())` — combines all three into one flat list

### `pipeline.py`

The entry point. `run_intelligence_pipeline(graph, trajectories, watchlist=())`:

1. Builds a Markov transition model from the batch
2. For each trajectory: runs all three anomaly checks, builds alerts, runs both predictors
3. Computes all analytics functions over the whole batch
4. Returns:

```python
{
    "alerts": [...],                # list of person4_to_person5.json-shaped dicts
    "predictions": {                # per-vehicle
        "VEH_1234": {
            "graph_based": [(camera, prob), ...],
            "history_based": [(camera, prob), ...],
        },
    },
    "analytics": {
        "busiest_cameras": [...],
        "congested_camera_hours": [...],
        "origin_destination_counts": {...},
        "most_common_routes": [...],
        "edge_travel_time_stats": {...},
        "average_speed_kmh": {...},
    },
}
```

Run standalone: `python pipeline.py` — generates a mock batch, runs the
full pipeline, prints the result as JSON.

## Data contracts

Shared with the rest of the team, in `../docs/contracts/`:

| File | Direction | Used by |
|---|---|---|
| `camera_graph.json` | shared | Person 3 (owns it) + Person 4 (reads it) |
| `person3_to_person4.json` | in | Person 3 → Person 4 |
| `person4_to_person5.json` | out | Person 4 → Person 5 |

`analytics` output has no formal contract yet — it's plain dicts.
Person 5 will define the analytics API response shape when that
endpoint gets built; until then, whatever `pipeline.py` returns under
`"analytics"` is the reference shape.

## Setup

```bash
cd person4-intelligence
pip install -r requirements.txt
```

## Running / checking your work

```bash
# unit tests — each module in isolation, fixed deterministic fixtures
python3 -m pytest tests/ -v

# integration smoke test — random mock batch through the whole flow
python3 -m tests.test_smoke

# full pipeline — real output shape, inspect it directly
python3 pipeline.py | less
```

All 26 unit tests should pass. The smoke test and `pipeline.py` use
randomly generated mock data, so exact alert counts vary run to run —
what matters is no crash, sane analytics numbers, and at least some
alerts firing (since `anomaly_rate=0.3` guarantees some injected
anomalies).

## Known limitations / what's not real yet

- `camera_graph.json`'s cameras, distances, and `historical_probability`
  values are made up — replace with Person 3's real camera network
  once available.
- Thresholds in `config.py` are guesses, not calibrated against real
  traffic patterns.
- No persistence — `pipeline.py` runs in-memory per call; Person 5
  will handle storing alerts/analytics.
- `analytics` output shape isn't contract-frozen yet, since no
  consumer (Person 5's API, Person 6's frontend) exists to lock it in.

## Research question

Can historical camera and vehicle trajectories be used to predict
movement and identify statistically unusual traffic behaviour?

The `route_predictor.py` (static graph) vs. `markov_predictor.py`
(learned from data) split exists specifically to let this be answered
empirically once real trajectories accumulate — compare prediction
accuracy of the two over time.
