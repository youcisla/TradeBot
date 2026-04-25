"use client";

import { useEffect, useState } from "react";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";

interface BotStatus {
  running?: boolean;
  version?: string;
  started_at?: string;
  uptime_hours?: number;
  broker?: string;
  mt5_server?: string;
  mt5_login?: string;
  account_type?: string;
  environment?: string;
  risk_per_trade_pct?: number;
  max_daily_loss_pct?: number;
  max_daily_loss_amount?: number;
  max_lot_size?: number;
  max_concurrent_trades?: number;
  primary_strategy?: string;
  lstm_lookback?: number;
  wfo_enabled?: boolean;
  wfo_period?: number;
  last_retrain?: string;
  crucix_enabled?: boolean;
  crucix_url?: string;
  crucix_last_signal?: string;
  news_filter_enabled?: boolean;
  symbols?: string[];
}

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div
      className="flex justify-between items-center py-3 border-b"
      style={{ borderColor: "var(--border)" }}
    >
      <span className="text-sm" style={{ color: "var(--text-2)" }}>{label}</span>
      <span
        className="text-sm text-right break-all tracking-wide"
        style={{
          color: "var(--text-1)",
          fontFamily: mono ? "var(--font-mono)" : undefined,
          maxWidth: "60%",
        }}
      >
        {value}
      </span>
    </div>
  );
}

const SYMBOLS_DEFAULT = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "USDCAD", "NZDUSD", "USDCHF"];

export default function SettingsPage() {
  const [status, setStatus] = useState<BotStatus>({});
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

  const isRunning = status.state === "running";

  return (
    <div className="flex flex-col gap-4">

      {/* Bot status banner */}
      <div
        className="flex items-center justify-between rounded-lg p-5"
        style={{
          background: isRunning ? "rgba(48,209,88,0.08)" : "rgba(255,69,58,0.08)",
          border: `1px solid ${isRunning ? "rgba(48,209,88,0.25)" : "rgba(255,69,58,0.25)"}`,
        }}
      >
        <div className="flex items-center gap-4">
          <span
            className="rounded-full flex-shrink-0"
            style={{
              width: 10, height: 10,
              background: isRunning ? "var(--green)" : "var(--red)",
              boxShadow: isRunning ? "0 0 8px var(--green)" : "none",
            }}
          />
          <div>
            <div className="font-bold text-base" style={{ color: "var(--text-1)" }}>
              PulseTrade TradingBot · {isRunning ? "Running" : "Stopped"}
            </div>
            <div className="font-mono text-xs mt-0.5" style={{ color: "var(--text-3)" }}>
              {status.version ? `v${status.version}` : ""} · Started {relTime(status.started_at)}
              {status.uptime_hours != null ? ` · ${status.uptime_hours.toFixed(1)}h uptime` : ""}
            </div>
          </div>
        </div>
        <StatusBadge
          label={isRunning ? "LIVE" : "OFFLINE"}
          variant={isRunning ? "success" : "danger"}
          pulse={isRunning}
        />
      </div>

      {/* 2-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Broker */}
        <Panel title="Broker Connection">
          <Row label="Broker"        value={status.broker ?? "PU Prime / MetaTrader 5"} />
          <Row label="Server"        value={status.mt5_server ?? "—"} mono />
          <Row label="Login"         value={status.mt5_login ? `****${String(status.mt5_login).slice(-4)}` : "—"} mono />
          <Row label="Account Type"  value={status.account_type ?? "—"} />
          <Row label="Environment"   value={status.environment ?? "production"} />
        </Panel>

        {/* Risk limits */}
        <Panel title="Risk Limits">
          <Row label="Risk per Trade"        value={status.risk_per_trade_pct != null ? `${status.risk_per_trade_pct}%` : "—"} mono />
          <Row label="Max Daily Loss %"       value={status.max_daily_loss_pct != null ? `${status.max_daily_loss_pct}%` : "—"} mono />
          <Row label="Max Daily Loss $"       value={status.max_daily_loss_amount != null ? `$${status.max_daily_loss_amount}` : "—"} mono />
          <Row label="Max Lot Size"           value={status.max_lot_size != null ? String(status.max_lot_size) : "—"} mono />
          <Row label="Max Concurrent Trades"  value={status.max_concurrent_trades != null ? String(status.max_concurrent_trades) : "—"} mono />
        </Panel>

        {/* Strategy */}
        <Panel title="Strategy & Model">
          <Row label="Active Strategy"  value={status.primary_strategy ?? "LSTM Neural"} />
          <Row label="LSTM Lookback"    value={status.lstm_lookback != null ? `${status.lstm_lookback} bars` : "—"} mono />
          <Row label="WFO Enabled"      value={status.wfo_enabled ? "Yes" : "No"} />
          <Row label="WFO Period"       value={status.wfo_period != null ? `${status.wfo_period}d` : "—"} mono />
          <Row label="Last Retrain"    value={relTime(status.last_retrain)} />
        </Panel>

        {/* Crucix */}
        <Panel title="Intelligence Suite">
          <div className="flex items-center gap-3 py-3 border-b" style={{ borderColor: "var(--border)" }}>
            <span
              className="rounded-full flex-shrink-0"
              style={{
                width: 7, height: 7,
                background: status.crucix_enabled ? "var(--green)" : "var(--text-3)",
                boxShadow: status.crucix_enabled ? "0 0 5px var(--green)" : "none",
              }}
            />
            <span
              className="text-sm font-semibold"
              style={{ color: status.crucix_enabled ? "var(--green)" : "var(--text-3)" }}
            >
              {status.crucix_enabled ? "Connected" : "Disabled"}
            </span>
          </div>
          <Row label="Endpoint"     value={status.crucix_url ?? "https://crucix-pi.vercel.app/"} mono />
          <Row label="Last Signal" value={relTime(status.crucix_last_signal)} />
          <Row label="News Filter" value={status.news_filter_enabled ? "Active" : "Off"} />
        </Panel>
      </div>

      {/* Symbols */}
      <Panel title="Configured Symbols">
        {loading ? (
          <span className="text-sm" style={{ color: "var(--text-3)" }}>Loading…</span>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(status.symbols ?? SYMBOLS_DEFAULT).map((sym) => (
              <span
                key={sym}
                className="rounded px-3 py-1.5 text-xs font-bold font-mono"
                style={{
                  background: "var(--bg-3)",
                  border: "1px solid var(--border)",
                  color: "var(--text-1)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.03em",
                }}
              >
                {sym}
              </span>
            ))}
          </div>
        )}
      </Panel>

      {/* Env note */}
      <div
        className="rounded-lg p-4"
        style={{
          background: "rgba(10,132,255,0.07)",
          border: "1px solid rgba(10,132,255,0.20)",
        }}
      >
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-2)", margin: 0 }}>
          <span className="font-bold" style={{ color: "var(--accent)" }}>Note:</span>{" "}
          All settings are read from the Python bot&apos;s environment variables and config files.
          To change settings, edit{" "}
          <code
            className="rounded px-1.5 py-0.5 text-xs"
            style={{
              fontFamily: "var(--font-mono)",
              background: "var(--bg-3)",
            }}
          >
            config/settings.py
          </code>{" "}
          and restart the bot.
        </p>
      </div>
    </div>
  );
}
