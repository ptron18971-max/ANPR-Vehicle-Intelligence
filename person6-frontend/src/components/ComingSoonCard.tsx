interface Props {
  title: string;
  description: string;
  neededEndpoint: string;
  icon: React.ReactNode;
}

export function ComingSoonCard({ title, description, neededEndpoint, icon }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-steel bg-ink-raised/40 p-3.5 space-y-2">
      <div className="flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-steel-soft flex items-center justify-center text-fg-faint shrink-0">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-bold text-fg">{title}</div>
          <span className="text-[9px] font-bold text-amber uppercase tracking-wide">
            Not yet available
          </span>
        </div>
      </div>
      <p className="text-[11px] text-fg-muted leading-relaxed">{description}</p>
      <div className="rounded-md bg-ink/60 border border-steel-soft px-2 py-1.5">
        <span className="text-[9px] font-semibold text-fg-faint uppercase tracking-wide block mb-0.5">
          Needs backend
        </span>
        <code className="text-[10px] font-mono text-accent/90 break-all">{neededEndpoint}</code>
      </div>
    </div>
  );
}
