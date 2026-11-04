import type { Alert, Camera, LiveDetection, Trajectory, Vehicle } from '../types';
import { assessSyntheticTransition } from './constraintGraph';

interface RawObservation {
  observation_id?: number | string;
  camera_id: string;
  timestamp: number;
  global_vehicle_id?: string;
  local_track_id?: string;
  plate_text?: string;
  plate_confidence?: number;
  detection_confidence?: number;
  vehicle_type?: string;
  vehicle_color?: string;
}

interface CameraFile {
  camera_id: string;
  observations?: RawObservation[];
  frames?: Array<{ timestamp: number; vehicles: RawObservation[] }>;
}

export interface SyntheticDataset {
  cameras: Camera[];
  vehicles: Vehicle[];
  alerts: Alert[];
  trajectories: Record<string, Trajectory[]>;
  feed: Array<LiveDetection & { simulationSeconds: number }>;
}

const cameraRoads: Record<string, string> = {
  CAM_01: 'Synthetic north gate',
  CAM_02: 'Synthetic east gate',
  CAM_03: 'Synthetic central east',
  CAM_04: 'Synthetic central',
  CAM_05: 'Synthetic southwest',
  CAM_06: 'Synthetic south central',
  CAM_07: 'Synthetic south east',
  CAM_08: 'Synthetic east loop',
  CAM_09: 'Synthetic east terminal',
  CAM_10: 'Synthetic south loop',
  CAM_11: 'Synthetic south gate',
  CAM_12: 'Synthetic southwest gate',
};

const cameraFiles = Array.from({ length: 12 }, (_, index) =>
  `/synthetic-json/CAM_${String(index + 1).padStart(2, '0')}_observations.json`,
);

function isoTime(seconds: number) {
  return new Date(Date.UTC(2026, 8, 5, 9, 0, 0) + seconds * 1000).toISOString();
}

function confidence(observation: RawObservation) {
  return Math.max(0, Math.min(1, ((observation.detection_confidence ?? 1) + (observation.plate_confidence ?? 1)) / 2));
}

function normalizePlate(value: string | undefined) {
  return value?.trim().toUpperCase().replace(/[^A-Z0-9]/g, '') ?? '';
}

function vehicleKey(observation: RawObservation) {
  if (observation.global_vehicle_id) return `SYN_${observation.global_vehicle_id}`;
  const plate = normalizePlate(observation.plate_text);
  return plate
    ? `SYN_${plate}`
    : `SYN_${observation.camera_id.trim().toUpperCase()}_${String(observation.local_track_id ?? observation.observation_id).trim()}`;
}

