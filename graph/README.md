# Person 3 — Spatio-Temporal Graph + Trajectory Reconstruction

Owns: camera network graph (`../docs/contracts/camera_graph.json`), road
topology, trajectory generation, temporal reasoning, route reconstruction,
missing-observation inference, and trajectory confidence.

Input:
Person 2 canonical vehicle observations.

Shared graph:
`../docs/contracts/camera_graph.json`
*Note: The shared graph contains the full spatial and temporal edge constraints (min/avg/max travel times and distances).*

Output:
`../docs/contracts/person3_to_person4.json`
*Note: Person 3 seamlessly reconstructs missing camera observations using the spatio-temporal constraints, exporting a complete trajectory.*

## Processing Pipeline Completed

1. **Candidate Path Generation**: Uses NetworkX to generate candidate simple
   paths between camera observations when intermediate observations are missing.

2. **Temporal Validation**: Verifies whether the observed travel time falls
   within the physical `[min_time, max_time]` bounds of a candidate path.

3. **Spatio-Temporal Path Selection**: Ranks temporally feasible candidate
   paths using travel-time error and selects the best-fitting route.

4. **Gap Recovery**: Reconstructs missing intermediate camera nodes and
   estimates their timestamps using the selected path's edge travel times.

5. **Confidence Scoring**: Assigns confidence scores to reconstructed
   observations based on observation confidence and temporal fit.

6. **Outlier Rejection**: Identifies impossible trajectories and classifies
   them as `UNREACHABLE` or `INVALID_TIME`.

7. **Trajectory & Transition Generation**: Produces ordered camera sequences,
   timestamps, transitions, distances, duration, and trajectory confidence.

8. **Export Pipeline**: Generates clean, Person 4-ready JSON containing the full reconstructed trajectories, chronological timestamps, transition distances, and strict CONFIRMED/INFERRED statuses.

## API Wrappers
To easily query the exported trajectory data, we expose two simple modules:

**1. `src/query.py`**
- `get_vehicle_trajectory(vehicle_id)`: Fetches full trajectory object.
- `get_vehicle_location(vehicle_id, timestamp)`: Looks up vehicle status at an exact timestamp.
- `get_vehicles_at_camera(camera_id)`: Finds all vehicles seen by a specific camera.
- `get_vehicle_transitions(vehicle_id)`: Retrieves the sequence of transitions/edges.
- `get_route_between_cameras(from_camera_id, to_camera_id)`: Fetches road-network geometry.

**2. `src/gis.py`**
- `get_camera_coordinates(camera_id)`: Maps a camera ID to lat/lon.
- `get_trajectory_coordinates(vehicle_id)`: Returns the chronological `[lat, lon]` array for plotting routes on a map.
- `get_road_route_coordinates(from_camera_id, to_camera_id)`: Returns the exact Google Maps road route geometry between two cameras.

## Road-Network Routing

- **Backend Integration**: Routing is performed exclusively backend-side via `src/routing.py`. It features a pluggable architecture supporting two providers via the `ROUTING_PROVIDER` environment variable.
- **Providers**:
  - `google`: Production provider using Google Maps Platform (Routes API V2). Requires `GOOGLE_MAPS_API_KEY`.
  - `osrm`: Development / SIH V1 testing fallback using the public OSRM API. This is the default if no key or provider is set.
- **Security**: API credentials are kept in environment variables (see `.env.example`) and are never exposed to the frontend.
- **Caching**: Route results (distance, duration, geometry) are cached locally in `data/route_cache.json` to eliminate redundant API requests and avoid high billing costs/rate limits.
- **Enrichment Layer**: Road routing acts purely as an enrichment layer for the canonical graph. It produces a `routing_distance_meters` property on edges but does not blindly overwrite carefully tuned spatial/temporal `min/avg/max` anomaly thresholds.
- **Resiliency**: The core trajectory engine does *not* depend on live routing API availability. The pipeline will flawlessly construct trajectories using the fallback or the raw canonical graph if APIs fail.

## Person 3 -> Person 4 Integration Contract

The sole output file passed to the team is `docs/contracts/person3_to_person4.json`. 
This file guarantees exactly one record per vehicle and does not require any Person 3 backend dependencies, libraries, or mock data.

**Schema:**
```json
[
  {
    "vehicle_id": "V001",
    "trajectory_status": "VALID|RECOVERED|INVALID_TIME|UNREACHABLE",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "camera_sequence": ["C01", "C02"],
    "timestamps": ["YYYY-MM-DDTHH:MM:SS", "YYYY-MM-DDTHH:MM:SS"],
    "observations": [
      {
        "camera_id": "C01",
        "timestamp": "YYYY-MM-DDTHH:MM:SS",
        "status": "CONFIRMED|INFERRED",
        "confidence": 0.95
      }
    ],
    "transitions": [
      {
        "from_camera_id": "C01",
        "to_camera_id": "C02",
        "travel_time_sec": 120.0,
        "distance_meters": 500.0,
        "status": "CONFIRMED|INFERRED",
        "confidence": 0.95
      }
    ],
    "route_geometry": [
      {
        "from_camera_id": "C01",
        "to_camera_id": "C02",
        "distance_meters": 500.0,
        "points": [
          {"lat": 12.9716, "lon": 77.5946},
          {"lat": 12.9718, "lon": 77.5950}
        ]
      }
    ],
    "distance_meters": 500.0,
    "duration_sec": 120.0,
    "trajectory_confidence": 0.95
  }
]
```
