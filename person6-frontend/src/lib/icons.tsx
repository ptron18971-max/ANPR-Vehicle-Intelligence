/** Single-stroke line icon set for the dock/pane chrome — one voice, no mixed
 * icon libraries, no emoji standing in for icons. */

const common = { viewBox: '0 0 20 20', fill: 'none', stroke: 'currentColor', strokeWidth: 1.5 } as const;

export function VehiclesIcon() {
  return (
    <svg {...common}>
      <path d="M3 13l1.4-4.2A2 2 0 0 1 6.3 7.5h7.4a2 2 0 0 1 1.9 1.3L17 13v3H3v-3Z" />
      <circle cx="6.5" cy="16" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="13.5" cy="16" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function AlertsIcon() {
  return (
    <svg {...common}>
      <path d="M10 3 2 17h16L10 3Z" />
      <path d="M10 8v4" strokeLinecap="round" />
      <circle cx="10" cy="14.2" r="0.7" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function MapIcon() {
  return (
    <svg {...common}>
      <circle cx="10" cy="10" r="7" />
      <circle cx="10" cy="10" r="1.4" fill="currentColor" stroke="none" />
      <path d="M10 3v2M10 15v2M3 10h2M15 10h2" strokeLinecap="round" />
    </svg>
  );
}

export function FeedIcon() {
  return (
    <svg {...common}>
      <path d="M10 16.5V4" strokeLinecap="round" />
      <path d="M6.5 8a5 5 0 0 1 7 0M4 5.5a9 9 0 0 1 12 0" strokeLinecap="round" />
    </svg>
  );
}

export function CamerasIcon() {
  return (
    <svg {...common}>
      <rect x="2.5" y="6" width="11" height="8" rx="1.5" />
      <path d="M13.5 9l4-2.3v6.6l-4-2.3" />
    </svg>
  );
}

export function AnalyticsIcon() {
  return (
    <svg {...common}>
      <path d="M4 16V10M9.5 16V4M15 16v-6" strokeLinecap="round" />
    </svg>
  );
}

export function TrajectoryIcon() {
  return (
    <svg {...common}>
      <circle cx="4" cy="15" r="1.6" />
      <circle cx="16" cy="5" r="1.6" />
      <path d="M5.3 13.8 14.7 6.2" strokeLinecap="round" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 4l8 8M12 4l-8 8" strokeLinecap="round" />
    </svg>
  );
}
