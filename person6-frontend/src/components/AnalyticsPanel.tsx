import { useMemo } from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Alert, Camera, Vehicle } from '../types';
import { ComingSoonCard } from './ComingSoonCard';
import { EmptyState } from './StatusStates';

interface Props {
  vehicles: Vehicle[] | undefined;
  cameras: Camera[] | undefined;
  alerts: Alert[] | undefined;
}

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: '#d65118',
  MEDIUM: '#f36e25',
  LOW: '#facc15',
};

function MiniBarChart({
  data,
  colorFor,
}: {
  data: { name: string; value: number }[];
  colorFor: (name: string) => string;
}) {
  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="name"
          width={70}
          tick={{ fill: '#9fb3c2', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'rgba(243,141,49,0.06)' }}
          contentStyle={{
            background: '#041b33f2',
            border: '1px solid #0d3d55',
            borderRadius: 8,
            fontSize: 11,
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14}>
          {data.map((d, i) => (
            <Cell key={i} fill={colorFor(d.name)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AnalyticsPanel({ vehicles, cameras, alerts }: Props) {
  const severityData = useMemo(() => {
    if (!alerts) return [];
    const counts: Record<string, number> = {};
    for (const a of alerts) counts[a.severity] = (counts[a.severity] ?? 0) + 1;
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [alerts]);

  const typeData = useMemo(() => {
    if (!vehicles) return [];
    const counts: Record<string, number> = {};
    for (const v of vehicles) counts[v.vehicle_type] = (counts[v.vehicle_type] ?? 0) + 1;
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6);
  }, [vehicles]);

  const cameraStatusData = useMemo(() => {
    if (!cameras) return [];
    const active = cameras.filter((c) => c.status === 'active').length;
    const offline = cameras.length - active;
    return [
      { name: 'active', value: active },
      { name: 'offline', value: offline },
    ];
  }, [cameras]);

  const hasAnyData = (vehicles?.length ?? 0) + (cameras?.length ?? 0) + (alerts?.length ?? 0) > 0;

  return (
    <div className="flex-1 overflow-auto p-3.5 space-y-4">
      <div>
        <div className="divider-label mb-2">Live statistics</div>
        {!hasAnyData ? (
          <EmptyState
            title="No data yet"
            description="Summary charts populate once vehicles, cameras, and alerts have loaded."
          />
        ) : (
          <div className="space-y-4">
            {alerts && alerts.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-fg-muted mb-1">
                  Alerts by severity ({alerts.length} total)
                </div>
                <MiniBarChart data={severityData} colorFor={(n) => SEVERITY_COLORS[n] ?? '#9fb3c2'} />
              </div>
            )}
            {vehicles && vehicles.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-fg-muted mb-1">
                  Fleet by vehicle type ({vehicles.length} tracked)
                </div>
                <MiniBarChart data={typeData} colorFor={() => 'var(--color-accent)'} />
              </div>
            )}
            {cameras && cameras.length > 0 && (
              <div>
                <div className="text-[10px] font-semibold text-fg-muted mb-1">
                  Camera network status ({cameras.length} cameras)
                </div>
                <MiniBarChart
                  data={cameraStatusData}
                  colorFor={(n) => (n === 'active' ? 'var(--color-active)' : 'var(--color-offline)')}
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div>
        <div className="divider-label mb-2">Not yet available</div>
        <div className="space-y-2">
          <ComingSoonCard
            title="Traffic heatmap"
            description="Density/congestion overlay across the city. No endpoint currently returns aggregate detection density by area or time — this can't be built without fabricating numbers."
            neededEndpoint="GET /analytics/traffic-density (grid or road-segment density counts, ideally bucketed by time)"
            icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M4 20V10M10 20V4M16 20v-7M22 20V13" strokeLinecap="round" />
              </svg>
            }
          />
          <ComingSoonCard
            title="Speed by segment (citywide)"
            description="Average speed per road segment across all traffic. Per-vehicle hop speed is already shown in the trajectory drawer (derived from real distance/travel_time), but a citywide view needs the backend to aggregate across vehicles — looping every vehicle's trajectory client-side wouldn't scale."
            neededEndpoint="GET /analytics/segment-speed (avg speed per camera-to-camera hop, aggregated server-side)"
            icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M12 8v4l3 2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="12" cy="12" r="9" />
              </svg>
            }
          />
          <ComingSoonCard
            title="Route density / common corridors"
            description="Which routes vehicles most commonly take. This needs an origin-destination matrix or corridor-frequency aggregation computed server-side from historical trajectories."
            neededEndpoint="GET /analytics/od-matrix or /analytics/route-density"
            icon={
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="1.8">
                <circle cx="5" cy="6" r="2" />
                <circle cx="19" cy="18" r="2" />
                <path d="M7 7c4 2 8 6 10 10" strokeLinecap="round" />
              </svg>
            }
          />
        </div>
      </div>
    </div>
  );
}
