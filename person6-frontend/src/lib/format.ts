import type { AlertSeverity } from '../types';

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`;
  return `${Math.round(meters)} m`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

/** Average speed derived from a single hop's real distance/time — this is
 * genuine per-vehicle data (not a fabricated citywide estimate). Returns
 * undefined when travel_time_sec is zero/invalid to avoid a divide-by-zero
 * "Infinity km/h" reading. */
export function formatSpeedKmh(distanceMeters: number, seconds: number): string | undefined {
  if (!seconds || seconds <= 0) return undefined;
  const kmh = (distanceMeters / 1000) / (seconds / 3600);
  if (!Number.isFinite(kmh)) return undefined;
  return `${kmh.toFixed(0)} km/h`;
}

export function formatPercent(value: number): string {
  // Accept either 0-1 fractions or already-0-100 values.
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(0)}%`;
}

export function confidenceRatio(value: number): number {
  const pct = value <= 1 ? value : value / 100;
  return Math.max(0, Math.min(1, pct));
}

/** Maps a 0-1 confidence ratio to a color from red -> amber -> cyan/green. */
export function confidenceColor(value: number): string {
  const r = confidenceRatio(value);
  if (r >= 0.75) return 'var(--color-active)';
  if (r >= 0.45) return 'var(--color-amber)';
  return 'var(--color-severity-high)';
}

export function severityColor(severity: AlertSeverity): string {
  switch (severity) {
    case 'HIGH':
      return 'var(--color-severity-high)';
    case 'MEDIUM':
      return 'var(--color-severity-medium)';
    case 'LOW':
      return 'var(--color-severity-low)';
    default:
      return 'var(--color-fg-muted)';
  }
}

/** Categorizes any transition/observation `status` string into the three
 * tiers the UI distinguishes visually. Anything the backend sends that
 * isn't literally CONFIRMED or INFERRED is treated as "uncertain" rather
 * than silently lumped in with one of the other two. */
export function segmentTier(status: string): 'confirmed' | 'inferred' | 'uncertain' {
  if (status === 'CONFIRMED') return 'confirmed';
  if (status === 'INFERRED') return 'inferred';
  return 'uncertain';
}

export function segmentTierColor(status: string): string {
  const tier = segmentTier(status);
  if (tier === 'confirmed') return 'var(--color-signal-cyan)';
  if (tier === 'inferred') return 'var(--color-amber)';
  return 'var(--color-severity-high)';
}

/** Soft ambient glow shadow to pair with a semantic CSS-variable color on badges/rings. */
export function glowShadow(colorVar: string, spread = 14): string {
  return `0 0 0 1px color-mix(in srgb, ${colorVar} 45%, transparent), 0 0 ${spread}px 0 color-mix(in srgb, ${colorVar} 55%, transparent)`;
}

export function initials(text: string): string {
  return text.slice(0, 2).toUpperCase();
}
