import { useEffect, useMemo, useState } from 'react';
import { api } from './api/client';
import { useApiResource } from './hooks/useApiResource';
import { useLiveFeed } from './hooks/useLiveFeed';
import { TopBar } from './components/TopBar';
import { Dock, type DockModule } from './components/Dock';
import { Workspace, type WorkspacePane } from './components/Workspace';
import { StatusBar } from './components/StatusBar';
import { VehicleTable } from './components/VehicleTable';
import { CameraTable } from './components/CameraTable';
import { AlertsPanel } from './components/AlertsPanel';
import { AnalyticsPanel } from './components/AnalyticsPanel';
import { FilterBar, withinRange, type FilterState } from './components/FilterBar';
import { LiveFeedPanel } from './components/LiveFeedPanel';
import { MapView } from './components/MapView';
import { MapLegend } from './components/MapLegend';
import { TrajectoryPanel } from './components/TrajectoryPanel';
import { LoadingState } from './components/StatusStates';
import {
  AlertsIcon,
  AnalyticsIcon,
  CamerasIcon,
  FeedIcon,
  MapIcon,
  TrajectoryIcon,
  VehiclesIcon,
} from './lib/icons';
import type { Alert, Camera, PaneKey } from './types';

const KEY_TO_PANE: Record<string, PaneKey> = {
  '1': 'vehicles',
  '2': 'alerts',
  '3': 'map',
  '4': 'feed',
  '5': 'cameras',
  '6': 'analytics',
  '7': 'trajectory',
};

