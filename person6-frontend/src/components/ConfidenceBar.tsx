import { confidenceColor, confidenceRatio, formatPercent } from '../lib/format';

interface Props {
  value: number;
  width?: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ConfidenceBar({ value, width = 64, label, size = 'md' }: Props) {
  const ratio = confidenceRatio(value);
  const color = confidenceColor(value);
  const height = size === 'sm' ? 4 : size === 'lg' ? 8 : 6;
  const textSize = size === 'lg' ? 'text-base' : size === 'sm' ? 'text-[11px]' : 'text-xs';
  const glow = ratio >= 0.75 ? `0 0 8px 0 color-mix(in srgb, ${color} 65%, transparent)` : 'none';

  return (
    <div className="flex items-center gap-2" title={label ?? `Confidence ${formatPercent(value)}`}>
      <div className="rounded-full bg-steel overflow-hidden shrink-0" style={{ width, height }}>
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${ratio * 100}%`, backgroundColor: color, boxShadow: glow }}
        />
      </div>
      <span
        className={`font-mono font-bold tabular-nums shrink-0 ${textSize}`}
        style={{ color }}
      >
        {formatPercent(value)}
      </span>
    </div>
  );
}
