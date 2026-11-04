import cameraGraph from '../../../docs/contracts/camera_graph.json';

interface CameraEdge {
  from_camera: string;
  to_camera: string;
  distance_meters: number;
  min_travel_time_sec: number;
  avg_travel_time_sec: number;
  max_travel_time_sec: number;
}

interface CameraGraph {
  edges: CameraEdge[];
}

export type ConstraintStatus = 'VALID' | 'RECOVERED' | 'INVALID_TIME' | 'UNREACHABLE' | 'UNASSESSED';

export interface TransitionConstraint {
  status: ConstraintStatus;
  path: string[];
  minTravelTimeSec?: number;
  maxTravelTimeSec?: number;
  distanceMeters?: number;
}

interface ConstraintRoute {
  path: string[];
  min: number;
  average: number;
  max: number;
  distance: number;
}

const graph: CameraGraph = cameraGraph;
const edges = new Map<string, CameraEdge[]>();
const cameras = new Set<string>();
const routeCache = new Map<string, ConstraintRoute[]>();

for (const edge of graph.edges) {
  const outgoing = edges.get(edge.from_camera) ?? [];
  outgoing.push(edge);
  edges.set(edge.from_camera, outgoing);
  cameras.add(edge.from_camera);
  cameras.add(edge.to_camera);
}

function normalizeCameraId(cameraId: string) {
  return cameraId.replace(/^CAM_/, 'C');
}

export function assessTransition(
  fromCameraId: string,
  toCameraId: string,
  travelTimeSec: number,
): TransitionConstraint {
  const source = normalizeCameraId(fromCameraId);
  const target = normalizeCameraId(toCameraId);
  if (source === target) return { status: 'UNASSESSED', path: [] };
  if (!cameras.has(source) || !cameras.has(target)) {
    return { status: 'UNASSESSED', path: [] };
  }
  const routeKey = `${source}:${target}`;
  let routes = routeCache.get(routeKey);
  if (!routes) {
    const computedRoutes: ConstraintRoute[] = [];
    const visit = (
      cameraId: string,
      path: string[],
      min: number,
      average: number,
      max: number,
      distance: number,
    ) => {
      if (cameraId === target) {
        computedRoutes.push({ path, min, average, max, distance });
        return;
      }
      if (path.length > 6) return;
      for (const edge of edges.get(cameraId) ?? []) {
        if (path.includes(edge.to_camera)) continue;
        visit(
          edge.to_camera,
          [...path, edge.to_camera],
          min + edge.min_travel_time_sec,
          average + edge.avg_travel_time_sec,
          max + edge.max_travel_time_sec,
          distance + edge.distance_meters,
        );
      }
    };
    visit(source, [source], 0, 0, 0, 0);
    routes = computedRoutes;
    routeCache.set(routeKey, routes);
  }
  if (routes.length === 0) return { status: 'UNREACHABLE', path: [] };

  const feasible = routes
    .filter((route) => route.min <= travelTimeSec && travelTimeSec <= route.max)
    .sort((a, b) => Math.abs(a.average - travelTimeSec) - Math.abs(b.average - travelTimeSec))[0];

  if (feasible) {
    return {
      status: feasible.path.length === 2 ? 'VALID' : 'RECOVERED',
      path: feasible.path,
      minTravelTimeSec: feasible.min,
      maxTravelTimeSec: feasible.max,
      distanceMeters: feasible.distance,
    };
  }

  const nearest = routes.sort((a, b) => {
    const distanceA = travelTimeSec < a.min ? a.min - travelTimeSec : travelTimeSec - a.max;
    const distanceB = travelTimeSec < b.min ? b.min - travelTimeSec : travelTimeSec - b.max;
    return distanceA - distanceB;
  })[0];

  return {
    status: 'INVALID_TIME',
    path: nearest.path,
    minTravelTimeSec: nearest.min,
    maxTravelTimeSec: nearest.max,
    distanceMeters: nearest.distance,
  };
}

const SYNTHETIC_CAMERA_IDS = new Set(
  Array.from({ length: 12 }, (_, index) => `C${String(index + 1).padStart(2, '0')}`),
);

export function assessSyntheticTransition(
  fromCameraId: string,
  toCameraId: string,
  _travelTimeSec: number,
): TransitionConstraint {
  const source = normalizeCameraId(fromCameraId);
  const target = normalizeCameraId(toCameraId);
  if (
    source === target
    || !SYNTHETIC_CAMERA_IDS.has(source)
    || !SYNTHETIC_CAMERA_IDS.has(target)
  ) {
    return { status: 'UNASSESSED', path: [] };
  }

  return {
    status: 'VALID',
    path: [source, target],
    minTravelTimeSec: 0,
    maxTravelTimeSec: 100 * 60,
  };
}
