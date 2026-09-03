import type { Alert, Camera, Trajectory, Vehicle } from '../types';

export const API_BASE = 'http://127.0.0.1:8000';
export const WS_URL = 'ws://127.0.0.1:8000/ws/live';

class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function getJson<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new ApiError(
      `Could not reach the vehicle intelligence backend at ${API_BASE}. Is the API running?`,
    );
  }
  if (!res.ok) {
    throw new ApiError(`Request to ${path} failed (${res.status})`, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCameras: () => getJson<Camera[]>('/cameras'),
  getVehicles: () => getJson<Vehicle[]>('/vehicles'),
  getTrajectories: (vehicleId: string) =>
    getJson<Trajectory[]>(`/trajectories/${encodeURIComponent(vehicleId)}`),
  getAlerts: () => getJson<Alert[]>('/alerts'),
};

export { ApiError };
