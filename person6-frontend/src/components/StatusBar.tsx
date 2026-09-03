import { useEffect, useState } from 'react';

interface Props {
  paneCount: number;
}

/** Real elapsed time since this session was opened — not a fabricated
 * "uptime" stat. Ticks every second like the top-bar clock. */
export function StatusBar({ paneCount }: Props) {
  const [startedAt] = useState(() => Date.now());
  const [uptime, setUptime] = useState('00:00:00');

  useEffect(() => {
    const tick = () => {
      const s = Math.floor((Date.now() - startedAt) / 1000);
      const hh = String(Math.floor(s / 3600)).padStart(2, '0');
      const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
      const ss = String(s % 60).padStart(2, '0');
      setUptime(`${hh}:${mm}:${ss}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <footer className="flex items-center gap-4 px-4 py-1.5 mx-3 mb-3 rounded-xl glass-panel text-[11px] font-mono text-fg-faint shrink-0">
      <span>
        SESSION <span className="text-fg-muted tabular-nums">{uptime}</span>
      </span>
      <span className="text-steel">·</span>
      <span>
        PANES <span className="text-fg-muted tabular-nums">{paneCount}</span>
      </span>
      <span className="text-steel">·</span>
      <span>
        ZONE <span className="text-fg-muted">Bengaluru · City Ops</span>
      </span>
      <div className="ml-auto hidden md:flex items-center gap-4">
        <span>
          <kbd className="border border-steel rounded px-1 py-px">1</kbd>–
          <kbd className="border border-steel rounded px-1 py-px">7</kbd> toggle module
        </span>
        <span>
          <kbd className="border border-steel rounded px-1 py-px">Esc</kbd> close last pane
        </span>
      </div>
    </footer>
  );
}
