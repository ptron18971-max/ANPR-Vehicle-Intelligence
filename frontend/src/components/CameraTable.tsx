import { useEffect, useMemo, useRef, useState } from 'react';
import type { Camera, FetchState } from '../types';
import { formatDateTime, formatTime } from '../lib/format';
import { EmptyState, ErrorState, LoadingState } from './StatusStates';
import { Play, Square, Video } from 'lucide-react';

type SortKey = 'camera_id' | 'road_segment' | 'status' | 'installed_at';

interface Props {
  cameras: Camera[] | undefined;
  state: FetchState;
  error?: string;
  onReload: () => void;
  selectedCameraId?: string;
  onSelectCamera: (camera: Camera) => void;
  /** When the camera list was last successfully fetched — shown so an
   * operator never mistakes a snapshot for a live-updating table. */
  lastUpdatedAt?: number;
  syntheticMode?: boolean;
  simulationTime?: number;
  simulationRunning?: boolean;
  onStartSimulation?: () => void;
  onStopSimulation?: () => void;
}

export function CameraTable({
  cameras,
  state,
  error,
  onReload,
  selectedCameraId,
  onSelectCamera,
  lastUpdatedAt,
  syntheticMode = false,
  simulationTime = 0,
  simulationRunning = false,
  onStartSimulation,
  onStopSimulation,
}: Props) {
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('camera_id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [watchedCameraId, setWatchedCameraId] = useState<string>();
  const videoRef = useRef<HTMLVideoElement>(null);

  const simulationFinished = simulationTime >= 120;
  const watchedCamera = cameras?.find((camera) => camera.camera_id === watchedCameraId);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !watchedCameraId || simulationFinished) return;
    video.currentTime = simulationTime;
    if (simulationRunning) void video.play().catch(() => undefined);
    else video.pause();
  }, [watchedCameraId, simulationRunning, simulationFinished]);

  const watchCamera = (camera: Camera) => {
    if (!syntheticMode || simulationFinished) return;
    setWatchedCameraId(camera.camera_id);
    onSelectCamera(camera);
  };

  const rows = useMemo(() => {
    if (!cameras) return [];
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? cameras.filter(
          (c) =>
            c.camera_id.toLowerCase().includes(q) ||
            c.road_segment.toLowerCase().includes(q) ||
            c.status.toLowerCase().includes(q),
        )
      : cameras;
    return [...filtered].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [cameras, filter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: 'camera_id', label: 'Camera' },
    { key: 'road_segment', label: 'Segment' },
    { key: 'status', label: 'Status' },
    { key: 'installed_at', label: 'Installed' },
  ];

  if (state === 'loading' && !cameras) return <LoadingState label="Loading cameras…" />;
  if (state === 'error' && !cameras)
    return <ErrorState message={error ?? 'Could not load cameras.'} onRetry={onReload} />;

  const activeCount = cameras?.filter((c) => c.status === 'active').length ?? 0;

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {syntheticMode && (
        <div className="border-b border-steel-soft bg-ink-raised/40 p-2.5 space-y-2 shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wide text-fg-muted">Synthetic simulation</div>
              <div className={`font-mono text-sm font-bold tabular-nums ${simulationFinished ? 'text-severity-high' : 'text-accent'}`}>
                {Math.floor(simulationTime / 60).toString().padStart(2, '0')}:{Math.floor(simulationTime % 60).toString().padStart(2, '0')}
              </div>
            </div>
            {!simulationRunning && (
              <button
                type="button"
                onClick={onStartSimulation}
                className="inline-flex items-center gap-1.5 rounded-md bg-accent px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-ink hover:bg-accent/85"
              >
                <Play size={12} /> {simulationFinished ? 'Restart simulation' : 'Run simulation'}
              </button>
            )}
            {simulationRunning && (
              <button
                type="button"
                onClick={onStopSimulation}
                className="inline-flex items-center gap-1.5 rounded-md border border-steel px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-fg-muted hover:border-accent hover:text-fg"
              >
                <Square size={11} /> Stop
              </button>
            )}
            {simulationFinished && <span className="text-[10px] font-bold uppercase text-severity-high">Simulation ended</span>}
          </div>

          <div className="overflow-hidden rounded-md border border-steel-soft bg-black/30">
            {watchedCamera && !simulationFinished ? (
              <div>
                <div className="flex items-center justify-between border-b border-steel-soft px-2.5 py-1.5">
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-fg">
                    <Video size={12} className="text-accent" /> {watchedCamera.camera_id} live feed
                  </span>
                  <span className="font-mono text-[10px] text-fg-muted">{Math.floor(simulationTime)}s</span>
                </div>
                <video
                  ref={videoRef}
                  key={watchedCamera.camera_id}
                  src={`/videos/${watchedCamera.camera_id}_tracked.mp4`}
                  muted
                  playsInline
                  className="aspect-video w-full object-contain"
                  onLoadedMetadata={(event) => {
                    event.currentTarget.currentTime = simulationTime;
                    if (simulationRunning) void event.currentTarget.play().catch(() => undefined);
                  }}
                />
              </div>
            ) : (
              <div className="flex aspect-video items-center justify-center px-4 text-center text-[10px] uppercase tracking-wide text-fg-faint">
                {simulationFinished ? 'Simulation ended — restart to view camera feeds' : 'Run the simulation, then select a camera to view its feed'}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="p-2.5 border-b border-steel-soft flex items-center gap-2 shrink-0">
        <div className="relative flex-1">
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-fg-faint"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M21 21l-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter cameras…"
            className="w-full bg-ink-raised/60 border border-steel rounded-md pl-7 pr-2.5 py-1.5 text-xs text-fg placeholder:text-fg-faint focus:outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/25 transition-colors"
          />
        </div>
        <span className="text-[10px] font-mono text-active font-bold shrink-0">
          {activeCount}/{cameras?.length ?? 0}
        </span>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          title={filter ? 'No cameras match your filter' : 'No cameras registered'}
          description={filter ? 'Try a different ID, segment, or status.' : 'Camera inventory will appear here once registered.'}
        />
      ) : (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center gap-2 px-2.5 pt-2 pb-1 shrink-0">
            <span className="divider-label flex-1">Results · {rows.length}</span>
            {lastUpdatedAt && (
              <span className="text-[9px] font-mono text-fg-muted shrink-0" title="Last refreshed">
                Updated {formatTime(new Date(lastUpdatedAt).toISOString())}
              </span>
            )}
          </div>
          <div className="flex-1 overflow-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-ink-raised/95 backdrop-blur-sm z-10">
                <tr className="border-b border-steel-soft text-fg-faint">
                  {columns.map((col) => (
                    <th key={col.key} className="text-left font-bold px-2.5 py-1.5 select-none">
                      <button
                        onClick={() => toggleSort(col.key)}
                        className="flex items-center gap-1 hover:text-fg transition-colors uppercase tracking-wide text-[10px]"
                      >
                        {col.label}
                        {sortKey === col.key && (
                          <span className="text-accent">{sortDir === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => {
                  const selected = c.camera_id === selectedCameraId;
                  return (
                    <tr
                      key={c.camera_id}
                      tabIndex={0}
                      role="button"
                      aria-selected={selected}
                      aria-label={`Focus map on ${c.camera_id}`}
                      onClick={() => (syntheticMode ? watchCamera(c) : onSelectCamera(c))}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectCamera(c);
                        }
                      }}
                      className={`cursor-pointer border-b border-steel-soft/60 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent ${
                        selected ? 'bg-accent/10' : 'hover:bg-panel-hover'
                      }`}
                      style={selected ? { boxShadow: 'inset 1px 0 0 0 var(--color-accent)' } : undefined}
                    >
                      <td className="px-2.5 py-1.5 font-mono font-bold text-fg">{c.camera_id}</td>
                      <td className="px-2.5 py-1.5 text-fg-muted">{c.road_segment}</td>
                      <td className="px-2.5 py-1.5">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase ${
                            c.status === 'active' ? 'text-active' : 'text-offline'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              c.status === 'active' ? 'bg-active' : 'bg-offline'
                            }`}
                          />
                          {c.status}
                        </span>
                      </td>
                      <td className="px-2.5 py-1.5 text-fg-muted font-mono whitespace-nowrap">
                        {c.installed_at ? formatDateTime(c.installed_at) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
