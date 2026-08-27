-- Camera (canonical table)
CREATE TABLE camera (
    camera_id      VARCHAR PRIMARY KEY,
    location       GEOGRAPHY(POINT),
    road_segment   VARCHAR,
    status         VARCHAR,
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
    plate_confidence       FLOAT,
    detection_confidence   FLOAT,
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
    camera_id                VARCHAR REFERENCES camera(camera_id),
    timestamp                 TIMESTAMPTZ NOT NULL,
    plate_text                VARCHAR,
    embedding_ref             VARCHAR,
    identity_confidence       FLOAT,
    appearance_confidence     FLOAT,
    supporting_evidence       JSONB
);

-- Trajectory (Person 3 to Person 4) — high-level journey
CREATE TABLE trajectory (
    trajectory_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id             VARCHAR REFERENCES vehicles(vehicle_id),
    start_time              TIMESTAMPTZ,
    end_time                 TIMESTAMPTZ,
    distance_meters           FLOAT,
    duration                   INTERVAL,
    trajectory_confidence       FLOAT
);

-- Trajectory Observation (Person 3) — one row per camera point in a trajectory
CREATE TABLE trajectory_observation (
    trajectory_observation_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trajectory_id                 UUID REFERENCES trajectory(trajectory_id),
    camera_id                      VARCHAR REFERENCES camera(camera_id),
    timestamp                       TIMESTAMPTZ NOT NULL,
    sequence_number                  INTEGER,
    status                             VARCHAR,   -- CONFIRMED / INFERRED
    confidence                         FLOAT,
    source_observation_id               UUID REFERENCES observation(observation_id)
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
    confidence                       FLOAT,
    status                             VARCHAR   -- CONFIRMED / INFERRED
);

-- Intelligence Events / Alerts (Person 4 to Person 5)
CREATE TABLE intelligence_events (
    event_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id           VARCHAR REFERENCES vehicles(vehicle_id),
    event_type            VARCHAR,
    severity                VARCHAR,
    confidence               FLOAT,
    reason                     TEXT,
    camera_range               VARCHAR[],
    time_range_start           TIMESTAMPTZ,
    time_range_end             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

-- Traffic Analytics (Person 4) — density, avg speed, route density, congestion. TO CONFIRM with Person 4.
CREATE TABLE traffic_analytics (
    analytics_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id       VARCHAR REFERENCES camera(camera_id),
    time_bucket       TIMESTAMPTZ,
    metric_type        VARCHAR,   -- density / avg_speed / route_density / congestion
    value                FLOAT,
    unit                  VARCHAR
);

-- OD Matrix (Person 4) — Origin-Destination analysis. TO CONFIRM with Person 4.
CREATE TABLE od_matrix (
    od_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_zone       VARCHAR,
    destination_zone  VARCHAR,
    time_bucket       TIMESTAMPTZ,
    vehicle_count     INTEGER
);