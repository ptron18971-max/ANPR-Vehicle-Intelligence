import { useMemo, useRef, useState } from 'react';
import type { Vehicle } from '../types';

interface Props {
  vehicles: Vehicle[];
  onSelectVehicle: (vehicleId: string) => void;
}

export function SearchBar({ vehicles, onSelectVehicle }: Props) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return vehicles
      .filter(
        (v) =>
          v.plate_text.toLowerCase().includes(q) || v.vehicle_id.toLowerCase().includes(q),
      )
      .slice(0, 8);
  }, [query, vehicles]);

  const handleSelect = (v: Vehicle) => {
    onSelectVehicle(v.vehicle_id);
    setQuery(v.plate_text);
    setOpen(false);
    inputRef.current?.blur();
  };

  return (
    <div className="relative">
      <div className="relative">
        <svg
          className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-fg-faint"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M21 21l-4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          placeholder="Search plate or vehicle ID…"
          className="w-full bg-ink-raised/70 border border-steel rounded-md pl-8 pr-3 py-1.5 text-sm text-fg placeholder:text-fg-faint focus:outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/30 transition-colors"
        />
      </div>

      {open && query.trim() && (
        <div className="absolute z-30 mt-1.5 w-full rounded-lg glass-panel overflow-hidden">
          {matches.length === 0 ? (
            <div className="px-3 py-3 text-xs text-fg-faint">No vehicles match "{query}"</div>
          ) : (
            matches.map((v) => (
              <button
                key={v.vehicle_id}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handleSelect(v)}
                className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-accent/10 transition-colors border-b border-steel-soft last:border-0"
              >
                <div>
                  <div className="font-mono text-sm font-bold text-fg">{v.plate_text}</div>
                  <div className="text-[11px] text-fg-faint">
                    {v.vehicle_type} · {v.vehicle_color}
                  </div>
                </div>
                <span className="text-[10px] text-fg-faint font-mono">{v.vehicle_id}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
