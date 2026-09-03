import type { ReactNode } from 'react';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-10 text-fg-faint">
      <div className="relative h-9 w-9">
        <div className="absolute inset-0 rounded-full border-2 border-steel" />
        <div
          className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin"
          style={{ filter: 'drop-shadow(0 0 6px color-mix(in srgb, var(--color-accent) 60%, transparent))' }}
        />
      </div>
      <span className="text-xs font-medium tracking-wide text-fg-muted">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-10 px-4 text-center">
      <div className="h-9 w-9 rounded-full bg-severity-high/15 border border-severity-high/30 flex items-center justify-center text-severity-high font-bold shadow-[0_0_16px_-4px_var(--color-severity-high)]">
        !
      </div>
      <p className="text-sm text-fg-muted max-w-xs">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-semibold text-accent hover:text-fg border border-steel hover:border-accent/60 hover:shadow-[0_0_14px_-4px_var(--color-accent)] rounded-md px-3 py-1.5 transition-all"
        >
          Retry
        </button>
      )}
    </div>
  );
}

function DefaultEmptyIcon() {
  return (
    <div className="relative h-10 w-10 mb-1">
      <div className="absolute inset-0 rounded-full border border-steel" />
      <div className="absolute inset-[7px] rounded-full border border-steel-soft" />
      <div className="absolute inset-[15px] rounded-full bg-steel-soft animate-glow-ring" />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 py-10 px-4 text-center">
      {icon !== null && <div className="text-fg-faint">{icon ?? <DefaultEmptyIcon />}</div>}
      <p className="text-sm font-semibold text-fg-muted">{title}</p>
      {description && <p className="text-xs text-fg-faint max-w-xs">{description}</p>}
    </div>
  );
}
