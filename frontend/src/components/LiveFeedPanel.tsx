import { useEffect, useMemo, useRef, useState } from 'react';
import type { LiveDetection } from '../types';
import type { WsStatus } from '../hooks/useLiveFeed';
import { formatTime } from '../lib/format';
import { EmptyState } from './StatusStates';

interface Props {
  entries: LiveDetection[];
  status: WsStatus;
}

const statusCopy: Record<WsStatus, string> = {
  open: 'Streaming live detections',
  connecting: 'Connecting to detection stream…',
  reconnecting: 'Connection dropped — retrying…',
  closed: 'Disconnected — retrying…',
};

const BUCKET_COUNT = 16;
const BUCKET_MS = 4000;
const WINDOW_MS = BUCKET_COUNT * BUCKET_MS;

/** Lightweight CSS-bar activity sparkline — a quick "pulse" read of recent
 * detection volume without pulling in a chart library for 16 numbers. */
function ActivitySparkline({ entries }: { entries: LiveDetection[] }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const buckets = useMemo(() => {
    const counts = Array.from({ length: BUCKET_COUNT }, () => 0);
    for (const e of entries) {
      const t = e._receivedAt ?? Date.parse(e.timestamp);
      const age = now - t;
      if (age < 0 || age > WINDOW_MS) continue;
      const idx = BUCKET_COUNT - 1 - Math.floor(age / BUCKET_MS);
      if (idx >= 0 && idx < BUCKET_COUNT) counts[idx] += 1;
    }
    return counts;
  }, [entries, now]);

  const max = Math.max(1, ...buckets);

  return (
    <div className="flex items-end gap-[3px] h-8 px-3.5">
      {buckets.map((c, i) => {
        const isLatest = i === BUCKET_COUNT - 1;
        const h = c === 0 ? 3 : Math.max(4, (c / max) * 32);
        return (
          <div
            key={i}
            className={`flex-1 rounded-sm transition-all duration-500 ease-out ${
              isLatest && c > 0 ? 'shadow-[0_0_8px_-1px_var(--color-accent)]' : ''
            }`}
            style={{
              height: h,
              backgroundColor: c === 0 ? 'var(--color-steel)' : 'var(--color-accent)',
              opacity: c === 0 ? 0.5 : 0.55 + Math.min(0.45, (c / max) * 0.45),
            }}
          />
        );
      })}
    </div>
  );
}

export function LiveFeedPanel({ entries, status }: Props) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [entries.length]);

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="border-b border-steel-soft shrink-0">
        <div className="px-3.5 pt-2.5 flex items-center gap-2">
          <span className="relative flex h-1.5 w-1.5">
            {status === 'open' && (
              <span className="absolute inline-flex h-full w-full rounded-full bg-active animate-pulse-live" />
            )}
            <span
              className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
                status === 'open' ? 'bg-active' : 'bg-amber'
              }`}
            />
          </span>
          <span className="text-[11px] font-medium text-fg-muted">{statusCopy[status]}</span>
        </div>
        <ActivitySparkline entries={entries} />
      </div>

      {entries.length === 0 ? (
        <EmptyState
          title={status === 'open' ? 'Waiting for detections' : 'No detections yet'}
          description="New ANPR hits from the camera network will stream in here as they happen."
        />
      ) : (
        <div ref={listRef} className="flex-1 overflow-auto p-2.5 space-y-1.5">
          <div className="divider-label pb-1">Detections · {entries.length}/20</div>
          {entries.map((e, i) => (
            <div
              key={e._key ?? i}
              className={`relative rounded-lg border border-steel-soft bg-ink-raised/80 px-3 py-1.5 overflow-hidden ${
                i === 0 ? 'animate-feed-in' : ''
              }`}
            >
              <div
                className="absolute inset-y-0 left-0 w-[3px]"
                style={{ backgroundColor: 'var(--color-accent)', opacity: i === 0 ? 0.9 : 0.35 }}
              />
              <div className="flex items-center justify-between gap-2 pl-1.5">
                <span className="font-mono text-[15px] font-bold text-fg tracking-wide">
                  {e.plate_text || '—'}
                </span>
                <span className="text-[10px] font-mono text-fg-faint shrink-0">
                  {formatTime(e.timestamp)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2 mt-1 pl-1.5">
                <span className="text-[11px] text-fg-muted capitalize">
                  {e.vehicle_type} · {e.vehicle_color}
                </span>
                <span className="text-[10px] font-mono font-semibold text-accent/90">
                  {e.camera_id}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
