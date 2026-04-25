"use client";

import { useRisk } from "@/lib/swr";
import { fmtPct, fmtUsd } from "@/lib/format";

export default function DrawdownGauge() {
  const { data: risk } = useRisk();

  if (!risk) {
    return <div style={cardStyle}>Loading…</div>;
  }

  const dailyPct  = risk.daily_loss_pct  ?? 0;
  const monthlyPct = risk.monthly_loss_pct ?? 0;
  const dailyMax   = risk.max_daily_loss_pct   ?? 0;
  const monthlyMax = risk.max_monthly_loss_pct ?? 0;
  const dailyPnl    = risk.daily_pnl    ?? 0;
  const monthlyPnl  = risk.monthly_pnl  ?? 0;

  function gauge(pct: number, label: string, color: string, max: number) {
    const clamped = Math.min(Math.abs(pct), 100);
    return (
      <div style={gaugeStyle}>
        <span style={gaugeLabel}>{label}</span>
        <div style={gaugeTrack}>
          <div
            style={{
              ...gaugeFill,
              width: `${clamped}%`,
              background: pct >= 80 ? "var(--red)" : pct >= 50 ? "var(--orange)" : color,
            }}
          />
        </div>
        <div style={gaugeFooter}>
          <span style={{ ...gaugePct, color: pct >= 80 ? "var(--red)" : pct >= 50 ? "var(--orange)" : color }}>
            {Math.min(Math.abs(pct), 999).toFixed(1)}%
          </span>
          <span style={gaugeLimit}>/ {max > 0 ? fmtPct(max / 100) : "—"}</span>
        </div>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <span style={cardTitle}>Drawdown Controls</span>
      <div style={gaugesStyle}>
        {gauge(dailyPct, "Daily Loss", "var(--green)", dailyMax)}
        {gauge(monthlyPct, "Monthly Loss", "var(--green)", monthlyMax)}
      </div>
      <div style={monthlyStyle}>
        <span style={monthlyLabel}>Monthly P&L</span>
        <span style={{ ...monthlyValue, color: monthlyPnl >= 0 ? "var(--green)" : "var(--red)" }}>
          {fmtUsd(monthlyPnl, false)}
        </span>
      </div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "var(--bg-2)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-md)",
  padding: "var(--space-4)",
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-3)",
};

const cardTitle: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 9,
  fontWeight: 700,
  color: "var(--text-3)",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
};

const gaugesStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-3)",
};

const gaugeStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 4,
};

const gaugeLabel: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  fontWeight: 600,
  color: "var(--text-2)",
};

const gaugeTrack: React.CSSProperties = {
  height: 6,
  background: "var(--bg-3)",
  borderRadius: 3,
  overflow: "hidden",
};

const gaugeFill: React.CSSProperties = {
  height: "100%",
  borderRadius: 3,
  transition: "width 0.4s, background 0.3s",
};

const gaugeFooter: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
};

const gaugePct: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  fontWeight: 700,
};

const gaugeLimit: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  color: "var(--text-3)",
};

const monthlyStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  paddingTop: "var(--space-2)",
  borderTop: "1px solid var(--border)",
};

const monthlyLabel: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 10,
  fontWeight: 600,
  color: "var(--text-2)",
};

const monthlyValue: React.CSSProperties = {
  fontFamily: "var(--font-mono)",
  fontSize: 14,
  fontWeight: 700,
};
