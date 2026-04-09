import React from 'react';

type StatChipProps = {
  label: string;
  value: number | string;
  format?: 'currency' | 'percent' | 'number' | 'text';
  trend?: string; // e.g. "+2.3%"
  sparkline?: number[];
  className?: string;
};

function isValidNumber(v: number | string): boolean {
  if (typeof v === 'number') return !isNaN(v) && isFinite(v);
  return true;
}

function formatValue(value: number | string, format: string): string {
  if (typeof value === 'string') {
    // API may return numeric fields as strings — parse them before formatting
    const parsed = parseFloat(value);
    if (!isNaN(parsed) && isFinite(parsed)) {
      value = parsed;
    } else {
      return '—';
    }
  }
  if (!isValidNumber(value)) return '—';
  if (format === 'currency') {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  }
  if (format === 'percent') return `${value.toFixed(2)}%`;
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export const StatChip = ({ label, value, format = 'number', trend, sparkline, className = '' }: StatChipProps) => {
  const display = formatValue(value, format);
  const _isNaN = display === '—';

  let trendColor = '#adaaaa'; // muted
  if (trend?.startsWith('+')) trendColor = '#00fd87';
  else if (trend?.startsWith('-')) trendColor = '#ff716c';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#0e0e0e',
        border: '1px solid #494847',
        borderRadius: 4,
        padding: '12px',
      }}
    >
      <span style={{ color: '#adaaaa', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
        {label}
      </span>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <span
          style={{
            fontFamily: 'monospace',
            fontSize: 20,
            color: _isNaN ? '#494847' : '#e0e0e0',
          }}
        >
          {display}
        </span>
        {trend && (
          <span style={{ color: trendColor, fontSize: 12, marginLeft: 8, fontFamily: 'monospace' }}>
            {trend}
          </span>
        )}
      </div>
      {sparkline && sparkline.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'flex-end', gap: 2, height: 24 }}>
          {sparkline.map((val, i) => {
            const max = Math.max(...sparkline.map(Math.abs)) || 1;
            const h = Math.max(4, (Math.abs(val) / max) * 100);
            const bg = val >= 0 ? '#00fd87' : '#ff716c';
            return (
              <div
                key={i}
                style={{
                  width: '100%',
                  height: `${h}%`,
                  backgroundColor: bg,
                  borderRadius: '2px 2px 0 0',
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