export async function getSyntheticDataset(): Promise<SyntheticDataset> {
  const files = await Promise.all(
    cameraFiles.map((path) => fetch(path).then((response) => {
      if (!response.ok) throw new Error(`Could not load synthetic data: ${path}`);
      return response.json() as Promise<CameraFile>;
    })),
  );

  const observations = files.flatMap((file) => {
    if (file.observations) return file.observations;
    return (file.frames ?? []).flatMap((frame) => frame.vehicles.map((vehicle) => ({
      ...vehicle,
      camera_id: file.camera_id,
      timestamp: frame.timestamp,
    })));
  });
  const cameras: Camera[] = files.map((file) => ({
    camera_id: file.camera_id,
    latitude: 0,
    longitude: 0,
    road_segment: cameraRoads[file.camera_id] ?? 'Synthetic road',
    status: 'active',
    installed_at: '2026-01-01T00:00:00Z',
  }));

  const grouped = new Map<string, RawObservation[]>();
  for (const observation of observations) {
    const key = vehicleKey(observation);
    const current = grouped.get(key) ?? [];
    current.push(observation);
    grouped.set(key, current);
  }

  const vehicles: Vehicle[] = [];
  const trajectories: Record<string, Trajectory[]> = {};
  const alerts: Alert[] = [];
  const feed: Array<LiveDetection & { simulationSeconds: number }> = [];

  for (const [vehicleId, sightings] of grouped) {
    sightings.sort((a, b) => a.timestamp - b.timestamp);
    const first = sightings[0];
    const last = sightings[sightings.length - 1];
    const route = Array.from(new Map(sightings.map((observation) => [observation.camera_id, observation])).values());
    const plate = normalizePlate(first.plate_text) || 'UNREAD-' + vehicleId.slice(-8);
    vehicles.push({
      vehicle_id: vehicleId,
      plate_text: plate,
      vehicle_type: first.vehicle_type || 'unknown',
      vehicle_color: first.vehicle_color || 'unknown',
      first_seen: isoTime(first.timestamp),
      last_seen: isoTime(last.timestamp),
      last_seen_camera: last.camera_id,
      cameras_seen: [...new Set(sightings.map((sighting) => sighting.camera_id))].sort(),
    });

    const observationsForTrajectory = route.map((observation, sequence_number) => ({
      camera_id: observation.camera_id,
      timestamp: isoTime(observation.timestamp),
      sequence_number: sequence_number + 1,
      status: normalizePlate(observation.plate_text) ? 'CONFIRMED' : 'INFERRED',
      confidence: confidence(observation),
    }));
    const transitions = route.slice(1).map((observation, index) => {
      const previous = route[index];
      const travelTimeSec = Math.max(1, Math.round(observation.timestamp - previous.timestamp));
      const constraint = assessSyntheticTransition(previous.camera_id, observation.camera_id, travelTimeSec);
      return {
        from_camera_id: previous.camera_id,
        to_camera_id: observation.camera_id,
        travel_time_sec: travelTimeSec,
        distance_meters: constraint.distanceMeters ?? 0,
        confidence: confidence(observation),
        status: constraint.status === 'VALID' || constraint.status === 'UNASSESSED'
          ? normalizePlate(observation.plate_text) ? 'CONFIRMED' : 'INFERRED'
          : constraint.status === 'RECOVERED' ? 'INFERRED' : constraint.status,
        constraint_status: constraint.status,
        constraint_path: constraint.path,
        min_travel_time_sec: constraint.minTravelTimeSec,
        max_travel_time_sec: constraint.maxTravelTimeSec,
      };
    });
    const suspiciousTransition = transitions.find((transition) =>
      transition.constraint_status === 'INVALID_TIME' || transition.constraint_status === 'UNREACHABLE',
    );
    const trajectoryStatus = suspiciousTransition?.constraint_status === 'UNREACHABLE'
      ? 'UNREACHABLE'
      : suspiciousTransition ? 'INVALID_TIME'
      : transitions.some((transition) => transition.constraint_status === 'RECOVERED') ? 'RECOVERED'
      : 'VALID';
    const trajectory: Trajectory = {
      trajectory_id: `SYN_TRAJ_${vehicleId}`,
      vehicle_id: vehicleId,
      trajectory_status: trajectoryStatus,
      start_time: isoTime(first.timestamp),
      end_time: isoTime(last.timestamp),
      distance_meters: transitions.reduce((sum, transition) => sum + transition.distance_meters, 0),
      duration: Math.max(0, last.timestamp - first.timestamp),
      trajectory_confidence: sightings.reduce((sum, item) => sum + confidence(item), 0) / sightings.length,
      observations: observationsForTrajectory,
      transitions,
    };
    trajectories[vehicleId] = [trajectory];

    if (suspiciousTransition) {
      const unreachable = suspiciousTransition.constraint_status === 'UNREACHABLE';
      const min = suspiciousTransition.min_travel_time_sec;
      const max = suspiciousTransition.max_travel_time_sec;
      alerts.push({
        event_id: `SYN_PATH_ALERT_${vehicleId}`,
        vehicle_id: vehicleId,
        event_type: unreachable ? 'ROUTE_ANOMALY' : 'TRAVEL_TIME_ANOMALY',
        severity: unreachable ? 'HIGH' : 'MEDIUM',
        confidence: suspiciousTransition.confidence,
        reason: unreachable
          ? `No feasible route between ${suspiciousTransition.from_camera_id} and ${suspiciousTransition.to_camera_id} exists in the camera constraint graph.`
          : `Observed travel time of ${suspiciousTransition.travel_time_sec}s is outside the graph bounds${min !== undefined && max !== undefined ? ` (${min}-${max}s)` : ''} for ${suspiciousTransition.from_camera_id} to ${suspiciousTransition.to_camera_id}.`,
        camera_range: [suspiciousTransition.from_camera_id, suspiciousTransition.to_camera_id],
        time_range_start: isoTime(first.timestamp),
        time_range_end: isoTime(last.timestamp),
        created_at: isoTime(last.timestamp),
      });
    }

    const weakest = sightings.reduce((weak, item) => confidence(item) < confidence(weak) ? item : weak, first);
    if (confidence(weakest) < 0.45 || !normalizePlate(weakest.plate_text)) {
      alerts.push({
        event_id: `SYN_ALERT_${vehicleId}`,
        vehicle_id: vehicleId,
        event_type: normalizePlate(weakest.plate_text) ? 'LOW_CONFIDENCE_DETECTION' : 'PLATE_NOT_READ',
        severity: confidence(weakest) < 0.3 ? 'HIGH' : 'MEDIUM',
        confidence: confidence(weakest),
        reason: normalizePlate(weakest.plate_text) ? 'Synthetic detection confidence is below the operational threshold.' : 'Synthetic observation has no readable plate text.',
        camera_range: [weakest.camera_id],
        time_range_start: isoTime(weakest.timestamp),
        time_range_end: isoTime(weakest.timestamp),
        created_at: isoTime(weakest.timestamp),
      });
    }
  }

  for (const observation of observations) {
    feed.push({
      event: 'observation',
      observation_id: String(observation.observation_id),
      camera_id: observation.camera_id,
      timestamp: isoTime(observation.timestamp),
      plate_text: normalizePlate(observation.plate_text) || 'PLATE_UNREAD',
      vehicle_type: observation.vehicle_type || 'unknown',
      vehicle_color: observation.vehicle_color || 'unknown',
      simulationSeconds: observation.timestamp,
      _key: `synthetic-${observation.camera_id}-${observation.observation_id}`,
    });
  }

  feed.sort((a, b) => a.simulationSeconds - b.simulationSeconds || a.camera_id.localeCompare(b.camera_id));
  return { cameras, vehicles, alerts, trajectories, feed };
}
