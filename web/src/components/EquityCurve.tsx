"use client";

import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";

interface EquityCurveProps {
  data: { day: string; pnl: number }[];
}

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;

interface TooltipPayload {
  value?: number;
  payload?: { cumulative?: number };
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const cum = payload[0]?.payload?.cumulative ?? 0;
  return (
    <div
      style={{
        background: "#2C2C2E",
        borderRadius: 8,
        padding: "8px 12px",
        fontFamily: FONT,
        fontSize: 12,
        color: "#FFFFFF",
        border: "none",
        boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ color: "rgba(235,235,245,0.6)", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontWeight: 700, color: cum >= 0 ? "#30D158" : "#FF453A" }}>
        {cum >= 0 ? "+" : ""}${cum.toFixed(2)}
      </div>
    </div>
  );
}

export default function EquityCurve({ data }: EquityCurveProps) {
  if (!data || data.length < 2) {
    return (
      <div
        style={{
          height: 180,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: FONT,
          fontSize: 14,
          color: "rgba(235,235,245,0.3)",
        }}
      >
        Not enough data
      </div>
    );
  }

  // Build cumulative series
  let cum = 0;
  const chartData = data.map((d) => {
    cum += Number(d.pnl);
    return { day: d.day, cumulative: parseFloat(cum.toFixed(2)) };
  });

  const lastVal = chartData[chartData.length - 1].cumulative;
  const isPositive = lastVal >= 0;
  const lineColor = isPositive ? "#30D158" : "#FF453A";
  const gradientId = isPositive ? "equityGradientGreen" : "equityGradientRed";

  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
            <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="day"
          tick={{ fill: "rgba(235,235,245,0.3)", fontSize: 11, fontFamily: FONT }}
          axisLine={false}
          tickLine={false}
          tickCount={4}
        />
        <YAxis
          tick={{ fill: "rgba(235,235,245,0.3)", fontSize: 11, fontFamily: FONT }}
          axisLine={false}
          tickLine={false}
          width={52}
          tickFormatter={(v: number) => `$${v}`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="cumulative"
          stroke={lineColor}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          dot={false}
          activeDot={{ r: 4, fill: lineColor, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
