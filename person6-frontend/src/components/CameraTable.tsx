import { useMemo, useState } from 'react';
import type { Camera, FetchState } from '../types';
import { formatDateTime, formatTime } from '../lib/format';
import { EmptyState, ErrorState, LoadingState } from './StatusStates';

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
}

export function CameraTable({
  cameras,
  state,
  error,
  onReload,
  selectedCameraId,
  onSelectCamera,
  lastUpdatedAt,
}: Props) {
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('camera_id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

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
                      onClick={() => onSelectCamera(c)}
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
