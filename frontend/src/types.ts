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
  last_seen_camera?: string;
  cameras_seen?: string[];
}

export type SegmentStatus = 'CONFIRMED' | 'INFERRED' | string;

export interface RoutePoint {
  lat: number;
  lon: number;
}

export interface RouteGeometrySegment {
  from_camera_id: string;
  to_camera_id: string;
  points: RoutePoint[];
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
  constraint_status?: 'VALID' | 'RECOVERED' | 'INVALID_TIME' | 'UNREACHABLE' | 'UNASSESSED';
  constraint_path?: string[];
  min_travel_time_sec?: number;
  max_travel_time_sec?: number;
  // NOTE: route_geometry moved to top-level Trajectory to match backend API schema.
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
  route_geometry?: RouteGeometrySegment[];
}

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | string;

export type DatasetMode = 'live' | 'synthetic';

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
  _receivedAt?: number;
  _key?: string;
}

export type FetchState = 'idle' | 'loading' | 'success' | 'error';

export type PaneKey = 'vehicles' | 'cameras' | 'alerts' | 'analytics' | 'feed' | 'map' | 'trajectory'
  ;
