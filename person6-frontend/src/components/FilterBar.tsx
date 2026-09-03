import { useState } from 'react';
import type { Camera } from '../types';

export interface FilterState {
  dateFrom?: string;
  dateTo?: string;
  cameraId?: string;
}

interface Props {
  cameras: Camera[];
  filters: FilterState;
  onChange: (patch: Partial<FilterState>) => void;
  onClear: () => void;
}

export function FilterBar({ cameras, filters, onChange, onClear }: Props) {
  const [open, setOpen] = useState(false);
  const activeCount = [filters.dateFrom, filters.dateTo, filters.cameraId].filter(Boolean).length;

  const sortedCameras = [...cameras].sort((a, b) => a.camera_id.localeCompare(b.camera_id));

  return (
    <div className="border-b border-steel-soft/80 shrink-0">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3.5 py-2 text-left"
      >
        <span className="flex items-center gap-2 text-[11px] font-bold text-fg-muted uppercase tracking-wide">
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M4 5h16M7 12h10M10 19h4" strokeLinecap="round" />
          </svg>
          Filters
          {activeCount > 0 && (
            <span className="text-[10px] font-bold bg-accent text-ink rounded-full px-1.5 leading-4">
              {activeCount}
            </span>
          )}
        </span>
        <span className="text-fg-faint text-[10px]">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-3.5 pb-3 space-y-2.5 animate-panel-in">
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1">
              <span className="text-[9px] font-semibold text-fg-faint uppercase tracking-wide">From</span>
              <input
                type="datetime-local"
                value={filters.dateFrom ?? ''}
                onChange={(e) => onChange({ dateFrom: e.target.value || undefined })}
                className="bg-ink-raised/60 border border-steel rounded-md px-1.5 py-1 text-[11px] text-fg focus:outline-none focus:border-accent/60"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[9px] font-semibold text-fg-faint uppercase tracking-wide">To</span>
              <input
                type="datetime-local"
                value={filters.dateTo ?? ''}
                onChange={(e) => onChange({ dateTo: e.target.value || undefined })}
                className="bg-ink-raised/60 border border-steel rounded-md px-1.5 py-1 text-[11px] text-fg focus:outline-none focus:border-accent/60"
              />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[9px] font-semibold text-fg-faint uppercase tracking-wide">Camera</span>
            <select
              value={filters.cameraId ?? ''}
              onChange={(e) => onChange({ cameraId: e.target.value || undefined })}
              className="bg-ink-raised/60 border border-steel rounded-md px-1.5 py-1.5 text-[11px] text-fg focus:outline-none focus:border-accent/60"
            >
              <option value="">All cameras</option>
              {sortedCameras.map((c) => (
                <option key={c.camera_id} value={c.camera_id}>
                  {c.camera_id} · {c.road_segment}
                </option>
              ))}
            </select>
          </label>

          {activeCount > 0 && (
            <button
              onClick={onClear}
              className="text-[10px] font-semibold text-accent hover:text-fg transition-colors"
            >
              Clear all filters
            </button>
          )}
          <p className="text-[9px] text-fg-faint leading-relaxed">
            Date range applies to vehicles (last seen) and alerts (raised). Camera applies to
            alerts whose route touches it, and focuses the map.
          </p>
        </div>
      )}
    </div>
  );
}

export function withinRange(iso: string, from?: string, to?: string): boolean {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return true;
  if (from && t < Date.parse(from)) return false;
  if (to && t > Date.parse(to)) return false;
  return true;
}
