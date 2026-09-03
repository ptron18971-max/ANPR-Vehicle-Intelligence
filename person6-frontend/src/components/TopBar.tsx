import { useEffect, useState } from 'react';
import type { Vehicle } from '../types';
import type { WsStatus } from '../hooks/useLiveFeed';
import { SearchBar } from './SearchBar';

interface Props {
  vehicles: Vehicle[];
  onSelectVehicle: (vehicleId: string) => void;
  wsStatus: WsStatus;
}

export function TopBar({ vehicles, onSelectVehicle, wsStatus }: Props) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const statusMeta: Record<
    WsStatus,
    { dot: string; label: string; text: string; pulse?: 'live' | 'dot' }
  > = {
    open: { dot: 'bg-active', label: 'Live', text: 'text-active', pulse: 'live' },
    connecting: { dot: 'bg-amber', label: 'Connecting', text: 'text-amber', pulse: 'dot' },
    reconnecting: { dot: 'bg-amber', label: 'Reconnecting', text: 'text-amber', pulse: 'dot' },
    closed: { dot: 'bg-severity-high', label: 'Offline', text: 'text-severity-high' },
  };
  const s = statusMeta[wsStatus];

  return (
    <header className="relative m-3 mb-0 shrink-0 rounded-2xl glass-panel animate-panel-in">
      <div className="flex items-center gap-4 px-4 py-2.5">
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="relative h-8 w-8 rounded-lg bg-accent/10 border border-accent/40 flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 text-accent" fill="none">
              <circle cx="12" cy="12" r="3" fill="currentColor" />
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.4" opacity="0.5" />
              <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" strokeWidth="1.4" />
            </svg>
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-tight text-fg">Vehicle Intelligence</div>
            <div className="text-[10px] font-medium text-fg-faint tracking-[0.08em] uppercase">
              City Traffic Operations
            </div>
          </div>
        </div>

        <div className="flex-1 max-w-md">
          <SearchBar vehicles={vehicles} onSelectVehicle={onSelectVehicle} />
        </div>

        <div className="flex items-center gap-4 ml-auto shrink-0">
          <div className="flex items-center gap-3 rounded-lg border border-steel-soft bg-ink-raised/60 px-3 py-1.5">
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span
                  className={`absolute inline-flex h-full w-full rounded-full ${s.dot} ${
                    s.pulse === 'live' ? 'animate-pulse-live' : s.pulse === 'dot' ? 'animate-pulse-dot' : ''
                  }`}
                />
                <span className={`relative inline-flex h-2 w-2 rounded-full ${s.dot}`} />
              </span>
              <span className={`text-xs font-bold tracking-wide ${s.text}`}>{s.label}</span>
            </div>
            <div className="h-3 w-px bg-steel" />
            <div className="font-mono text-xs font-medium text-fg-muted tabular-nums hidden sm:block">
              {now.toLocaleTimeString([], { hour12: false })}
            </div>
          </div>
          <div className="hidden md:flex flex-col items-end leading-tight">
            <span className="font-mono text-lg font-bold text-accent tabular-nums">
              {vehicles.length}
            </span>
            <span className="text-[9px] font-medium text-fg-faint uppercase tracking-wide">
              tracked
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
