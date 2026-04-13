"use client";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  icon?: React.ReactNode;
  color?: string;
  trend?: "up" | "down" | "flat";
}

export function StatCard({ label, value, sub, icon, color, trend }: StatCardProps) {
  return (
    <div
      className="rounded flex flex-col gap-1 p-4 relative overflow-hidden"
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border)",
      }}
    >
      {/* Accent bar */}
      {color && (
        <div
          className="absolute top-0 left-0 right-0 h-px"
          style={{ background: color }}
        />
      )}

      <div className="flex items-start justify-between gap-2">
        <span
          className="text-xs font-semibold uppercase tracking-widest"
          style={{
            color: "var(--text-3)",
            fontFamily: "var(--font-mono)",
            fontSize: 9,
          }}
        >
          {label}
        </span>
        {icon && (
          <span
            className="material-symbols-outlined text-base flex-shrink-0"
            style={{
              color: color ?? "var(--text-3)",
              fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16",
            }}
          >
            {icon as string}
          </span>
        )}
      </div>

      <div className="flex items-end gap-2">
        <span
          className="font-bold tracking-tight"
          style={{
            color: color ?? "var(--text-1)",
            fontFamily: "var(--font-mono)",
            fontSize: 20,
            lineHeight: 1.1,
          }}
        >
          {value}
        </span>
        {trend && (
          <span
            className="material-symbols-outlined text-sm mb-0.5"
            style={{
              color:
                trend === "up"
                  ? "var(--green)"
                  : trend === "down"
                  ? "var(--red)"
                  : "var(--text-3)",
              fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16",
            }}
          >
            {trend === "up" ? "trending_up" : trend === "down" ? "trending_down" : "trending_flat"}
          </span>
        )}
      </div>

      {sub && (
        <span
          className="text-xs"
          style={{
            color: "var(--text-2)",
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
