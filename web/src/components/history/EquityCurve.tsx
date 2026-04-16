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
    <div
      className="rounded px-2 py-1.5 flex flex-col gap-0.5"
      style={{ background: "var(--bg-3)", border: "1px solid var(--border)" }}
    >
      <span className="font-mono text-[9px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
        {label}
      </span>
      <span
        className="font-mono text-xs font-bold"
        style={{ fontFamily: "var(--font-mono)", color: payload[0].value >= 0 ? "var(--green)" : "var(--red)" }}
      >
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
    return (
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4 text-center">
        <span className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          Loading…
        </span>
      </div>
    );
  }

  if (curve.length === 0) {
    return (
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4 text-center">
        <span className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          No equity data yet
        </span>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4">
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
