import { useEffect, useMemo, useState } from 'react';
import { api } from './api/client';
import { getSyntheticDataset } from './api/synthetic';
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
import { SyntheticMap } from './components/SyntheticMap';
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
import type { Alert, Camera, DatasetMode, FetchState, PaneKey } from './types';

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
  const [mode, setMode] = useState<DatasetMode>('live');
  const isLiveMode = mode === 'live';
  const [simulationTime, setSimulationTime] = useState(0);
  const [simulationRunning, setSimulationRunning] = useState(false);

  useEffect(() => {
    if (!simulationRunning) return;
    const interval = window.setInterval(() => {
      setSimulationTime((current) => {
        const next = Math.min(current + 0.25, 120);
        if (next >= 120) setSimulationRunning(false);
        return next;
      });
    }, 250);
    return () => window.clearInterval(interval);
  }, [simulationRunning]);

  const cameras = useApiResource(api.getCameras, [mode], { pollMs: 20000, enabled: isLiveMode });
  const vehicles = useApiResource(api.getVehicles, [mode], { pollMs: 20000, enabled: isLiveMode });
  const alerts = useApiResource(api.getAlerts, [mode], { pollMs: 20000, enabled: isLiveMode });
  const synthetic = useApiResource(getSyntheticDataset, [mode], { enabled: !isLiveMode });
  const { entries: liveEntries, status: wsStatus } = useLiveFeed(isLiveMode);

  const selectedCameras = isLiveMode ? cameras.data : synthetic.data?.cameras;
  const selectedVehicles = isLiveMode ? vehicles.data : synthetic.data?.vehicles;
  const selectedAlerts = isLiveMode ? alerts.data : synthetic.data?.alerts;
  const selectedCameraState: FetchState = isLiveMode ? cameras.state : synthetic.state;
  const selectedVehicleState: FetchState = isLiveMode ? vehicles.state : synthetic.state;
  const selectedAlertState: FetchState = isLiveMode ? alerts.state : synthetic.state;
  const selectedCameraError = isLiveMode ? cameras.error : synthetic.error;
  const selectedVehicleError = isLiveMode ? vehicles.error : synthetic.error;
  const selectedAlertError = isLiveMode ? alerts.error : synthetic.error;
  const selectedCameraReload = isLiveMode ? cameras.reload : synthetic.reload;
  const selectedVehicleReload = isLiveMode ? vehicles.reload : synthetic.reload;
  const selectedAlertReload = isLiveMode ? alerts.reload : synthetic.reload;
  const selectedVehiclesUpdatedAt = isLiveMode ? vehicles.lastUpdatedAt : undefined;
  const selectedCamerasUpdatedAt = isLiveMode ? cameras.lastUpdatedAt : undefined;
  const selectedFeedEntries = useMemo(() => {
    if (isLiveMode) return liveEntries;
    return (synthetic.data?.feed ?? [])
      .filter((entry) => entry.simulationSeconds <= simulationTime)
      .slice(-20)
      .reverse();
  }, [isLiveMode, liveEntries, synthetic.data, simulationTime]);

  // The workspace — which dashboards the operator currently has open, and in
  // what order. Opening the same key twice is a no-op; togglePane closes it.
  const [openPanes, setOpenPanes] = useState<PaneKey[]>(['map', 'vehicles']);

  const [selectedVehicleId, setSelectedVehicleId] = useState<string>();
  const [selectedAlertId, setSelectedAlertId] = useState<string>();
  const [alertCameraRange, setAlertCameraRange] = useState<string[]>([]);
  const [flyToCameraId, setFlyToCameraId] = useState<string>();
  const [filters, setFilters] = useState<FilterState>({});

  const trajectories = useApiResource(
    () => isLiveMode
      ? api.getTrajectories(selectedVehicleId as string)
      : Promise.resolve(synthetic.data?.trajectories[selectedVehicleId as string] ?? []),
    [selectedVehicleId, mode, synthetic.data],
    { enabled: !!selectedVehicleId && (isLiveMode || !!synthetic.data) },
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
    () => selectedVehicles?.find((v) => v.vehicle_id === selectedVehicleId),
    [selectedVehicles, selectedVehicleId],
  );

  useEffect(() => {
    if (openPanes.includes('trajectory') && !selectedVehicleId && selectedVehicles?.length) {
      setSelectedVehicleId(selectedVehicles[0].vehicle_id);
    }
  }, [openPanes, selectedVehicleId, selectedVehicles]);

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
    if (!selectedVehicles) return selectedVehicles;
    if (!filters.dateFrom && !filters.dateTo) return selectedVehicles;
    return selectedVehicles.filter((v) => withinRange(v.last_seen, filters.dateFrom, filters.dateTo));
  }, [selectedVehicles, filters.dateFrom, filters.dateTo]);

  const filteredAlerts = useMemo(() => {
    if (!selectedAlerts) return selectedAlerts;
    return selectedAlerts.filter((a) => {
      if (!withinRange(a.created_at, filters.dateFrom, filters.dateTo)) return false;
      if (filters.cameraId && !(a.camera_range ?? []).includes(filters.cameraId)) return false;
      return true;
    });
  }, [selectedAlerts, filters.dateFrom, filters.dateTo, filters.cameraId]);

  const handleModeChange = (nextMode: DatasetMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    setSelectedVehicleId(undefined);
    setSelectedAlertId(undefined);
    setAlertCameraRange([]);
    setFlyToCameraId(undefined);
    setFilters({});
    setSimulationRunning(false);
    setSimulationTime(0);
    setOpenPanes((prev) => (prev.includes('map') ? prev : [...prev, 'map']));
  };

  const startSimulation = () => {
    setSimulationTime(0);
    setSimulationRunning(true);
  };

  const stopSimulation = () => setSimulationRunning(false);

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
    (isLiveMode && cameras.state === 'loading' && !cameras.data && vehicles.state === 'loading' && !vehicles.data) ||
    (!isLiveMode && synthetic.state === 'loading' && !synthetic.data);

  if (initialLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-ink">
        <LoadingState label="Connecting to camera network…" />
      </div>
    );
  }

  const activeCameraCount = selectedCameras?.filter((c) => c.status === 'active').length ?? 0;

  const modules: DockModule[] = [
    {
      key: 'vehicles',
      keyNum: '1',
      label: 'Vehicles',
      hint: `${selectedVehicles?.length ?? 0} tracked`,
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
    { key: 'map', keyNum: '3', label: isLiveMode ? 'Live Map' : 'Synthetic Map', hint: isLiveMode ? 'City grid' : 'CARLA grid', icon: <MapIcon /> },
    {
      key: 'feed',
      keyNum: '4',
      label: isLiveMode ? 'Live Feed' : 'Synthetic Feed',
      hint: isLiveMode ? (wsStatus === 'open' ? 'streaming' : wsStatus) : 'dataset stream',
      icon: <FeedIcon />,
    },
    {
      key: 'cameras',
      keyNum: '5',
      label: 'Cameras',
      hint: `${activeCameraCount}/${selectedCameras?.length ?? 0} online`,
      icon: <CamerasIcon />,
    },
    { key: 'analytics', keyNum: '6', label: 'Analytics', hint: 'summary', icon: <AnalyticsIcon /> },
    {
      key: 'trajectory',
      keyNum: '7',
      label: 'Trajectory',
      hint: selectedVehicle ? selectedVehicle.plate_text : 'vehicle route details',
      icon: <TrajectoryIcon />,
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
              state={selectedVehicleState}
              error={selectedVehicleError}
              onReload={selectedVehicleReload}
              selectedVehicleId={selectedVehicleId}
              onSelectVehicle={handleSelectVehicle}
              lastUpdatedAt={selectedVehiclesUpdatedAt}
            />
          ),
        };
      case 'cameras':
        return {
          key,
          title: 'Cameras',
          status: `${activeCameraCount}/${selectedCameras?.length ?? 0} online`,
          icon: <CamerasIcon />,
          content: (
            <CameraTable
              cameras={selectedCameras}
              state={selectedCameraState}
              error={selectedCameraError}
              onReload={selectedCameraReload}
              selectedCameraId={filters.cameraId}
              onSelectCamera={handleSelectCamera}
              lastUpdatedAt={selectedCamerasUpdatedAt}
              syntheticMode={!isLiveMode}
              simulationTime={simulationTime}
              simulationRunning={simulationRunning}
              onStartSimulation={startSimulation}
              onStopSimulation={stopSimulation}
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
              state={selectedAlertState}
              error={selectedAlertError}
              onReload={selectedAlertReload}
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
          content: <AnalyticsPanel vehicles={selectedVehicles} cameras={selectedCameras} alerts={selectedAlerts} />,
        };
      case 'feed':
        return {
          key,
          title: isLiveMode ? 'Live Feed' : 'Synthetic Feed',
          status: `${selectedFeedEntries.length}/20`,
          icon: <FeedIcon />,
          content: <LiveFeedPanel entries={selectedFeedEntries} status={isLiveMode ? wsStatus : simulationRunning ? 'open' : 'closed'} />,
        };
      case 'map':
        return {
          key,
          title: isLiveMode ? 'Live Map' : 'Synthetic Map',
          status: isLiveMode && cameras.state === 'error' && !cameras.data ? 'offline' : 'sweeping',
          icon: <MapIcon />,
          content:
            isLiveMode && cameras.state === 'error' && !cameras.data ? (
              <div className="absolute inset-0 flex items-center justify-center bg-ink px-6 text-center">
                <div className="max-w-sm space-y-3">
                  <p className="text-sm text-fg-muted">{cameras.error}</p>
                  <button
                    onClick={selectedCameraReload}
                    className="text-xs font-semibold text-accent hover:text-fg border border-steel hover:border-accent/60 rounded-md px-3 py-1.5 transition-colors"
                  >
                    Retry connection
                  </button>
                </div>
              </div>
            ) : (
              isLiveMode ? (
                <>
                  <MapView
                    cameras={selectedCameras ?? []}
                    trajectories={visibleTrajectories ?? []}
                    selectedVehicleId={selectedVehicleId}
                    highlightedCameraIds={highlightedCameraIds}
                    focusedCameraId={focusedCameraId}
                    flyToCameraId={flyToCameraId}
                    onSelectCamera={handleSelectCamera}
                  />
                  <MapLegend />
                </>
              ) : (
                  <SyntheticMap
                    alerts={selectedAlerts ?? []}
                    trajectories={visibleTrajectories ?? []}
                    selectedVehicleId={selectedVehicleId}
                    focusedCameraId={focusedCameraId}
                  />
              )
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
              syntheticMode={!isLiveMode}
              vehicles={selectedVehicles}
              selectedVehicleId={selectedVehicleId}
              onSelectVehicle={handleSelectVehicle}
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
      <TopBar vehicles={selectedVehicles ?? []} onSelectVehicle={handleSelectVehicle} wsStatus={wsStatus} mode={mode} onModeChange={handleModeChange} />

      <div className="flex flex-1 min-h-0 flex-col md:flex-row">
        <aside className="flex flex-col shrink-0 w-full md:w-[240px] max-h-[38vh] md:max-h-none m-3 md:mr-0 rounded-2xl glass-panel overflow-hidden animate-panel-in">
          <FilterBar
            cameras={selectedCameras ?? []}
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
