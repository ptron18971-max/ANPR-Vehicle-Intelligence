import { useMemo, useState } from 'react';
import type { Vehicle } from '../types';
import { formatDateTime, formatTime } from '../lib/format';
import { EmptyState, ErrorState, LoadingState } from './StatusStates';
import type { FetchState } from '../types';

type SortKey = 'plate_text' | 'vehicle_type' | 'vehicle_color' | 'last_seen';

interface Props {
  vehicles: Vehicle[] | undefined;
  state: FetchState;
  error?: string;
  onReload: () => void;
  selectedVehicleId?: string;
  onSelectVehicle: (vehicleId: string) => void;
  /** When the vehicle list was last successfully fetched — shown so an
   * operator never mistakes a snapshot for a live-updating table. */
  lastUpdatedAt?: number;
}

export function VehicleTable({
  vehicles,
  state,
  error,
  onReload,
  selectedVehicleId,
  onSelectVehicle,
  lastUpdatedAt,
}: Props) {
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('last_seen');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const rows = useMemo(() => {
    if (!vehicles) return [];
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? vehicles.filter(
          (v) =>
            v.plate_text.toLowerCase().includes(q) ||
            v.vehicle_type.toLowerCase().includes(q) ||
            v.vehicle_color.toLowerCase().includes(q) ||
            v.vehicle_id.toLowerCase().includes(q),
        )
      : vehicles;
    const sorted = [...filtered].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [vehicles, filter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: 'plate_text', label: 'Plate' },
    { key: 'vehicle_type', label: 'Type' },
    { key: 'vehicle_color', label: 'Color' },
    { key: 'last_seen', label: 'Last seen' },
  ];

  if (state === 'loading' && !vehicles) return <LoadingState label="Loading vehicles…" />;
  if (state === 'error' && !vehicles)
    return <ErrorState message={error ?? 'Could not load vehicles.'} onRetry={onReload} />;

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="p-2.5 border-b border-steel-soft shrink-0">
        <div className="relative">
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
            placeholder="Filter vehicles…"
            className="w-full bg-ink-raised/60 border border-steel rounded-md pl-7 pr-2.5 py-1.5 text-xs text-fg placeholder:text-fg-faint focus:outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/25 transition-colors"
          />
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          title={filter ? 'No vehicles match your filter' : 'No vehicles recorded yet'}
          description={
            filter ? 'Try a different plate, type, or color.' : 'Detections will populate this list as cameras report vehicles.'
          }
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
                {rows.map((v) => {
                  const selected = v.vehicle_id === selectedVehicleId;
                  return (
                    <tr
                      key={v.vehicle_id}
                      tabIndex={0}
                      role="button"
                      aria-selected={selected}
                      aria-label={`View ${v.plate_text} trajectory`}
                      onClick={() => onSelectVehicle(v.vehicle_id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectVehicle(v.vehicle_id);
                        }
                      }}
                      className={`relative cursor-pointer border-b border-steel-soft/60 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent ${
                        selected ? 'bg-accent/10' : 'hover:bg-panel-hover'
                      }`}
                      style={
                        selected
                          ? { boxShadow: 'inset 1px 0 0 0 var(--color-accent)' }
                          : undefined
                      }
                    >
                      <td className="px-2.5 py-1.5 font-mono font-bold text-fg whitespace-nowrap">{v.plate_text}</td>
                      <td className="px-2.5 py-1.5 text-fg-muted capitalize">{v.vehicle_type}</td>
                      <td className="px-2.5 py-1.5 text-fg-muted capitalize">{v.vehicle_color}</td>
                      <td className="px-2.5 py-1.5 text-fg-muted font-mono whitespace-nowrap">
                        {formatDateTime(v.last_seen)}
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
