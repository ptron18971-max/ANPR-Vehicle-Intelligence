import type { ReactNode } from 'react';
import type { PaneKey } from '../types';
import { CloseIcon } from '../lib/icons';

export interface WorkspacePane {
  key: PaneKey;
  title: string;
  status: string;
  icon: ReactNode;
  content: ReactNode;
}

interface Props {
  panes: WorkspacePane[];
  onClose: (key: PaneKey) => void;
}

/** Tiles open panes into a grid sized to the count — 1 pane fills the space,
 * more panes fold into roughly-square tiles. An uneven trailing row's lone
 * survivor spans the leftover columns instead of leaving a dead cell. */
export function Workspace({ panes, onClose }: Props) {
  const n = panes.length;

  if (n === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="max-w-sm text-center text-[12.5px] font-mono text-fg-faint leading-relaxed">
          No panes open. Pick a module from the dock — or press{' '}
          <span className="text-fg-muted font-semibold">1</span>–<span className="text-fg-muted font-semibold">7</span> — to
          bring it into the workspace. Open as many as you need, side by side.
        </p>
      </div>
    );
  }

  const cols = Math.ceil(Math.sqrt(n));
  const rows = Math.ceil(n / cols);

  return (
    <div
      className="flex-1 min-h-0 grid gap-1.5 p-1.5"
      style={{
        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
      }}
    >
      {panes.map((p, i) => {
        const lastRowStart = (rows - 1) * cols;
        const isTrailingLone = n % cols !== 0 && i === n - 1 && i >= lastRowStart;
        const span = isTrailingLone ? cols - (n % cols) + 1 : 1;
        return (
          <section
            key={p.key}
            aria-label={`${p.title} panel`}
            className="flex flex-col min-w-0 min-h-0 rounded-xl glass-panel overflow-hidden animate-panel-in"
            style={span > 1 ? { gridColumn: `span ${span}` } : undefined}
          >
            <div className="flex items-center gap-2 px-3 py-1.5 border-b border-steel-soft/80 shrink-0 bg-gradient-to-b from-white/[0.03] to-transparent">
              <span className="h-3.5 w-3.5 text-accent shrink-0">{p.icon}</span>
              <span className="text-[10.5px] font-mono font-bold uppercase tracking-wide text-fg-muted">
                {p.title}
              </span>
              <span className="text-[10px] font-mono text-fg-faint ml-auto truncate">{p.status}</span>
              <button
                onClick={() => onClose(p.key)}
                aria-label={`Close ${p.title}`}
                className="shrink-0 h-5 w-5 flex items-center justify-center rounded text-fg-faint hover:text-fg hover:bg-panel-hover transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
              >
                <span className="h-2.5 w-2.5">
                  <CloseIcon />
                </span>
              </button>
            </div>
            <div className="relative flex flex-1 flex-col min-h-0">{p.content}</div>
          </section>
        );
      })}
    </div>
  );
}
