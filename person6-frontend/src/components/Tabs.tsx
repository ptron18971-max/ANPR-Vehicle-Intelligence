interface Props<T extends string> {
  tabs: { key: T; label: string; badge?: number; badgeTone?: 'neutral' | 'alert' }[];
  active: T;
  onChange: (key: T) => void;
}

export function Tabs<T extends string>({ tabs, active, onChange }: Props<T>) {
  return (
    <div className="flex gap-1 px-2 pt-2.5 shrink-0">
      {tabs.map((tab) => {
        const isActive = active === tab.key;
        const hasBadge = typeof tab.badge === 'number' && tab.badge > 0;
        const alertBadge = hasBadge && tab.badgeTone === 'alert';
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`relative flex-1 flex items-center justify-center gap-1 text-[10.5px] font-semibold rounded-lg px-1 py-1.5 transition-all ${
              isActive
                ? 'bg-accent/12 text-accent shadow-[0_0_0_1px_var(--color-accent-soft)_inset]'
                : 'text-fg-muted hover:text-fg hover:bg-panel-hover'
            }`}
          >
            {tab.label}
            {hasBadge && (
              <span
                className={`text-[9px] font-bold font-mono rounded-full px-1 leading-4 ${
                  // Solid white-on-orange at this size needs a deeper shade
                  // than --color-severity-high (tuned for text/outline use)
                  // to clear 4.5:1 — d65118 + white is only 4.16:1.
                  alertBadge
                    ? 'bg-[#b8420f] text-white shadow-[0_0_10px_-1px_var(--color-severity-high)]'
                    : isActive
                      ? 'bg-accent text-ink'
                      : 'bg-steel text-fg-muted'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
