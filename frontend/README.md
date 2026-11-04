# Vehicle Intelligence Platform — Frontend

A GIS command-center dashboard for city-wide ANPR vehicle tracking: live map, vehicle search, real-time detection feed, alerts, and trajectory drill-down.

## Stack

- React + TypeScript + Vite
- MapLibre GL (CARTO dark basemap — no API key required)
- Recharts (per-hop confidence chart)
- Tailwind CSS v4

## Setup

```bash
npm install
npm run dev
```

The app expects the backend API at `http://127.0.0.1:8000` and the live feed at `ws://127.0.0.1:8000/ws/live` (see `src/api/client.ts` to change these). Start your backend first — the app will show a clear connection error with a retry button if it can't reach it, and the live feed will show "Reconnecting…" and retry with backoff if the socket drops.

## Project structure

```
src/
  api/client.ts          REST client for /cameras, /vehicles, /trajectories, /alerts
  hooks/
    useApiResource.ts    Generic fetch hook (loading/error/success + polling)
    useLiveFeed.ts        WebSocket hook with auto-reconnect (exp. backoff, capped at 20 entries)
  components/
    MapView.tsx          MapLibre map: camera pins + trajectory polylines
    MapLegend.tsx         Map legend (status colors, confirmed/inferred line key)
    TopBar.tsx / SearchBar.tsx
    VehicleTable.tsx      Sortable/filterable vehicle table
    AlertsPanel.tsx       Severity-coded alert list
    LiveFeedPanel.tsx     Animated live detection stream
    TrajectoryDrawer.tsx  Slide-up trajectory timeline + confidence chart
    ConfidenceBar.tsx     Shared confidence visualization (bar + color + %)
    CollapsiblePanel.tsx / Tabs.tsx / StatusStates.tsx
  lib/format.ts           Date/duration/confidence/severity formatting & color helpers
  types.ts                Types matching the backend API shapes exactly
```

## Notes

- Trajectories are drawn using the real `route_geometry` points per transition, not straight lines between cameras. CONFIRMED segments render solid; INFERRED render dashed; both scale opacity/width by `confidence`.
- Selecting a vehicle (via search, table row, or an alert) fits the map to its trajectory and opens the drawer.
- Clicking an alert also highlights its `camera_range` cameras on the map with an amber glow.
- Every panel has a real loading, error (with retry), and empty state — nothing renders blank while fetching.
- No features beyond what the listed endpoints support were added (no heatmaps or historical playback).
