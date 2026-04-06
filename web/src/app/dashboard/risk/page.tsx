"use client";

import { useEffect, useState } from "react";

//  Types 

interface RiskData {
  equity?: number;
  balance?: number;
  daily_pnl?: number;
  daily_pnl_pct?: number;
  monthly_pnl?: number;
  monthly_pnl_pct?: number;
  max_daily_loss?: number;
  max_daily_loss_pct?: number;
  max_total_drawdown?: number;
  max_total_drawdown_pct?: number;
  risk_per_trade_pct?: number;
  max_lot_size?: number;
  max_concurrent_trades?: number;
  open_trades?: number;
  emergency_stop?: boolean;
  emergency_reason?: string;
  wfo_enabled?: boolean;
  wfo_period?: number;
  last_retrain?: string;
}

//  Helpers 

function fmtUsd(v?: number): string {
  if (v == null || isNaN(v)) return "—";
  const abs = Math.abs(v);
  const s   = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + s;
}

function pnlColor(v?: number): string {
  if (v == null) return "var(--text-muted)";
  return v > 0 ? "var(--buy)" : v < 0 ? "var(--sell)" : "var(--text-muted)";
}

function limitBar(value: number, max: number, good?: boolean): { used: number; color: string } {
  const pct = max !== 0 ? Math.min(Math.abs(value / max), 1) * 100 : 0;
  const color = pct > 90 ? "var(--sell)" : pct > 60 ? "var(--health-warn)" : (good ? "var(--buy)" : "var(--accent)");
  return { used: pct, color };
}

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const h  = Math.floor(ms / 3_600_000);
  if (h < 1)  return `${Math.floor(ms / 60_000)}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

//  Page 

export default function RiskPage() {
  const [data,    setData]    = useState<RiskData>({});
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/risk");
        if (!r.ok) throw new Error();
        const d = await r.json();
        setData(d);
        setError(false);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    load();
    const t = setInterval(load, 15_000);
    return () => clearInterval(t);
  }, []);

  const MONO = "var(--font-mono-stack)";
  const card: React.CSSProperties = {
    background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10,
  };
  const sectionLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
    letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 16,
  };

  // Daily loss limit bar
  const dailyBar   = limitBar(data.daily_pnl ?? 0, data.max_daily_loss ?? 0);
  const tradCntBar = limitBar(data.open_trades ?? 0, data.max_concurrent_trades ?? 0);

  return (
    <>
      {/*  Emergency banner  */}
      {data.emergency_stop && (
        <div style={{
          marginBottom: 20, padding: "14px 20px", borderRadius: 12,
          background: "var(--sell-dim)", border: "1px solid rgba(239,68,68,0.35)",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          <span style={{ fontSize: 18, fontFamily: "Material Symbols Outlined", color: "var(--sell)" }}>emergency</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--sell)", letterSpacing: -0.2 }}>EMERGENCY STOP ACTIVE</div>
            {data.emergency_reason && (
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{data.emergency_reason}</div>
            )}
          </div>
        </div>
      )}

      {/*  Equity / Balance strip  */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Equity",          value: fmtUsd(data.equity),       color: "var(--text-primary)" },
          { label: "Balance",         value: fmtUsd(data.balance),      color: "var(--text-primary)" },
          { label: "Daily P&L",       value: data.daily_pnl != null ? `${fmtUsd(data.daily_pnl)} (${(data.daily_pnl_pct ?? 0).toFixed(2)}%)` : "—", color: pnlColor(data.daily_pnl) },
          { label: "Monthly P&L",     value: data.monthly_pnl != null ? `${fmtUsd(data.monthly_pnl)} (${(data.monthly_pnl_pct ?? 0).toFixed(2)}%)` : "—", color: pnlColor(data.monthly_pnl) },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ ...card, padding: "18px 20px" }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color, fontFamily: MONO, letterSpacing: -0.5 }}>
              {loading ? "—" : value}
            </div>
          </div>
        ))}
      </div>

      {/*  Loss limiter gauges  */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>

        {/* Daily drawdown */}
        <div style={{ ...card, padding: "20px" }}>
          <div style={sectionLabel}>Daily Loss Limit</div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: pnlColor(data.daily_pnl), fontFamily: MONO }}>
              {fmtUsd(data.daily_pnl)}
            </span>
            <span style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: MONO }}>
              / {fmtUsd(data.max_daily_loss)}
            </span>
          </div>
          <div style={{ height: 8, background: "var(--surface-3)", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
            <div style={{ height: "100%", width: `${dailyBar.used}%`, background: dailyBar.color, borderRadius: 4, transition: "width 0.3s" }} />
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: MONO }}>
            {dailyBar.used.toFixed(1)}% of daily limit consumed
          </div>
          {data.max_daily_loss_pct != null && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Cap: {data.max_daily_loss_pct.toFixed(2)}% of balance
            </div>
          )}
        </div>

        {/* Total drawdown */}
        <div style={{ ...card, padding: "20px" }}>
          <div style={sectionLabel}>Max Total Drawdown</div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: "var(--health-warn)", fontFamily: MONO }}>
              {data.max_total_drawdown != null ? fmtUsd(data.max_total_drawdown) : "—"}
            </span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {data.max_total_drawdown_pct != null ? `${data.max_total_drawdown_pct.toFixed(2)}% limit` : "not set"}
            </span>
          </div>
          <div style={{ height: 8, background: "var(--surface-3)", borderRadius: 4, overflow: "hidden", marginBottom: 6 }}>
            <div style={{ height: "100%", width: "0%", background: "var(--health-warn)", borderRadius: 4 }} />
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: MONO }}>Absolute drawdown ceiling</div>
        </div>
      </div>

      {/*  Bottom row: position sizing + WFO + open trades  */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>

        {/* Position sizing */}
        <div style={{ ...card, padding: "20px" }}>
          <div style={sectionLabel}>Position Sizing</div>
          {[
            { label: "Risk per Trade",          value: data.risk_per_trade_pct != null ? `${data.risk_per_trade_pct.toFixed(2)}%` : "—" },
            { label: "Max Lot Size",            value: data.max_lot_size != null ? String(data.max_lot_size) : "—" },
            { label: "Max Concurrent Trades",   value: data.max_concurrent_trades != null ? String(data.max_concurrent_trades) : "—" },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", fontFamily: MONO }}>{value}</span>
            </div>
          ))}
        </div>

        {/* Open positions */}
        <div style={{ ...card, padding: "20px" }}>
          <div style={sectionLabel}>Open Positions</div>
          <div style={{ textAlign: "center", padding: "10px 0 6px" }}>
            <div style={{ fontSize: 48, fontWeight: 700, color: "var(--accent)", fontFamily: MONO, lineHeight: 1 }}>
              {data.open_trades ?? 0}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
              of {data.max_concurrent_trades ?? "—"} allowed
            </div>
          </div>
          <div style={{ height: 8, background: "var(--surface-3)", borderRadius: 4, overflow: "hidden", margin: "12px 0 8px" }}>
            <div style={{ height: "100%", width: `${tradCntBar.used}%`, background: tradCntBar.color, borderRadius: 4, transition: "width 0.3s" }} />
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: MONO, textAlign: "center" }}>
            {tradCntBar.used.toFixed(0)}% slot utilisation
          </div>
        </div>

        {/* WFO status */}
        <div style={{ ...card, padding: "20px" }}>
          <div style={sectionLabel}>Walk-Forward Optimisation</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: data.wfo_enabled ? "var(--buy)" : "var(--text-muted)",
              boxShadow: data.wfo_enabled ? "0 0 6px var(--buy)" : "none",
            }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: data.wfo_enabled ? "var(--buy)" : "var(--text-muted)" }}>
              {data.wfo_enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          {[
            { label: "Retrain Period", value: data.wfo_period != null ? `${data.wfo_period}d` : "—" },
            { label: "Last Retrain",   value: relTime(data.last_retrain) },
          ].map(({ label, value }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border-subtle)" }}>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", fontFamily: MONO }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}