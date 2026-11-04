import mapImage from "../assets/map.png";
import { Video } from "lucide-react";
import type { Alert, Camera, Trajectory } from "../types";

type SyntheticCamera = Camera & { x: number; y: number };

const SYNTHETIC_CAMERA_SPECS: Array<[string, string, number, number]> = [
  ["CAM_01", "Synthetic north gate", 36.8, 10.7],
  ["CAM_02", "Synthetic east gate", 48.0, 10.7],
  ["CAM_03", "Synthetic central east", 40.4, 19.3],
  ["CAM_04", "Synthetic central", 40.4, 38.1],
  ["CAM_05", "Synthetic southwest", 34.4, 54.9],
  ["CAM_06", "Synthetic south central", 45.0, 54.9],
  ["CAM_07", "Synthetic south east", 65.3, 54.9],
  ["CAM_08", "Synthetic east loop", 78.1, 54.9],
  ["CAM_09", "Synthetic east terminal", 83.8, 42.4],
  ["CAM_10", "Synthetic south loop", 84.0, 65.1],
  ["CAM_11", "Synthetic south gate", 39.7, 92.4],
  ["CAM_12", "Synthetic southwest gate", 56.5, 92.4],
];

export const SYNTHETIC_CAMERAS: SyntheticCamera[] = SYNTHETIC_CAMERA_SPECS.map(([camera_id, road_segment, x, y]) => ({
  camera_id,
  latitude: 0,
  longitude: 0,
  road_segment,
  status: "active",
  installed_at: "2026-01-01T00:00:00Z",
  x,
  y,
}));

const cameraById = new Map(SYNTHETIC_CAMERAS.map((camera) => [camera.camera_id, camera]));
function roadPath(from: SyntheticCamera, to: SyntheticCamera) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  // Follow the synthetic map's horizontal/vertical road corridors. The
  // corner is geometry only; it is never treated as an observed camera.
  if (Math.abs(dx) >= Math.abs(dy)) {
    const cornerX = to.x;
    const cornerY = from.y;
    return `M ${from.x} ${from.y} L ${cornerX} ${cornerY} L ${to.x} ${to.y}`;
  }
  const cornerX = from.x;
  const cornerY = to.y;
  return `M ${from.x} ${from.y} L ${cornerX} ${cornerY} L ${to.x} ${to.y}`;
}

function routePaths(trajectories: Trajectory[]) {
  const paths: string[] = [];
  for (const trajectory of trajectories) {
    for (const transition of trajectory.transitions) {
      const constraintPath = transition.constraint_path?.map((cameraId) => {
        const normalizedId = cameraId.startsWith('C') ? `CAM_${cameraId.slice(1)}` : cameraId;
        return cameraById.get(normalizedId);
      });
      const points = constraintPath?.length && constraintPath.every(Boolean)
        ? constraintPath.filter((camera): camera is SyntheticCamera => camera !== undefined)
        : [
            cameraById.get(transition.from_camera_id),
            cameraById.get(transition.to_camera_id),
          ].filter((camera): camera is SyntheticCamera => camera !== undefined);
      for (let index = 1; index < points.length; index += 1) {
        if (points[index - 1].camera_id !== points[index].camera_id) {
          paths.push(roadPath(points[index - 1], points[index]));
        }
      }
    }
  }
  return paths;
}

export function SyntheticMap({
  alerts = [],
  trajectories = [],
  selectedVehicleId,
  focusedCameraId,
}: {
  alerts?: Alert[];
  trajectories?: Trajectory[];
  selectedVehicleId?: string;
  focusedCameraId?: string;
}) {
  const alertCameraIds = new Set(alerts.flatMap((alert) => alert.camera_range ?? []));
  const routePathsForVehicle = selectedVehicleId ? routePaths(trajectories) : [];
  const focusedCamera = focusedCameraId ? cameraById.get(focusedCameraId) : undefined;

  return (
    <div className="relative w-full h-full bg-slate-900 overflow-hidden flex flex-col">
      <div className="absolute inset-0 bg-slate-900">
        <img src={mapImage} alt="CARLA synthetic road network" className="w-full h-full object-fill" />
      </div>
      {routePathsForVehicle.length > 0 && (
        <svg className="absolute inset-0 h-full w-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Selected vehicle route">
          <defs>
            <marker id="synthetic-route-arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
              <path d="M 0 0 L 5 2.5 L 0 5 z" fill="#e8b83f" />
            </marker>
          </defs>
          {routePathsForVehicle.map((path, index) => (
            <path key={`${path}-${index}`} d={path} fill="none" stroke="#071827" strokeWidth="1.35" strokeLinecap="round" />
          ))}
          {routePathsForVehicle.map((path, index) => (
            <path key={`route-${path}-${index}`} d={path} fill="none" stroke="#e8b83f" strokeWidth="0.65" strokeLinecap="round" strokeDasharray="2.2 1.4" markerMid="url(#synthetic-route-arrow)" />
          ))}
        </svg>
      )}
      <div className="absolute inset-0 pointer-events-none">
        {SYNTHETIC_CAMERAS.map((camera) => (
          <div
            key={camera.camera_id}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${camera.x}%`, top: `${camera.y}%` }}
            title={camera.camera_id}
          >
            <div className="relative flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-accent text-ink shadow-lg">
              <Video size={13} strokeWidth={2.5} />
              {alertCameraIds.has(camera.camera_id) && (
                <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-severity-high ring-2 ring-white" />
              )}
            </div>
            <span className="absolute left-1/2 top-8 -translate-x-1/2 whitespace-nowrap rounded bg-ink/80 px-1.5 py-0.5 text-[9px] font-mono font-bold text-white">
              {camera.camera_id}
            </span>
          </div>
        ))}
        {focusedCamera && (
          <div
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-ink bg-accent shadow-[0_0_0_6px_rgba(232,184,63,0.28)] animate-pulse"
            style={{ left: `${focusedCamera.x}%`, top: `${focusedCamera.y}%`, width: 22, height: 22 }}
            title={`${selectedVehicleId ?? "Vehicle"} current position`}
          />
        )}
      </div>
    </div>
  );
}


