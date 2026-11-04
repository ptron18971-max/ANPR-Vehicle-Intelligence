import { useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { FetchState, Trajectory, Vehicle } from '../types';
import { assessSyntheticTransition, assessTransition } from '../api/constraintGraph';
import { ConfidenceBar } from './ConfidenceBar';
import { EmptyState, ErrorState, LoadingState } from './StatusStates';
import {
  confidenceColor,
  confidenceRatio,
  formatDateTime,
  formatDistance,
  formatDuration,
  formatPercent,
  formatSpeedKmh,
  segmentTierColor,
} from '../lib/format';

interface Props {
  vehicle: Vehicle | undefined;
  syntheticMode: boolean;
  vehicles: Vehicle[] | undefined;
  selectedVehicleId?: string;
  onSelectVehicle: (vehicleId: string) => void;
  trajectories: Trajectory[] | undefined;
  state: FetchState;
  error?: string;
  onReload: () => void;
}

export function TrajectoryPanel({
  vehicle,
  syntheticMode,
  vehicles,
  selectedVehicleId,
  onSelectVehicle,
  trajectories,
  state,
  error,
  onReload,
}: Props) {
  const [activeIdx, setActiveIdx] = useState(0);
  const traj = trajectories?.[Math.min(activeIdx, (trajectories?.length ?? 1) - 1)];

  const chartData = useMemo(() => {
    if (!traj) return [];
    return traj.transitions.map((t, i) => ({
      name: `${t.from_camera_id}→${t.to_camera_id}`,
      confidence: Math.round(confidenceRatio(t.confidence) * 100),
      status: t.status,
      idx: i,
    }));
  }, [traj]);

  if (!vehicle) {
    return (
      <EmptyState
        title="No vehicle selected"
        description="Select a vehicle from the Vehicles pane, an alert, or search above — its route appears here."
      />
    );
  }

  const trajColor = traj ? confidenceColor(traj.trajectory_confidence) : undefined;

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 border-b border-steel-soft/60 shrink-0">
        <div className="shrink-0">
          <label className="sr-only" htmlFor="trajectory-vehicle-select">Select vehicle trajectory</label>
          <select
            id="trajectory-vehicle-select"
            value={selectedVehicleId ?? ''}
            onChange={(event) => onSelectVehicle(event.target.value)}
            className="max-w-[280px] bg-ink-raised border border-steel rounded-md px-2 py-1 font-mono text-sm font-bold text-fg focus:outline-none focus:border-accent/60"
          >
            {(vehicles ?? []).map((option) => (
              <option key={option.vehicle_id} value={option.vehicle_id}>
                {option.plate_text} · {(option.cameras_seen ?? []).join(', ') || 'camera data unavailable'}
              </option>
            ))}
          </select>
          <div className="text-[10.5px] text-fg-faint capitalize whitespace-nowrap">
            {vehicle.vehicle_type} · {vehicle.vehicle_color}
          </div>
        </div>
        {traj && (
          <div
            className="text-[11px] font-extrabold px-2 py-1 rounded-lg shrink-0 tracking-wide"
            style={{
              color: trajColor,
              backgroundColor: `color-mix(in srgb, ${trajColor} 16%, transparent)`,
            }}
          >
            {formatPercent(traj.trajectory_confidence)} confidence
          </div>
        )}
        {traj && (
          <div className="hidden lg:flex items-center gap-2.5 text-[10.5px] text-fg-muted font-mono">
            <span className="font-semibold text-fg">{formatDistance(traj.distance_meters)}</span>
            <span className="font-semibold text-fg">{formatDuration(traj.duration)}</span>
            <span className="text-fg-faint uppercase tracking-wide">{traj.trajectory_status}</span>
          </div>
        )}
        {trajectories && trajectories.length > 1 && (
          <div className="flex gap-1 ml-auto shrink-0">
            {trajectories.map((t, i) => (
              <button
                key={t.trajectory_id}
                onClick={() => setActiveIdx(i)}
                className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent ${
                  i === activeIdx ? 'bg-accent/15 text-accent' : 'text-fg-muted hover:text-fg'
                }`}
              >
                Trip {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {state === 'loading' && !trajectories && <LoadingState label="Loading trajectory…" />}
        {state === 'error' && !trajectories && (
          <ErrorState message={error ?? 'Could not load trajectory.'} onRetry={onReload} />
        )}
        {trajectories && trajectories.length === 0 && (
          <EmptyState
            title="No trajectory data"
            description="This vehicle has no recorded multi-camera trajectory yet."
          />
        )}

        {traj && (
          <div className="flex h-full min-h-0">
            <div className="flex-1 min-w-0 flex flex-col px-3 py-2">
              <div className="divider-label pb-2 shrink-0">Route</div>
              <div
                className="flex-1 min-h-0 overflow-x-auto overflow-y-hidden"
                style={{
                  WebkitMaskImage: 'linear-gradient(90deg, black calc(100% - 24px), transparent 100%)',
                  maskImage: 'linear-gradient(90deg, black calc(100% - 24px), transparent 100%)',
                }}
              >
                <ol className="flex items-stretch gap-0 h-full min-w-max pl-3">
                  {traj.observations
                    .slice()
                    .sort((a, b) => a.sequence_number - b.sequence_number)
                    .map((obs, i, arr) => {
                      const nextTransition = traj.transitions.find(
                        (t) => t.from_camera_id === obs.camera_id,
                      );
                      const graphCheck = nextTransition
                        ? syntheticMode
                          ? assessSyntheticTransition(
                              nextTransition.from_camera_id,
                              nextTransition.to_camera_id,
                              nextTransition.travel_time_sec,
                            )
                          : nextTransition.constraint_status
                          ? {
                              status: nextTransition.constraint_status,
                              path: nextTransition.constraint_path ?? [],
                              minTravelTimeSec: nextTransition.min_travel_time_sec,
                              maxTravelTimeSec: nextTransition.max_travel_time_sec,
                            }
                          : assessTransition(
                              nextTransition.from_camera_id,
                              nextTransition.to_camera_id,
                              nextTransition.travel_time_sec,
                            )
                        : undefined;
                      const graphStatus = graphCheck?.status;
                      const graphColor = graphStatus === 'VALID'
                        ? 'var(--color-active)'
                        : graphStatus === 'RECOVERED'
                          ? 'var(--color-amber)'
                          : graphStatus === 'UNASSESSED'
                            ? 'var(--color-fg-faint)'
                            : 'var(--color-severity-high)';
                      return (
                        <li key={`${obs.camera_id}-${obs.sequence_number}`} className="flex items-stretch">
                          <div className="flex flex-col items-center justify-center w-[150px] px-2 py-2 rounded-lg border border-steel-soft bg-ink-raised/80">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-fg-faint font-mono">
                                #{obs.sequence_number}
                              </span>
                              <span
                                className="text-[9.5px] font-bold uppercase tracking-wide px-1 rounded"
                                style={{
                                  color: segmentTierColor(obs.status),
                                  backgroundColor: `color-mix(in srgb, ${segmentTierColor(obs.status)} 16%, transparent)`,
                                }}
                              >
                                {obs.status}
                              </span>
                            </div>
                            <span className="font-mono text-sm font-bold text-fg mt-0.5">{obs.camera_id}</span>
                            <span className="text-[10px] text-fg-faint font-mono mt-0.5">
                              {formatDateTime(obs.timestamp)}
                            </span>
                            <div className="mt-1.5">
                              <ConfidenceBar value={obs.confidence} width={48} size="sm" />
                            </div>
                          </div>
                          {i < arr.length - 1 && nextTransition && (
                            <div className="flex flex-col items-center justify-center px-2 min-w-[92px]">
                              <span
                                className="text-[10px] uppercase tracking-wide font-bold"
                                style={{ color: confidenceColor(nextTransition.confidence) }}
                              >
                                {nextTransition.status}
                              </span>
                              <svg width="72" height="10" className="my-1">
                                <line
                                  x1="0"
                                  y1="5"
                                  x2="72"
                                  y2="5"
                                  stroke={confidenceColor(nextTransition.confidence)}
                                  strokeWidth={nextTransition.status === 'CONFIRMED' ? 2.5 : 1.5}
                                  strokeDasharray={
                                    nextTransition.status === 'CONFIRMED'
                                      ? undefined
                                      : nextTransition.status === 'INFERRED'
                                        ? '4,3'
                                        : '1,2.5'
                                  }
                                  opacity={0.4 + confidenceRatio(nextTransition.confidence) * 0.6}
                                />
                              </svg>
                              <span className="text-[10px] text-fg-faint font-mono">
                                {formatDuration(nextTransition.travel_time_sec)}
                              </span>
                              {graphCheck && (
                                <span
                                  className="max-w-[120px] text-center text-[9px] font-mono leading-tight"
                                  style={{ color: graphColor }}
                                  title={`Constraint route: ${graphCheck.path.join(' → ') || 'no feasible path'}`}
                                >
                                  Graph {graphStatus?.replace('_', ' ')}
                                  {graphCheck.path.length > 0 && ` · ${graphCheck.path.join(' → ')}`}
                                  {graphCheck.minTravelTimeSec !== undefined && graphCheck.maxTravelTimeSec !== undefined
                                    && ` · ${graphCheck.minTravelTimeSec}-${graphCheck.maxTravelTimeSec}s`}
                                </span>
                              )}
                              {nextTransition.distance_meters > 0
                                && formatSpeedKmh(nextTransition.distance_meters, nextTransition.travel_time_sec) && (
                                <span className="text-[10px] font-semibold text-fg-muted font-mono">
                                  {formatSpeedKmh(nextTransition.distance_meters, nextTransition.travel_time_sec)}
                                </span>
                              )}
                            </div>
                          )}
                        </li>
                      );
                    })}
                </ol>
              </div>
            </div>

            {chartData.length > 0 && (
              <div className="w-[220px] shrink-0 border-l border-steel-soft/80 px-3 py-2.5 hidden xl:block">
                <div className="divider-label mb-1.5">Per-hop confidence</div>
                <ResponsiveContainer width="100%" height={130}>
                  <BarChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                    <CartesianGrid stroke="#0d3d55" vertical={false} />
                    <XAxis dataKey="idx" tick={false} axisLine={{ stroke: '#0d3d55' }} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#6d8a9a', fontSize: 9 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      cursor={{ fill: 'rgba(243,141,49,0.08)' }}
                      contentStyle={{
                        background: '#041b33f2',
                        border: '1px solid #0d3d55',
                        borderRadius: 8,
                        fontSize: 11,
                        boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                      }}
                      labelFormatter={() => ''}
                      formatter={(value, _name, entry) => [
                        `${value}%`,
                        (entry?.payload?.name as string | undefined) ?? 'confidence',
                      ]}
                    />
                    <Bar dataKey="confidence" radius={[3, 3, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={confidenceColor(d.confidence / 100)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
