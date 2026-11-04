import type { Alert, AlertSeverity, FetchState } from '../types';
import { ConfidenceBar } from './ConfidenceBar';
import { EmptyState, ErrorState, LoadingState } from './StatusStates';
import { formatDateTime, severityColor } from '../lib/format';

interface Props {
  alerts: Alert[] | undefined;
  state: FetchState;
  error?: string;
  onReload: () => void;
  onSelectAlert: (alert: Alert) => void;
  selectedAlertId?: string;
}

function SeverityIcon({ severity }: { severity: AlertSeverity }) {
  if (severity === 'HIGH') {
    return (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="currentColor">
        <path d="M12 2 1 21h22L12 2Zm0 6.5 6 10.5H6l6-10.5Z" />
        <rect x="11" y="10" width="2" height="5" fill="currentColor" />
        <circle cx="12" cy="17" r="1.1" fill="currentColor" />
      </svg>
    );
  }
  if (severity === 'MEDIUM') {
    return (
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v5" strokeLinecap="round" />
        <circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v4" strokeLinecap="round" />
      <circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function AlertsPanel({
  alerts,
  state,
  error,
  onReload,
  onSelectAlert,
  selectedAlertId,
}: Props) {
  if (state === 'loading' && !alerts) return <LoadingState label="Loading alerts…" />;
  if (state === 'error' && !alerts)
    return <ErrorState message={error ?? 'Could not load alerts.'} onRetry={onReload} />;
  if (!alerts || alerts.length === 0)
    return (
      <EmptyState
        title="No active alerts"
        description="Anomalies detected across the camera network will appear here."
      />
    );

  const sorted = [...alerts].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  const highCount = sorted.filter((a) => a.severity === 'HIGH').length;

  return (
    <div className="flex-1 overflow-auto divide-y divide-steel-soft/60">
      <div className="divider-label px-3.5 pt-2.5 pb-1.5">Alerts · {sorted.length}</div>
      {highCount > 0 && (
        <div className="px-3.5 py-1.5 flex items-center gap-2 bg-severity-high/10 border-b border-severity-high/20">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full rounded-full bg-severity-high animate-pulse-dot" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-severity-high" />
          </span>
          <span className="text-[11px] font-bold text-severity-high tracking-wide">
            {highCount} high-severity {highCount === 1 ? 'alert' : 'alerts'} need review
          </span>
        </div>
      )}
      {sorted.map((alert) => {
        const color = severityColor(alert.severity);
        const selected = alert.event_id === selectedAlertId;
        const isHigh = alert.severity === 'HIGH';
        return (
          <button
            key={alert.event_id}
            onClick={() => onSelectAlert(alert)}
            className={`relative w-full text-left px-3.5 py-2 flex flex-col gap-1 transition-colors ${
              selected ? 'bg-accent/10' : 'hover:bg-panel-hover'
            }`}
            style={{
              borderLeft: `1px solid ${color}`,
              background: selected
                ? undefined
                : `linear-gradient(90deg, color-mix(in srgb, ${color} 7%, transparent), transparent 60%)`,
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className="inline-flex items-center gap-1 text-[11px] font-extrabold px-2 py-0.5 rounded-md tracking-wide"
                style={{
                  color,
                  backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)`,
                  boxShadow: isHigh ? `0 0 10px -1px color-mix(in srgb, ${color} 70%, transparent)` : undefined,
                }}
              >
                <SeverityIcon severity={alert.severity} />
                {alert.severity}
              </span>
              <span className="text-[10px] font-mono text-fg-faint">
                {formatDateTime(alert.created_at)}
              </span>
            </div>
            <div className="text-[13px] text-fg font-semibold leading-snug">{alert.event_type}</div>
            <p className="text-[11px] text-fg-muted leading-snug line-clamp-2">{alert.reason}</p>
            <div className="flex items-center justify-between gap-2 pt-0.5">
              <span className="text-[10px] font-mono text-fg-faint truncate">
                {alert.vehicle_id} · {alert.camera_range?.join(' → ') || 'unknown route'}
              </span>
              <ConfidenceBar value={alert.confidence} width={40} size="sm" />
            </div>
          </button>
        );
      })}
    </div>
  );
}
