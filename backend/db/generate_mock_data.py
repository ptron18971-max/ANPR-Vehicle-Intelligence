from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import random
import uuid


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "mock_seed.sql"
random.seed(20260905)

COLORS = ["white", "black", "silver", "red", "blue", "green", "yellow", "gray"]
TYPES = ["car", "bike", "truck", "bus", "van"]
GRAPH_PATH = ROOT.parents[1] / "docs" / "contracts" / "camera_graph.json"
with GRAPH_PATH.open(encoding="utf-8") as graph_file:
    CAMERA_GRAPH = json.load(graph_file)

GRAPH_ADJACENCY = {}
GRAPH_NODES = set()
for edge in CAMERA_GRAPH["edges"]:
    GRAPH_ADJACENCY.setdefault(edge["from_camera"], []).append(edge)
    GRAPH_NODES.update((edge["from_camera"], edge["to_camera"]))


def unreachable_pairs():
    pairs = []
    for source in sorted(GRAPH_NODES):
        visited = {source}
        pending = [source]
        while pending:
            current = pending.pop()
            for edge in GRAPH_ADJACENCY.get(current, []):
                target = edge["to_camera"]
                if target not in visited:
                    visited.add(target)
                    pending.append(target)
        pairs.extend(
            (source, target)
            for target in sorted(GRAPH_NODES - visited)
            if GRAPH_ADJACENCY.get(target)
        )
    if not pairs:
        raise ValueError("Camera graph has no unreachable camera pairs for demo alerts")
    return pairs


UNREACHABLE_PAIRS = unreachable_pairs()


class RawSql(str):
    pass


def sql(value):
    if isinstance(value, RawSql):
        return value
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def build_route(vehicle_index, route_length, camera_by_id):
    unreachable = vehicle_index < 12
    if unreachable:
        candidate_pairs = UNREACHABLE_PAIRS[vehicle_index:] + UNREACHABLE_PAIRS[:vehicle_index]
        for source_id, target_id in candidate_pairs:
            remaining_edges = extend_route([source_id, target_id], route_length - 2, vehicle_index)
            if remaining_edges is not None:
                camera_ids = [source_id, target_id, *(edge["to_camera"] for edge in remaining_edges)]
                travel_times = [600, *(round(edge["avg_travel_time_sec"]) for edge in remaining_edges)]
                break
        else:
            raise ValueError(f"No unreachable route found for vehicle {vehicle_index}")
    else:
        for start_id in sorted(GRAPH_NODES):
            remaining_edges = extend_route([start_id], route_length - 1, vehicle_index)
            if remaining_edges is not None:
                camera_ids = [start_id, *(edge["to_camera"] for edge in remaining_edges)]
                travel_times = [round(edge["avg_travel_time_sec"]) for edge in remaining_edges]
                break
        else:
            raise ValueError(f"No graph-valid route found for vehicle {vehicle_index}")

    return [camera_by_id[camera_id] for camera_id in camera_ids], travel_times, unreachable


def extend_route(camera_ids, hops, offset):
    if hops == 0:
        return []
    outgoing = GRAPH_ADJACENCY.get(camera_ids[-1], [])
    candidates = [edge for edge in outgoing if edge["to_camera"] not in camera_ids]
    if not candidates:
        return None
    for index in range(len(candidates)):
        edge = candidates[(offset + index) % len(candidates)]
        extended = extend_route([*camera_ids, edge["to_camera"]], hops - 1, offset)
        if extended is not None:
            return [edge, *extended]
    return None


