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

8. **Export Pipeline**: Generates a clean Person-4-ready JSON contract with
   chronological trajectories and strict `CONFIRMED` / `INFERRED` observation
   statuses.
