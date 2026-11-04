import type { ReactNode } from 'react';

interface Props {
  side: 'left' | 'right';
  collapsed: boolean;
  onToggle: () => void;
  title: string;
  children: ReactNode;
  headerExtra?: ReactNode;
  accentIcon?: ReactNode;
}

export function CollapsiblePanel({
  side,
  collapsed,
  onToggle,
  title,
  children,
  headerExtra,
  accentIcon,
}: Props) {
  const arrow = side === 'left' ? (collapsed ? '›' : '‹') : collapsed ? '‹' : '›';
  // Expanded: straddle the panel/map boundary with a negative offset off the
  // panel's own edge — that edge is meaningful (300px away) so the overlap
  // reads as "grab here to collapse". Collapsed: the panel is a 0-width box,
  // so that same offset math places the button half off the viewport edge
  // instead (verified via boundingBox at 390px: x:-12 / x:378, half clipped).
  // A positive inset from the *inner* edge keeps it fully on-screen instead.
  const togglePositionClass = collapsed
    ? side === 'left'
      ? 'left-1'
      : 'right-1'
    : side === 'left'
      ? '-right-3'
      : '-left-3';

  return (
    <div
      className={`relative flex flex-col shrink-0 transition-[width,margin] duration-300 ease-out ${
        collapsed ? 'w-0 m-0' : `w-[300px] ${side === 'left' ? 'ml-3' : 'mr-3'}`
      } my-3`}
    >
      <button
        onClick={onToggle}
        aria-label={collapsed ? `Expand ${title}` : `Collapse ${title}`}
        className={`absolute top-4 z-20 h-6 w-6 flex items-center justify-center rounded-full glass-panel text-fg-muted hover:text-accent hover:border-accent/50 transition-all ${togglePositionClass}`}
      >
        <span className="text-xs leading-none">{arrow}</span>
      </button>

      <div
        className={`glass-panel flex flex-col min-h-0 h-full rounded-2xl overflow-hidden transition-all duration-300 ease-out ${
          collapsed
            ? 'opacity-0 pointer-events-none scale-[0.98]'
            : 'opacity-100 scale-100 animate-panel-in'
        } ${side === 'left' ? (collapsed ? '-translate-x-2' : 'translate-x-0') : collapsed ? 'translate-x-2' : 'translate-x-0'}`}
      >
        <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-steel-soft/80 shrink-0 bg-gradient-to-b from-white/[0.03] to-transparent">
          <div className="flex items-center gap-2">
            {accentIcon}
            <h2 className="text-[11px] font-bold text-fg tracking-[0.06em] uppercase">{title}</h2>
          </div>
          {headerExtra}
        </div>
        <div className="flex flex-1 flex-col min-h-0">{children}</div>
      </div>
    </div>
  );
}
