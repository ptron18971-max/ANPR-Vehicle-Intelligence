import type { ReactNode } from 'react';
import type { PaneKey } from '../types';

export interface DockModule {
  key: PaneKey;
  keyNum: string;
  label: string;
  hint: string;
  icon: ReactNode;
  badge?: number;
  disabled?: boolean;
}

interface Props {
  modules: DockModule[];
  open: Set<PaneKey>;
  onToggle: (key: PaneKey) => void;
}

export function Dock({ modules, open, onToggle }: Props) {
  return (
    <nav className="flex flex-col gap-1 p-2 overflow-y-auto" aria-label="Dashboard modules">
      <div className="divider-label px-1.5 pt-1 pb-2">Modules · 1–7</div>
      {modules.map((m) => {
        const isOpen = open.has(m.key);
        return (
          <button
            key={m.key}
            onClick={() => onToggle(m.key)}
            disabled={m.disabled}
            aria-pressed={isOpen}
            title={m.disabled ? m.hint : undefined}
            className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent disabled:opacity-40 disabled:cursor-not-allowed ${
              isOpen ? 'bg-accent/10 ring-1 ring-inset ring-accent/35' : 'hover:bg-panel-hover'
            }`}
          >
            <span className={`shrink-0 h-4 w-4 ${isOpen ? 'text-accent' : 'text-fg-muted'}`}>{m.icon}</span>
            <span className="flex-1 min-w-0">
              <span className="block text-[12.5px] font-medium text-fg truncate">{m.label}</span>
              <span className="block text-[10px] font-mono text-fg-faint truncate">{m.hint}</span>
            </span>
            {m.badge ? (
              <span className="shrink-0 text-[10px] font-mono font-bold bg-[#b8420f] text-white rounded-full px-1.5 leading-4">
                {m.badge}
              </span>
            ) : null}
            <span
              className={`shrink-0 text-[10px] font-mono font-bold border rounded px-1 leading-4 ${
                isOpen ? 'text-accent border-accent/40' : 'text-fg-faint border-steel'
              }`}
            >
              {m.keyNum}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
