import React from 'react';

type ArcGaugeProps = {
  value: number;
  max: number;
  label: string;
  size?: number;
};

export const ArcGauge = ({ value, max, label, size = 120 }: ArcGaugeProps) => {
  const radius = size * 0.4;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * radius;
  const validValue = Math.min(Math.max(value, 0), max);
  const strokeDashoffset = circumference - (validValue / max) * circumference;

  const isWarning = validValue / max > 0.75;
  const isDanger = validValue / max > 0.9;
  const color = isDanger ? 'var(--red)' : isWarning ? 'var(--orange)' : 'var(--cyan)';

  return (
    <div className="flex flex-col items-center justify-center p-4 bg-bg-2 rounded-sm border border-border">
      <div className="relative">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
          <circle
            cx={cx} cy={cy} r={radius}
            stroke="var(--bg-3)" strokeWidth="12" fill="none"
          />
          <circle
            cx={cx} cy={cy} r={radius}
            stroke={color} strokeWidth="12" fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xl font-mono text-text-1 font-bold">{value}</span>
        </div>
      </div>
      <span className="text-xs mt-2 font-ui text-text-3 uppercase tracking-widest">{label}</span>
    </div>
  );
};
