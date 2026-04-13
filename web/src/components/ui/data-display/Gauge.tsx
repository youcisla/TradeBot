"use client";

type ColorVariant = "positive" | "negative" | "warning" | "info" | "accent";

const COLOR_MAP: Record<ColorVariant, string> = {
  positive: "var(--positive)",
  negative: "var(--negative)",
  warning:  "var(--warning)",
  info:     "var(--info)",
  accent:   "var(--accent)",
};

interface GaugeProps {
  /** Current value */
  value: number;
  /** Maximum value (for fill gauges) or the negative limit (for drawdown) */
  max: number;
  /** Display label above the gauge */
  label?: string;
  /** Show threshold markers (for risk gauges) */
  thresholds?: {
    warnAt: number;      // e.g. 50 → show warning color above 50%
    criticalAt: number; // e.g. 80 → show critical color above 80%
  };
  /** Color of the fill when value is low */
  baseColor?: ColorVariant;
  /** Show percentage label */
  showPercent?: boolean;
  /** Sub-label below the bar (e.g. "/ $500 limit") */
  sub?: string;
  /** Height of the bar */
  height?: number;
  className?: string;
}

/**
 * Horizontal fill gauge.
 * Used for: drawdown %, position utilisation, confidence score.
 *
 * @example
 * <Gauge
 *   value={-2.3}
 *   max={-5}
 *   label="Daily Drawdown"
 *   thresholds={{ warnAt: 50, criticalAt: 80 }}
 *   sub="/ $500 limit"
 * />
 */
export function Gauge({
  value,
  max,
  label,
  thresholds,
  baseColor = "positive",
  showPercent = true,
  sub,
  height = 6,
  className,
}: GaugeProps) {
  // For drawdown: value and max are negative; use abs for fill %
  const absValue = Math.abs(value);
  const absMax   = Math.abs(max);
  const pct = absMax > 0 ? Math.min((absValue / absMax) * 100, 100) : 0;

  // Determine fill color based on thresholds
  let fillColor = COLOR_MAP[baseColor];
  if (thresholds) {
    if (absValue >= thresholds.criticalAt) fillColor = "var(--negative)";
    else if (absValue >= thresholds.warnAt)  fillColor = "var(--warning)";
  }

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {label && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: 10,
              fontWeight: 600,
              color: "var(--text-2)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {label}
          </span>
          {showPercent && (
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                fontWeight: 700,
                color: fillColor,
              }}
            >
              {value.toFixed(1)}%
            </span>
          )}
        </div>
      )}

      {/* Track */}
      <div
        style={{
          height,
          background: "var(--bg-3)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        {/* Fill */}
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: fillColor,
            borderRadius: 3,
            transition: "width 0.4s ease, background 0.3s ease",
            boxShadow: `0 0 6px ${fillColor}60`,
          }}
        />
      </div>

      {sub && (
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            color: "var(--text-3)",
          }}
        >
          {sub}
        </span>
      )}
    </div>
  );
}