export default function App() {
  const cameras = useApiResource(api.getCameras, [], { pollMs: 20000 });
  const vehicles = useApiResource(api.getVehicles, [], { pollMs: 20000 });
  const alerts = useApiResource(api.getAlerts, [], { pollMs: 20000 });
  const { entries: liveEntries, status: wsStatus } = useLiveFeed();

  // The workspace — which dashboards the operator currently has open, and in
  // what order. Opening the same key twice is a no-op; togglePane closes it.
  const [openPanes, setOpenPanes] = useState<PaneKey[]>(['map', 'vehicles']);

  const [selectedVehicleId, setSelectedVehicleId] = useState<string>();
  const [selectedAlertId, setSelectedAlertId] = useState<string>();
  const [alertCameraRange, setAlertCameraRange] = useState<string[]>([]);
  const [flyToCameraId, setFlyToCameraId] = useState<string>();
  const [filters, setFilters] = useState<FilterState>({});

  const trajectories = useApiResource(
    () => api.getTrajectories(selectedVehicleId as string),
    [selectedVehicleId],
    { enabled: !!selectedVehicleId },
  );

  // Trajectory data for whichever vehicle is *actually* selected right now.
  // useApiResource doesn't clear `data` while a new fetch is in flight, so
  // for one render after switching vehicles, trajectories.data can still be
  // the previous vehicle's route. Every consumer (map route line, focused
  // camera marker, trajectory pane) reads this derived value instead of the
  // raw resource so none of them ever show one vehicle's trajectory under
  // another vehicle's header/pin.
  const visibleTrajectories = useMemo(() => {
    const trajs = trajectories.data;
    if (!trajs || !selectedVehicleId) return undefined;
    if (trajs.some((t) => t.vehicle_id !== selectedVehicleId)) return undefined;
    return trajs;
  }, [trajectories.data, selectedVehicleId]);

  const selectedVehicle = useMemo(
    () => vehicles.data?.find((v) => v.vehicle_id === selectedVehicleId),
    [vehicles.data, selectedVehicleId],
  );

  // The camera of the selected vehicle's single most recent observation
  // across every returned trajectory — drives the larger pulsing "current
  // position" marker on the map, separate from the amber alert/filter glow.
  const focusedCameraId = useMemo(() => {
    if (!visibleTrajectories || visibleTrajectories.length === 0) return undefined;
    let best: { time: number; cameraId: string } | undefined;
    for (const traj of visibleTrajectories) {
      for (const o of traj.observations) {
        const t = Date.parse(o.timestamp);
        if (!best || t > best.time) best = { time: t, cameraId: o.camera_id };
      }
    }
    return best?.cameraId;
  }, [visibleTrajectories]);

  const highlightedCameraIds = useMemo(() => {
    const set = new Set<string>(alertCameraRange);
    if (filters.cameraId) set.add(filters.cameraId);
    return Array.from(set);
  }, [alertCameraRange, filters.cameraId]);

  const filteredVehicles = useMemo(() => {
    if (!vehicles.data) return vehicles.data;
    if (!filters.dateFrom && !filters.dateTo) return vehicles.data;
    return vehicles.data.filter((v) => withinRange(v.last_seen, filters.dateFrom, filters.dateTo));
  }, [vehicles.data, filters.dateFrom, filters.dateTo]);

  const filteredAlerts = useMemo(() => {
    if (!alerts.data) return alerts.data;
    return alerts.data.filter((a) => {
      if (!withinRange(a.created_at, filters.dateFrom, filters.dateTo)) return false;
      if (filters.cameraId && !(a.camera_range ?? []).includes(filters.cameraId)) return false;
      return true;
    });
  }, [alerts.data, filters.dateFrom, filters.dateTo, filters.cameraId]);

  const togglePane = (key: PaneKey) => {
    setOpenPanes((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  };
  const openPane = (key: PaneKey) => {
    setOpenPanes((prev) => (prev.includes(key) ? prev : [...prev, key]));
  };
  const closePane = (key: PaneKey) => {
    setOpenPanes((prev) => prev.filter((k) => k !== key));
  };

  // Keyboard shortcuts: 1-7 toggle a module, Esc closes the most recently
  // opened pane — the same hotbar/tmux-window vocabulary as the dock's own
  // key badges. Ignored while typing into an input so search/filter fields
  // keep working normally.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const tag = (document.activeElement as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const key = KEY_TO_PANE[e.key];
      if (key) {
        togglePane(key);
        return;
      }
      if (e.key === 'Escape') {
        setOpenPanes((prev) => (prev.length ? prev.slice(0, -1) : prev));
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleSelectVehicle = (vehicleId: string) => {
    setSelectedVehicleId(vehicleId);
    setSelectedAlertId(undefined);
    setAlertCameraRange([]);
    openPane('trajectory');
  };

  const handleSelectAlert = (alert: Alert) => {
    setSelectedAlertId(alert.event_id);
    setSelectedVehicleId(alert.vehicle_id);
    setAlertCameraRange(alert.camera_range ?? []);
    openPane('trajectory');
  };

  const handleSelectCamera = (camera: Camera) => {
    setFilters((f) => ({ ...f, cameraId: camera.camera_id }));
    setFlyToCameraId(camera.camera_id);
    openPane('map');
  };

  const handleFilterChange = (patch: Partial<FilterState>) => {
    setFilters((f) => ({ ...f, ...patch }));
    if (patch.cameraId) setFlyToCameraId(patch.cameraId);
  };

  const handleClearFilters = () => setFilters({});

  const initialLoading =
    cameras.state === 'loading' && !cameras.data && vehicles.state === 'loading' && !vehicles.data;

  if (initialLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-ink">
        <LoadingState label="Connecting to camera network…" />
      </div>
    );
  }

  const activeCameraCount = cameras.data?.filter((c) => c.status === 'active').length ?? 0;

  const modules: DockModule[] = [
    {
      key: 'vehicles',
      keyNum: '1',
      label: 'Vehicles',
      hint: `${vehicles.data?.length ?? 0} tracked`,
      icon: <VehiclesIcon />,
    },
    {
      key: 'alerts',
      keyNum: '2',
      label: 'Alerts',
      hint: `${filteredAlerts?.length ?? 0} open`,
      icon: <AlertsIcon />,
      badge: filteredAlerts?.length || undefined,
    },
    { key: 'map', keyNum: '3', label: 'Live Map', hint: 'City grid', icon: <MapIcon /> },
    {
      key: 'feed',
      keyNum: '4',
      label: 'Live Feed',
      hint: wsStatus === 'open' ? 'streaming' : wsStatus,
      icon: <FeedIcon />,
    },
    {
      key: 'cameras',
      keyNum: '5',
      label: 'Cameras',
      hint: `${activeCameraCount}/${cameras.data?.length ?? 0} online`,
      icon: <CamerasIcon />,
    },
    { key: 'analytics', keyNum: '6', label: 'Analytics', hint: 'summary', icon: <AnalyticsIcon /> },
    {
      key: 'trajectory',
      keyNum: '7',
      label: 'Trajectory',
      hint: selectedVehicle ? selectedVehicle.plate_text : 'select a vehicle',
      icon: <TrajectoryIcon />,
      disabled: !selectedVehicle,
    },
  ];

  const paneFor = (key: PaneKey): WorkspacePane => {
    switch (key) {
      case 'vehicles':
        return {
          key,
          title: 'Vehicles',
          status: `${filteredVehicles?.length ?? 0} results`,
          icon: <VehiclesIcon />,
          content: (
            <VehicleTable
              vehicles={filteredVehicles}
              state={vehicles.state}
              error={vehicles.error}
              onReload={vehicles.reload}
              selectedVehicleId={selectedVehicleId}
              onSelectVehicle={handleSelectVehicle}
              lastUpdatedAt={vehicles.lastUpdatedAt}
            />
          ),
        };
      case 'cameras':
        return {
          key,
          title: 'Cameras',
          status: `${activeCameraCount}/${cameras.data?.length ?? 0} online`,
          icon: <CamerasIcon />,
          content: (
            <CameraTable
              cameras={cameras.data}
              state={cameras.state}
              error={cameras.error}
              onReload={cameras.reload}
              selectedCameraId={filters.cameraId}
              onSelectCamera={handleSelectCamera}
              lastUpdatedAt={cameras.lastUpdatedAt}
            />
          ),
        };
      case 'alerts':
        return {
          key,
          title: 'Alerts',
          status: `${filteredAlerts?.length ?? 0} open`,
          icon: <AlertsIcon />,
          content: (
            <AlertsPanel
              alerts={filteredAlerts}
              state={alerts.state}
              error={alerts.error}
              onReload={alerts.reload}
              onSelectAlert={handleSelectAlert}
              selectedAlertId={selectedAlertId}
            />
          ),
        };
      case 'analytics':
        return {
          key,
          title: 'Analytics',
          status: 'summary',
          icon: <AnalyticsIcon />,
          content: <AnalyticsPanel vehicles={vehicles.data} cameras={cameras.data} alerts={alerts.data} />,
        };
      case 'feed':
        return {
          key,
          title: 'Live Feed',
          status: `${liveEntries.length}/20`,
          icon: <FeedIcon />,
          content: <LiveFeedPanel entries={liveEntries} status={wsStatus} />,
        };
      case 'map':
        return {
          key,
          title: 'Live Map',
          status: cameras.state === 'error' && !cameras.data ? 'offline' : 'sweeping',
          icon: <MapIcon />,
          content:
            cameras.state === 'error' && !cameras.data ? (
              <div className="absolute inset-0 flex items-center justify-center bg-ink px-6 text-center">
                <div className="max-w-sm space-y-3">
                  <p className="text-sm text-fg-muted">{cameras.error}</p>
                  <button
                    onClick={cameras.reload}
                    className="text-xs font-semibold text-accent hover:text-fg border border-steel hover:border-accent/60 rounded-md px-3 py-1.5 transition-colors"
                  >
                    Retry connection
                  </button>
                </div>
              </div>
            ) : (
              <>
                <MapView
                  cameras={cameras.data ?? []}
                  trajectories={visibleTrajectories ?? []}
                  selectedVehicleId={selectedVehicleId}
                  highlightedCameraIds={highlightedCameraIds}
                  focusedCameraId={focusedCameraId}
                  flyToCameraId={flyToCameraId}
                  onSelectCamera={handleSelectCamera}
                />
                <MapLegend />
              </>
            ),
        };
      case 'trajectory':
        return {
          key,
          title: 'Trajectory',
          status: selectedVehicle?.plate_text ?? '—',
          icon: <TrajectoryIcon />,
          content: (
            <TrajectoryPanel
              vehicle={selectedVehicle}
              trajectories={visibleTrajectories}
              state={trajectories.state}
              error={trajectories.error}
              onReload={trajectories.reload}
            />
          ),
        };
    }
  };

  const panes = openPanes.map(paneFor);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <TopBar vehicles={vehicles.data ?? []} onSelectVehicle={handleSelectVehicle} wsStatus={wsStatus} />

      <div className="flex flex-1 min-h-0 flex-col md:flex-row">
        <aside className="flex flex-col shrink-0 w-full md:w-[240px] max-h-[38vh] md:max-h-none m-3 md:mr-0 rounded-2xl glass-panel overflow-hidden animate-panel-in">
          <FilterBar
            cameras={cameras.data ?? []}
            filters={filters}
            onChange={handleFilterChange}
            onClear={handleClearFilters}
          />
          <Dock modules={modules} open={new Set(openPanes)} onToggle={togglePane} />
        </aside>

        <div className="flex flex-col flex-1 min-w-0 min-h-0">
          <Workspace panes={panes} onClose={closePane} />
          <StatusBar paneCount={panes.length} />
        </div>
      </div>
    </div>
  );
}