def make_rows():
    cameras = []
    camera_rng = random.Random(20260905)
    for index in range(60):
        camera_id = f"C{index + 1:02d}"
        # Scatter cameras across the synthetic Bengaluru-area viewport instead
        # of placing them on a regular row/column grid.
        latitude = round(camera_rng.uniform(12.9000, 13.0200), 6)
        longitude = round(camera_rng.uniform(77.5000, 77.6300), 6)
        status = "offline" if index in {11, 28, 47} else "active"
        cameras.append((camera_id, latitude, longitude, f"Sector {index // 10 + 1} Road {index % 10 + 1}", status))

    vehicles = []
    observations = []
    identities = []
    trajectories = []
    trajectory_observations = []
    transitions = []
    geometry = []
    alerts = []
    camera_by_id = {camera[0]: camera for camera in cameras}
    base_time = datetime(2026, 8, 25, 6, 0, tzinfo=timezone.utc)

    for vehicle_index in range(120):
        vehicle_id = f"VEH_{9000 + vehicle_index:04d}"
        plate = f"KA{vehicle_index % 99 + 1:02d}{chr(65 + vehicle_index % 26)}{chr(65 + (vehicle_index * 3) % 26)}{vehicle_index:04d}"
        first_seen = base_time + timedelta(minutes=vehicle_index * 3)
        vehicle_type = TYPES[vehicle_index % len(TYPES)]
        color = COLORS[(vehicle_index * 3) % len(COLORS)]
        route_length = 3 + vehicle_index % 4
        route, travel_times, unreachable = build_route(vehicle_index, route_length, camera_by_id)
        trajectory_times = [first_seen]
        for travel_time in travel_times:
            trajectory_times.append(trajectory_times[-1] + timedelta(seconds=travel_time))
        end_time = trajectory_times[-1]
        vehicles.append((vehicle_id, plate, vehicle_type, color, first_seen, end_time))

        trajectory_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"trajectory-{vehicle_id}"))
        trajectory_status = "UNREACHABLE" if unreachable else "VALID"
        trajectories.append((trajectory_id, vehicle_id, trajectory_status, first_seen, end_time, 900 + vehicle_index * 17, (end_time - first_seen).total_seconds(), round(0.52 + (vehicle_index % 48) / 100, 2)))

        observation_ids = []
        for sequence, camera in enumerate(route):
            camera_id, latitude, longitude, _, _ = camera
            observed_at = trajectory_times[sequence]
            observation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"observation-{vehicle_id}-{sequence}"))
            observation_ids.append(observation_id)
            plate_confidence = round(0.55 + ((vehicle_index * 7 + sequence * 11) % 45) / 100, 2)
            detection_confidence = round(0.58 + ((vehicle_index * 5 + sequence * 13) % 40) / 100, 2)
            observations.append((observation_id, camera_id, observed_at, f"{vehicle_id}-T{sequence + 1}", plate, plate_confidence, detection_confidence, vehicle_type, color))
            status = "CONFIRMED" if (vehicle_index + sequence) % 3 else "INFERRED"
            path_confidence = round(0.48 + ((vehicle_index * 9 + sequence * 7) % 50) / 100, 2)
            trajectory_observations.append((str(uuid.uuid5(uuid.NAMESPACE_URL, f"trajectory-observation-{vehicle_id}-{sequence}")), trajectory_id, camera_id, observed_at, sequence + 1, status, path_confidence, observation_id))
            identities.append((str(uuid.uuid5(uuid.NAMESPACE_URL, f"identity-{vehicle_id}-{sequence}")), vehicle_id, observation_id, round(0.55 + ((vehicle_index + sequence * 4) % 43) / 100, 2), round(0.50 + ((vehicle_index * 2 + sequence * 5) % 48) / 100, 2)))

        for sequence, (from_camera, to_camera) in enumerate(zip(route, route[1:])):
            from_id, from_lat, from_lon, _, _ = from_camera
            to_id, to_lat, to_lon, _, _ = to_camera
            from_time = trajectory_times[sequence]
            to_time = trajectory_times[sequence + 1]
            transition_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"transition-{vehicle_id}-{sequence}"))
            status = "CONFIRMED" if (vehicle_index + sequence) % 2 else "INFERRED"
            confidence = round(0.50 + ((vehicle_index * 3 + sequence * 17) % 48) / 100, 2)
            transitions.append((transition_id, trajectory_id, from_id, to_id, from_time, to_time, travel_times[sequence], 450 + vehicle_index * 8 + sequence * 35, confidence, status))
            geometry.extend([
                (str(uuid.uuid5(uuid.NAMESPACE_URL, f"geometry-{transition_id}-1")), transition_id, 1, from_lat, from_lon),
                (str(uuid.uuid5(uuid.NAMESPACE_URL, f"geometry-{transition_id}-2")), transition_id, 2, round((from_lat + to_lat) / 2, 6), round((from_lon + to_lon) / 2, 6)),
                (str(uuid.uuid5(uuid.NAMESPACE_URL, f"geometry-{transition_id}-3")), transition_id, 3, to_lat, to_lon),
            ])

        if 20 <= vehicle_index < 32:
            alerts.append((
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"alert-{vehicle_id}")),
                vehicle_id,
                "BLACKLIST_MATCH",
                "HIGH",
                round(0.76 + ((vehicle_index - 20) % 20) / 100, 2),
                "Vehicle matched a watchlist entry",
                route[0][0],
                route[-1][0],
                first_seen,
                end_time,
            ))

    return cameras, vehicles, observations, identities, trajectories, trajectory_observations, transitions, geometry, alerts


