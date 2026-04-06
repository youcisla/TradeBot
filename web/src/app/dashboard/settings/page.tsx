"use client";

import { useEffect, useState } from "react";

//  Types 

interface Settings {
  // Broker
  broker_name?: string;
  mt5_server?: string;
  mt5_login?: string;
  mt5_account_type?: string;
  // Trading
  risk_per_trade?: number;
  max_daily_loss_pct?: number;
  max_daily_loss_amount?: number;
  max_lot_size?: number;
  max_concurrent_trades?: number;
  // Symbols
  symbols?: string[];
  // Strategy
  primary_strategy?: string;
  lstm_lookback?: number;
  // Crucix
  crucix_enabled?: boolean;
  crucix_url?: string;
}

interface BotStatus {
  running?: boolean;
  version?: string;
  started_at?: string;
  uptime_hours?: number;
}

//  Helpers 

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const m  = Math.floor(ms / 60000);
  if (m < 60)   return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)   return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

//  Sub-component: Row 

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  const MONO = '"SF Mono", SFMono-Regular, ui-monospace, monospace';
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
      <span style={{ fontSize: 13, color: "rgba(232,234,237,0.50)" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: "#E8EAED", fontFamily: mono ? MONO : undefined, textAlign: "right", maxWidth: "60%", wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}

//  Page 

export default function SettingsPage() {
  const [status,  setStatus]  = useState<BotStatus>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/status");
        const d = await r.json();
        setStatus(d ?? {});
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 20_000);
    return () => clearInterval(t);
  }, []);

  const MONO = '"SF Mono", SFMono-Regular, ui-monospace, monospace';
  const card: React.CSSProperties = {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 12, padding: "20px",
  };
  const sectionLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.40)",
    letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 14,
  };

  const isRunning = !!(status as any)?.running ?? false;

  return (
    <>
      {/*  Bot status banner  */}
      <div style={{
        ...card,
        marginBottom: 20,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: isRunning ? "rgba(52,199,89,0.08)" : "rgba(255,59,48,0.08)",
        border: `1px solid ${isRunning ? "rgba(52,199,89,0.25)" : "rgba(255,59,48,0.25)"}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%",
            background: isRunning ? "#34C759" : "#FF3B30",
            boxShadow: isRunning ? "0 0 8px #34C759" : "none",
            flexShrink: 0,
          }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#E8EAED" }}>
              PulseTrade TradingBot · {isRunning ? "Running" : "Stopped"}
            </div>
            <div style={{ fontSize: 12, color: "rgba(232,234,237,0.40)", marginTop: 2 }}>
              {(status as any)?.version ? `v${(status as any).version}` : ""} · Started {relTime((status as any)?.started_at)}
              {(status as any)?.uptime_hours != null ? ` · ${(status as any).uptime_hours.toFixed(1)}h uptime` : ""}
            </div>
          </div>
        </div>
        <span style={{
          fontSize: 11, fontWeight: 700,
          color: isRunning ? "#34C759" : "#FF3B30",
          background: isRunning ? "rgba(52,199,89,0.15)" : "rgba(255,59,48,0.15)",
          padding: "4px 12px", borderRadius: 6, letterSpacing: 0.4, textTransform: "uppercase",
        }}>
          {isRunning ? "LIVE" : "OFFLINE"}
        </span>
      </div>

      {/*  2-column layout  */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Broker */}
        <div style={card}>
          <div style={sectionLabel}>Broker Connection</div>
          <Row label="Broker"       value={(status as any)?.broker ?? "PU Prime / MetaTrader 5"} />
          <Row label="Server"       value={(status as any)?.mt5_server ?? "—"} mono />
          <Row label="Login"        value={(status as any)?.mt5_login ? `****${String((status as any).mt5_login).slice(-4)}` : "—"} mono />
          <Row label="Account Type" value={(status as any)?.account_type ?? "—"} />
          <Row label="Environment"  value={(status as any)?.environment ?? process.env.NODE_ENV ?? "—"} />
        </div>

        {/* Risk limits (read-only from config) */}
        <div style={card}>
          <div style={sectionLabel}>Risk Limits</div>
          <Row label="Risk per Trade"           value={(status as any)?.risk_per_trade_pct != null ? `${(status as any).risk_per_trade_pct}%` : "—"} mono />
          <Row label="Max Daily Loss %"         value={(status as any)?.max_daily_loss_pct != null ? `${(status as any).max_daily_loss_pct}%` : "—"} mono />
          <Row label="Max Daily Loss $"         value={(status as any)?.max_daily_loss_amount != null ? `$${(status as any).max_daily_loss_amount}` : "—"} mono />
          <Row label="Max Lot Size"             value={(status as any)?.max_lot_size != null ? String((status as any).max_lot_size) : "—"} mono />
          <Row label="Max Concurrent Trades"    value={(status as any)?.max_concurrent_trades != null ? String((status as any).max_concurrent_trades) : "—"} mono />
        </div>
      </div>

      {/*  Second row  */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Strategy */}
        <div style={card}>
          <div style={sectionLabel}>Strategy &amp; Model</div>
          <Row label="Active Strategy"   value={(status as any)?.primary_strategy ?? "LSTM Neural"} />
          <Row label="LSTM Lookback"     value={(status as any)?.lstm_lookback != null ? `${(status as any).lstm_lookback} bars` : "—"} mono />
          <Row label="WFO Enabled"       value={(status as any)?.wfo_enabled ? "Yes" : "No"} />
          <Row label="WFO Period"        value={(status as any)?.wfo_period != null ? `${(status as any).wfo_period}d` : "—"} mono />
          <Row label="Last Retrain"      value={relTime((status as any)?.last_retrain)} />
        </div>

        {/* Crucix */}
        <div style={card}>
          <div style={sectionLabel}>Intelligence Suite</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "11px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: (status as any)?.crucix_enabled ? "#34C759" : "rgba(232,234,237,0.20)",
              boxShadow: (status as any)?.crucix_enabled ? "0 0 5px #34C759" : "none",
            }} />
            <span style={{ fontSize: 13, fontWeight: 600, color: (status as any)?.crucix_enabled ? "#34C759" : "rgba(232,234,237,0.35)" }}>
              {(status as any)?.crucix_enabled ? "Connected" : "Disabled"}
            </span>
          </div>
          <Row label="Endpoint" value={(status as any)?.crucix_url ?? "http://localhost:3001"} mono />
          <Row label="Last Signal" value={relTime((status as any)?.crucix_last_signal)} />
          <Row label="News Filter" value={(status as any)?.news_filter_enabled ? "Active" : "Off"} />
        </div>
      </div>

      {/*  Symbols  */}
      <div style={card}>
        <div style={sectionLabel}>Configured Symbols</div>
        {loading ? (
          <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)" }}>Loading…</div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {((status as any)?.symbols ?? ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "USDCAD", "NZDUSD", "USDCHF"]).map((sym: string) => (
              <span key={sym} style={{
                padding: "5px 12px", borderRadius: 6,
                background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.10)",
                fontSize: 12, fontWeight: 600, color: "#E8EAED", fontFamily: MONO, letterSpacing: 0.3,
              }}>
                {sym}
              </span>
            ))}
          </div>
        )}
      </div>

      {/*  Env note  */}
      <div style={{ marginTop: 20, padding: "14px 18px", borderRadius: 10, background: "rgba(10,132,255,0.07)", border: "1px solid rgba(10,132,255,0.20)" }}>
        <div style={{ fontSize: 12, color: "rgba(232,234,237,0.50)", lineHeight: 1.6 }}>
          <span style={{ fontWeight: 700, color: "#0A84FF" }}>Note:</span> All settings are read from the Python bot&apos;s environment variables and config files.
          To change settings, edit <code style={{ fontFamily: MONO, fontSize: 11, background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 4 }}>config/settings.py</code> and restart the bot.
        </div>
      </div>
    </>
  );
}