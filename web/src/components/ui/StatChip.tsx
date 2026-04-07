import React from 'react';

type StatChipProps = {
  label: string;
  value: number | string;
  format?: 'currency' | 'percent' | 'number' | 'text';
  trend?: string; // e.g. "+2.3%"
  sparkline?: number[];
  className?: string;
};

export const StatChip = ({ label, value, format = 'number', trend, sparkline, className = '' }: StatChipProps) => {
  let displayValue = value;
  if (typeof value === 'number') {
    if (format === 'currency') displayValue = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
    else if (format === 'percent') displayValue = `${value.toFixed(2)}%`;
  }

  // Determine trend color
  let trendColor = 'text-text-3';
  if (trend?.startsWith('+')) trendColor = 'text-gold';
  else if (trend?.startsWith('-')) trendColor = 'text-red';

  return (
    <div className={`flex flex-col bg-bg-2 border border-border rounded-sm p-3 ${className}`}>
      <span className="text-text-3 text-xs uppercase font-ui tracking-wider mb-1">{label}</span>
      <div className="flex items-end justify-between">
        <span className={`text-xl font-mono text-text-1`}>{displayValue}</span>
        {trend && <span className={`text-xs ml-2 font-mono ${trendColor}`}>{trend}</span>}
      </div>
      {sparkline && sparkline.length > 0 && (
         <div className="mt-2 h-6 flex items-end space-x-1 opacity-70">
           {/* Mini bar chart representation */}
           {sparkline.map((val, i) => {
             const max = Math.max(...sparkline.map(Math.abs)) || 1;
             const h = Math.max(10, Math.abs(val) / max * 100);
             const bg = val >= 0 ? 'bg-gold' : 'bg-red';
             return <div key={i} className={`w-full ${bg} rounded-t-sm`} style={{ height: `${h}%` }} />;
           })}
         </div>
      )}
    </div>
  );
};
