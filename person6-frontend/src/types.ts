export type CameraStatus = 'active' | 'offline';

export interface Camera {
  camera_id: string;
  latitude: number;
  longitude: number;
  road_segment: string;
  status: CameraStatus;
  installed_at: string;
}

export interface Vehicle {
  vehicle_id: string;
  plate_text: string;
  vehicle_type: string;
  vehicle_color: string;
  first_seen: string;
  last_seen: string;
}

export type SegmentStatus = 'CONFIRMED' | 'INFERRED' | string;

export interface RoutePoint {
  lat: number;
  lon: number;
}

export interface Observation {
  camera_id: string;
  timestamp: string;
  sequence_number: number;
  status: string;
  confidence: number;
}

export interface Transition {
  from_camera_id: string;
  to_camera_id: string;
  travel_time_sec: number;
  distance_meters: number;
  confidence: number;
  status: SegmentStatus;
  route_geometry: RoutePoint[];
}

export interface Trajectory {
  trajectory_id: string;
  vehicle_id: string;
  trajectory_status: string;
  start_time: string;
  end_time: string;
  distance_meters: number;
  duration: number;
  trajectory_confidence: number;
  observations: Observation[];
  transitions: Transition[];
}

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | string;

export interface Alert {
  event_id: string;
  vehicle_id: string;
  event_type: string;
  severity: AlertSeverity;
  confidence: number;
  reason: string;
  camera_range: string[];
  time_range_start: string;
  time_range_end: string;
  created_at: string;
}

export interface LiveDetection {
  event: string;
  observation_id: string;
  camera_id: string;
  timestamp: string;
  plate_text: string;
  vehicle_type: string;
  vehicle_color: string;
  /** client-assigned, for React keys + animation */
  _receivedAt?: number;
  _key?: string;
}

export type FetchState = 'idle' | 'loading' | 'success' | 'error';

/** The seven modules an operator can open into the Command Deck workspace. */
export type PaneKey = 'vehicles' | 'cameras' | 'alerts' | 'analytics' | 'feed' | 'map' | 'trajectory';
