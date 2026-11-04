interface Props {
  /** The trajectory drawer spans the full map width when open and sits on
   * top of this legend's bottom-left corner — false hides the legend
   * instead of letting the drawer visually occlude part of it. */
  visible?: boolean;
}

export function MapLegend({ visible = true }: Props) {
  return (
    <div
      className={`absolute bottom-4 left-4 z-10 rounded-xl glass-panel px-3.5 py-3 text-[11px] text-fg-muted space-y-1.5 w-[200px] transition-opacity duration-200 ease-out ${
        visible ? 'opacity-100 animate-panel-in' : 'opacity-0 pointer-events-none'
      }`}
    >
      <div className="divider-label pb-0.5">Legend</div>
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full bg-active animate-pulse-dot" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-active" />
        </span>
        <span>Camera active</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-offline" />
        <span>Camera offline</span>
      </div>

      <div className="divider-label pt-1.5 pb-0.5">Route confidence</div>
      <div className="flex items-center gap-2">
        {/* Matches the map's trajectory-confirmed line color, not the UI
            accent — confirmed/verified state is deliberately the cool teal,
            kept distinct from the warm accent (see index.css). */}
        <span
          className="inline-block h-[3px] w-4 rounded-full"
          style={{ backgroundColor: 'var(--color-signal-cyan)' }}
        />
        <span>Confirmed hop</span>
      </div>
      <div className="flex items-center gap-2">
        <svg width="16" height="3" className="shrink-0">
          <line x1="0" y1="1.5" x2="16" y2="1.5" stroke="#e8b83f" strokeWidth="2" strokeDasharray="3,2" />
        </svg>
        <span>Inferred hop</span>
      </div>
      <div className="flex items-center gap-2">
        <svg width="16" height="3" className="shrink-0">
          <line x1="0" y1="1.5" x2="16" y2="1.5" stroke="#d65118" strokeWidth="2" strokeDasharray="0.5,2" />
        </svg>
        <span>Uncertain hop</span>
      </div>

      <div className="divider-label pt-1.5 pb-0.5">Tracking</div>
      <div className="flex items-center gap-2">
        <span className="relative flex h-3 w-3 items-center justify-center shrink-0">
          <span className="absolute inline-flex h-full w-full rounded-full animate-pulse-live bg-accent" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
        </span>
        <span>Selected vehicle's last position</span>
      </div>
      <div className="text-fg-faint pt-1.5 border-t border-steel-soft/80 leading-relaxed">
        Opacity/width = confidence
        <br />
        Drag to rotate/tilt · compass resets north
      </div>
    </div>
  );
}
