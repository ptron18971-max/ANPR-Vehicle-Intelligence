# Spatio-Temporal Graph + Trajectory Engine (Person 3)

## INPUT
- **Vehicle Observations**: ID, Camera, Timestamp, Confidence
- **Camera Locations / Road Graph**: Connections, avg/min/max travel times

## PROCESSING PIPELINE
1. **Candidate Path Generation**: Find all simple paths between disconnected camera observations.
2. **Temporal Validation**: Verify observed travel times fall within physical bounds.
3. **Spatio-Temporal Path Selection**: Score candidate paths based on time-error and select the most likely route.
4. **Gap Recovery**: Interpolate missing camera nodes and dynamically estimate intermediate timestamps.
5. **Confidence Scoring**: Calculate confidence for inferred nodes based on path time-error penalties.
6. **Outlier Rejection**: Rigorously flag impossible paths as `UNREACHABLE` or `INVALID_TIME`.

## EXPORT PIPELINE (Person 4 Interface)
- `person3_to_person4.json`: Complete trajectory reconstruction objects (VALID, RECOVERED, INVALID_TIME, UNREACHABLE).
- `person3_camera_graph.json`: Clean topology export for predictive modeling.

## OUTPUT
- Reconstructed chronologically sorted trajectory objects.
- High-fidelity edge transitions with accurate travel times and confidence scores.