-- Camera (canonical table)
CREATE TABLE camera (
    camera_id      VARCHAR PRIMARY KEY,
    location       GEOGRAPHY(POINT, 4326),
    road_segment   VARCHAR,
    status         VARCHAR CHECK (status IN ('active', 'offline')),
    installed_at   TIMESTAMPTZ
);

-- Vehicle (canonical table)
CREATE TABLE vehicles (
    vehicle_id      VARCHAR PRIMARY KEY,
    plate_text      VARCHAR,
    vehicle_type    VARCHAR,
    vehicle_color   VARCHAR,
    first_seen      TIMESTAMPTZ,
    last_seen       TIMESTAMPTZ
);

-- Observation (Person 1 to Person 2)
CREATE TABLE observation (
    observation_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id             VARCHAR REFERENCES camera(camera_id),
    timestamp              TIMESTAMPTZ NOT NULL,
    local_track_id         VARCHAR,
    plate_text             VARCHAR,
    plate_confidence       FLOAT CHECK (plate_confidence BETWEEN 0 AND 1),
    detection_confidence   FLOAT CHECK (detection_confidence BETWEEN 0 AND 1),
    vehicle_type           VARCHAR,
    vehicle_color          VARCHAR,
    vehicle_crop_ref       VARCHAR,
    bbox                    INTEGER[4]
);

-- Vehicle Identity Links (Person 2 to Person 3)
CREATE TABLE vehicle_identity_links (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id               VARCHAR REFERENCES vehicles(vehicle_id),
    observation_id           UUID REFERENCES observation(observation_id),
    embedding_ref             VARCHAR,
    identity_confidence       FLOAT CHECK (identity_confidence BETWEEN 0 AND 1),
    appearance_confidence     FLOAT CHECK (appearance_confidence BETWEEN 0 AND 1),
    supporting_evidence       JSONB
);

-- Trajectory (Person 3 to Person 4) — high-level journey
CREATE TABLE trajectory (
    trajectory_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id             VARCHAR REFERENCES vehicles(vehicle_id),
    trajectory_status        VARCHAR CHECK (trajectory_status IN ('VALID', 'RECOVERED', 'INVALID_TIME', 'UNREACHABLE')),
    start_time              TIMESTAMPTZ,
    end_time                 TIMESTAMPTZ,
    distance_meters           FLOAT,
    duration                   INTERVAL,
    trajectory_confidence       FLOAT CHECK (trajectory_confidence BETWEEN 0 AND 1)
);

-- Trajectory Observation (Person 3) — one row per camera point in a trajectory
CREATE TABLE trajectory_observation (
    trajectory_observation_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trajectory_id                 UUID REFERENCES trajectory(trajectory_id),
    camera_id                      VARCHAR REFERENCES camera(camera_id),
    timestamp                       TIMESTAMPTZ,
    sequence_number                  INTEGER,
    status                             VARCHAR CHECK (status IN ('CONFIRMED', 'INFERRED')),
    confidence                         FLOAT CHECK (confidence BETWEEN 0 AND 1),
    source_observation_id               UUID REFERENCES observation(observation_id),
    UNIQUE (trajectory_id, sequence_number)
);

-- Trajectory Transition (Person 3) — one row per camera-to-camera hop
CREATE TABLE trajectory_transition (
    transition_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trajectory_id           UUID REFERENCES trajectory(trajectory_id),
    from_camera_id           VARCHAR REFERENCES camera(camera_id),
    to_camera_id              VARCHAR REFERENCES camera(camera_id),
    from_timestamp             TIMESTAMPTZ,
    to_timestamp                 TIMESTAMPTZ,
    travel_time_sec                INTEGER,
    distance_meters                 FLOAT,
    confidence                       FLOAT CHECK (confidence BETWEEN 0 AND 1),
    status                             VARCHAR CHECK (status IN ('CONFIRMED', 'INFERRED'))
);

-- Trajectory Route Geometry (Person 3) — actual road polyline points per transition
CREATE TABLE trajectory_route_geometry (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transition_id           UUID REFERENCES trajectory_transition(transition_id),
    sequence_number           INTEGER,
    latitude                   FLOAT,
    longitude                   FLOAT
);

-- Intelligence Events / Alerts (Person 4 to Person 5)
CREATE TABLE intelligence_events (
    event_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id           VARCHAR REFERENCES vehicles(vehicle_id),
    event_type            VARCHAR,
    severity                VARCHAR,
    confidence               FLOAT CHECK (confidence BETWEEN 0 AND 1),
    reason                     TEXT,
    camera_range               VARCHAR[],
    time_range_start           TIMESTAMPTZ,
    time_range_end             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now()
);