def insert(table, columns, rows, transform=lambda row: row):
    lines = [f"INSERT INTO {table} ({', '.join(columns)}) VALUES"]
    lines.append(",\n".join("(" + ", ".join(sql(value) for value in transform(row)) + ")" for row in rows) + ";")
    return "\n".join(lines)


def main():
    cameras, vehicles, observations, identities, trajectories, trajectory_observations, transitions, geometry, alerts = make_rows()
    statements = [
        "-- Deterministic demo dataset: 120 vehicles, 60 cameras, 12 unreachable trajectories, 12 blacklist alerts.",
        "TRUNCATE TABLE trajectory_route_geometry, trajectory_transition, trajectory_observation, intelligence_events, vehicle_identity_links, observation, trajectory, vehicles, camera RESTART IDENTITY CASCADE;",
        insert("camera", ["camera_id", "location", "road_segment", "status", "installed_at"], cameras, lambda row: (row[0], RawSql(f"ST_SetSRID(ST_MakePoint({row[2]}, {row[1]}), 4326)"), row[3], row[4], "2025-11-01T00:00:00Z")),
        insert("vehicles", ["vehicle_id", "plate_text", "vehicle_type", "vehicle_color", "first_seen", "last_seen"], vehicles, lambda row: (row[0], row[1], row[2], row[3], stamp(row[4]), stamp(row[5]))),
        insert("observation", ["observation_id", "camera_id", "timestamp", "local_track_id", "plate_text", "plate_confidence", "detection_confidence", "vehicle_type", "vehicle_color"], observations, lambda row: (row[0], row[1], stamp(row[2]), row[3], row[4], row[5], row[6], row[7], row[8])),
        insert("vehicle_identity_links", ["id", "vehicle_id", "observation_id", "identity_confidence", "appearance_confidence", "supporting_evidence"], identities, lambda row: (row[0], row[1], row[2], row[3], row[4], '{"source":"mock_fusion","match_strategy":"multimodal_fusion"}')),
        insert("trajectory", ["trajectory_id", "vehicle_id", "trajectory_status", "start_time", "end_time", "distance_meters", "duration", "trajectory_confidence"], trajectories, lambda row: (row[0], row[1], row[2], stamp(row[3]), stamp(row[4]), row[5], f"{int(row[6])} seconds", row[7])),
        insert("trajectory_observation", ["trajectory_observation_id", "trajectory_id", "camera_id", "timestamp", "sequence_number", "status", "confidence", "source_observation_id"], trajectory_observations, lambda row: (row[0], row[1], row[2], stamp(row[3]), row[4], row[5], row[6], row[7])),
        insert("trajectory_transition", ["transition_id", "trajectory_id", "from_camera_id", "to_camera_id", "from_timestamp", "to_timestamp", "travel_time_sec", "distance_meters", "confidence", "status"], transitions, lambda row: (row[0], row[1], row[2], row[3], stamp(row[4]), stamp(row[5]), row[6], row[7], row[8], row[9])),
        insert("trajectory_route_geometry", ["id", "transition_id", "sequence_number", "latitude", "longitude"], geometry),
        insert("intelligence_events", ["event_id", "vehicle_id", "event_type", "severity", "confidence", "reason", "camera_range", "time_range_start", "time_range_end"], alerts, lambda row: (row[0], row[1], row[2], row[3], row[4], row[5], RawSql(f"ARRAY[{sql(row[6])}, {sql(row[7])}]"), stamp(row[8]), stamp(row[9]))),
    ]
    OUTPUT.write_text("\n\n".join(statements) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT} with 120 vehicles, 60 cameras, {len(observations)} observations, {len(transitions)} transitions, and {len(alerts)} alerts.")


if __name__ == "__main__":
    main()