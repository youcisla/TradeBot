"use client";

type ColorVariant = "positive" | "negative" | "neutral" | "accent" | "warning" | "info";
type TrendVariant = "up" | "down" | "flat";
type SizeVariant = "sm" | "md" | "lg";

const COLOR_MAP: Record<ColorVariant, string> = {
  positive: "var(--positive)",
  negative: "var(--negative)",
  neutral:  "var(--text-1)",
  accent:   "var(--accent)",
  warning:  "var(--warning)",
  info:     "var(--info)",
};

/** Resolve a color token — accepts either a named variant or a raw CSS var string */
function resolveColor(color: ColorVariant | string): string {
  return COLOR_MAP[color as ColorVariant] ?? (color.startsWith("var(--") ? color : "var(--text-1)");
}

const TREND_ICON: Record<TrendVariant, string> = {
  up:   "arrow_upward",
  down: "arrow_downward",
  flat: "horizontal_rule",
};

interface StatCardProps {
  label: string;
  value: string;
  /** Secondary value below the main value */
  sub?: string;
  /** Material Symbols icon name */
  icon?: string;
  color?: ColorVariant | string;
  trend?: TrendVariant;
  size?: SizeVariant;
  /** Shows a pulsing dot next to the value (for live data) */
  pulse?: boolean;
  className?: string;
}

const FONT_SIZE: Record<SizeVariant, number> = {
  sm: 16,
  md: 20,
  lg: 28,
};

export function StatCard({
  label,
  value,
  sub,
  icon,
  color = "neutral",
  trend,
  size = "md",
  pulse,
  className,
}: StatCardProps) {
  const textColor = resolveColor(color);
  const fontSize = FONT_SIZE[size];

  return (
    <div
      className={`rounded flex flex-col gap-1 p-3 relative overflow-hidden ${className ?? ""}`}
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border)",
      }}
    >
      {/* Top accent bar */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: textColor }}
      />

      {/* Label row */}
      <div className="flex items-start justify-between gap-2">
        <span
          className="text-xs font-bold uppercase tracking-widest"
          style={{
            color: "var(--text-3)",
            fontFamily: "var(--font-ui)",
            fontSize: 9,
            letterSpacing: "0.08em",
          }}
        >
          {label}
        </span>
        {icon && (
          <span
            className="material-symbols-outlined text-base flex-shrink-0"
            style={{
              color: textColor,
              fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16",
            }}
          >
            {icon}
          </span>
        )}
      </div>

      {/* Value row */}
      <div className="flex items-end gap-2">
        {pulse && (
          <span
            className="mb-0.5 flex-shrink-0"
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: textColor,
              animation: "pulse-dot 2s ease-in-out infinite",
              boxShadow: `0 0 6px ${textColor}`,
            }}
          />
        )}
        <span
          className="font-bold leading-none"
          style={{
            color: textColor,
            fontFamily: "var(--font-mono)",
            fontSize,
            letterSpacing: "-0.01em",
          }}
        >
          {value}
        </span>
        {trend && (
          <span
            className="material-symbols-outlined mb-0.5"
            style={{
              fontSize: 14,
              color:
                trend === "up"
                  ? "var(--positive)"
                  : trend === "down"
                  ? "var(--negative)"
                  : "var(--text-3)",
              fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16",
            }}
          >
            {TREND_ICON[trend]}
          </span>
        )}
      </div>

      {/* Sub value */}
      {sub && (
        <span
          className="font-mono"
          style={{
            color: "var(--text-3)",
            fontFamily: "var(--font-mono)",
            fontSize: 10,
          }}
        >
          {sub}
        </span>
      )}
    </div>
  );
}
