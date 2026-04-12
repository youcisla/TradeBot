"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { useAnalytics } from "@/lib/swr";
import { fmtUsd } from "@/lib/format";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tooltipStyle}>
      <span style={tooltipLabel}>{label}</span>
      <span style={{ ...tooltipValue, color: payload[0].value >= 0 ? "var(--green)" : "var(--red)" }}>
        {fmtUsd(payload[0].value)}
      </span>
    </div>
  );
}

export default function EquityCurve() {
  const { data: analytics } = useAnalytics();

  const curve = useMemo(() => {
    if (!analytics?.dailyPnl) return [];
    let cumulative = 0;
    return analytics.dailyPnl.map((d) => {
      cumulative += d.pnl;
      return { date: d.date, pnl: cumulative };
    });
  }, [analytics]);

  if (!analytics) {
    return <div style={emptyStyle}>Loading…</div>;
  }

  if (curve.length === 0) {
    return <div style={emptyStyle}>No equity data yet</div>;
  }

  return (
    <div style={styles.wrapper}>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="var(--accent)" stopOpacity={0.3} />
              <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontFamily: "var(--font-mono)", fontSize: 9, fill: "var(--text-3)" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v) => fmtUsd(v, false).replace("$", "")}
            tick={{ fontFamily: "var(--font-mono)", fontSize: 9, fill: "var(--text-3)" }}
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="pnl"
            stroke="var(--accent)"
            strokeWidth={1.5}
            fill="url(#eqGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-4)",
  },
};

const emptyStyle: React.CSSProperties = {
  background: "var(--bg-2)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-md)",
  padding: "var(--space-4)",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
  color: "var(--text-3)",
  textAlign: "center",
};

const tooltipStyle: React.CSSProperties = {
  background: "var(--bg-3)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "6px 10px",
  display: "flex",
  flexDirection: "column",
  gap: 2,
};

const tooltipLabel: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 9,
  color: "var(--text-3)",
};

const tooltipValue: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  fontWeight: 700,
};
