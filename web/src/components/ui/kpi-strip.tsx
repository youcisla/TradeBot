"use client";

import { cn } from "@/lib/utils";

interface KpiCellProps {
  label: string;
  value: string | React.ReactNode;
  sub?: string;
  accent?: boolean;
  className?: string;
}

export function KpiCell({ label, value, sub, accent, className }: KpiCellProps) {
  return (
    <div className={cn("kpi-cell", className)}>
      <span className="label">{label}</span>
      <span className="v" style={accent ? { color: "var(--accent-warm)" } : undefined}>
        {value}
      </span>
      {sub && <span className="sub">{sub}</span>}
    </div>
  );
}

interface KpiStripProps {
  children: React.ReactNode;
  className?: string;
}

export function KpiStrip({ children, className }: KpiStripProps) {
  return (
    <div className={cn("kpi-strip", className)}>
      {children}
    </div>
  );
}