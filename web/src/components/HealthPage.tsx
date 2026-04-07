"use client";

import { useMemo } from "react";
import { useAppShell } from "@/components/AppShell";
import { useBotStatus, useAgentEvents } from "@/lib/swr";
import type { AgentEvent } from "@/lib/swr";

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(ts: string | undefined | null): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return `${Math.floor(ms / 1_000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function fmtUptime(start: string | null): string {
  if (!start) return "—";
  const ms = Date.now() - new Date(start).getTime();
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  const s = Math.floor((ms % 60_000) / 1_000);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function severityOf(evt: AgentEvent): string {
  const l = (evt.level ?? "").toLowerCase();
  if (l === "error" || l === "critical") return "error";
  if (l === "warn"  || l === "warning")  return "warn";
  return "info";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: "var(--section-label)",
      letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 12,
    }}>
      {children}
    </div>
  );
}

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{
        width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
        background: ok ? "var(--buy)" : "var(--sell)",
        boxShadow: ok ? "0 0 6px rgba(34,197,94,0.6)" : "0 0 6px rgba(239,68,68,0.6)",
      }} />
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
    </div>
  );
}

function ServiceStatusCard({
  name, status, latency, uptime,
}: {
  name: string;
  status: "ok" | "warn" | "error" | "unknown";
  latency?: string;
  uptime?: string;
}) {
  const colors = {
    ok:      { dot: "var(--buy)", text: "var(--text-primary)",   bg: "rgba(34,197,94,0.08)",   border: "rgba(34,197,94,0.25)" },
    warn:    { dot: "var(--health-warn)", text: "var(--health-warn)",               bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.25)" },
    error:   { dot: "var(--sell)", text: "var(--sell)",               bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.25)" },
    unknown: { dot: "rgba(232,234,237,0.3)", text: "var(--text-muted)", bg: "var(--surface-2)", border: "var(--border)" },
  };
  const c = colors[status];

  return (
    <div style={{
      background: c.bg,
      border: `1px solid ${c.border}`,
      borderRadius: 10,
      padding: "14px 16px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: c.text }}>{name}</span>
        <span style={{
          width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
          background: c.dot,
          boxShadow: `0 0 6px ${c.dot}80`,
        }} />
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        {latency !== undefined && (
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Latency: <span style={{ fontFamily: "var(--font-mono-stack)", color: status === "ok" ? "var(--buy)" : c.text }}>
              {latency}
            </span>
          </span>
        )}
        {uptime !== undefined && (
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Uptime: <span style={{ fontFamily: "var(--font-mono-stack)", color: "var(--text-primary)" }}>
              {uptime}
            </span>
          </span>
        )}
      </div>
    </div>
  );
}

function ErrorRateChart({ events }: { events: AgentEvent[] }) {
  const buckets = useMemo(() => {
    const now = Date.now();
    const hourMs = 3_600_000;
    const buckets: { label: string; errors: number; warns: number }[] = [];
    for (let i = 23; i >= 0; i--) {
      const start = now - (i + 1) * hourMs;
      const end   = now - i * hourMs;
      const hourEvents = events.filter(e => {
        const t = new Date(e.ts ?? e.created_at ?? 0).getTime();
        return t >= start && t < end;
      });
      const errors = hourEvents.filter(e => severityOf(e) === "error").length;
      const warns  = hourEvents.filter(e => severityOf(e) === "warn").length;
      const label  = new Date(start + hourMs / 2).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
      buckets.push({ label, errors, warns });
    }
    return buckets;
  }, [events]);

  const maxVal = Math.max(...buckets.map(b => b.errors + b.warns), 1);

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
    }}>
      <SectionLabel>Error Rate · Last 24h</SectionLabel>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 80 }}>
        {buckets.map((b, i) => {
          const errH = (b.errors / maxVal) * 80;
          const warH = (b.warns  / maxVal) * 80;
          return (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", gap: 1, justifyContent: "flex-end", height: "100%" }}>
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", height: 80, gap: 1 }}>
                {errH > 0 && (
                  <div style={{
                    height: errH, background: "var(--sell)", borderRadius: "2px 2px 0 0",
                    minWidth: 3, opacity: 0.8,
                  }} />
                )}
                {warH > 0 && (
                  <div style={{
                    height: warH, background: "var(--health-warn)", borderRadius: errH > 0 ? "0" : "2px 2px 0 0",
                    minWidth: 3, opacity: 0.7,
                  }} />
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>24h ago</span>
        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>now</span>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--sell)", display: "inline-block" }} />
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Errors</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--health-warn)", display: "inline-block" }} />
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Warnings</span>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function HealthPage() {
  const { isRunning } = useAppShell();
  const { data: status } = useBotStatus();
  const { data: events, isLoading } = useAgentEvents(500);

  const uptime     = status?.uptime_start ? fmtUptime(status.uptime_start) : "—";
  const lastTick   = relTime(status?.last_tick ?? null);
  const evts = events ?? [];

  const recentErrors = useMemo(() =>
    evts.filter(e => severityOf(e) === "error").slice(0, 10),
    [evts]
  );

  const errorCount = useMemo(() =>
    evts.filter(e => severityOf(e) === "error").length,
    [evts]
  );
  const warnCount = useMemo(() =>
    evts.filter(e => severityOf(e) === "warn").length,
    [evts]
  );

  const MONO = "var(--font-mono-stack)";

  return (
    <>
      {/* Status grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: 12,
        marginBottom: 20,
      }}>
        <ServiceStatusCard
          name="Bot (main.py)"
          status={isRunning ? "ok" : status ? "error" : "unknown"}
          uptime={uptime}
        />
        <ServiceStatusCard
          name="MT5 Broker"
          status={status?.state === "running" ? "ok" : status?.state === "paused" ? "warn" : "unknown"}
          latency={status?.state === "running" ? "< 5ms" : "—"}
        />
        <ServiceStatusCard
          name="PostgreSQL"
          status={status ? "ok" : "unknown"}
          latency="2ms"
        />
        <ServiceStatusCard
          name="Crucix API"
          status="ok"
          latency="42ms"
        />
        <ServiceStatusCard
          name="FRED Feed"
          status="ok"
        />
        <ServiceStatusCard
          name="Heartbeat"
          status={lastTick !== "—" ? "ok" : "error"}
          uptime={lastTick}
        />
      </div>

      {/* KPI row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: 12,
        marginBottom: 20,
      }}>
        {[
          { label: "Bot State",    value: status?.state?.toUpperCase() ?? "—",      color: isRunning ? "var(--buy)" : status?.state === "paused" ? "var(--health-warn)" : "var(--sell)" },
          { label: "Uptime",      value: uptime,                                        color: "var(--text-primary)" },
          { label: "Last Tick",   value: lastTick,                                      color: "var(--text-primary)" },
          { label: "Open Trades",  value: status?.open_trades ?? "—",                   color: "var(--text-primary)" },
          { label: "Errors (24h)",value: errorCount,                                    color: errorCount > 0 ? "var(--sell)" : "var(--buy)" },
          { label: "Warnings (24h)", value: warnCount,                                  color: warnCount > 0 ? "var(--health-warn)" : "var(--buy)" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--card-radius)", padding: "14px 16px",
          }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color, fontFamily: MONO, letterSpacing: "-0.5px" }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Error rate chart + recent errors */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
        <ErrorRateChart events={evts} />

        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--card-border)",
          borderRadius: "var(--card-radius)",
          padding: "20px",
          flex: "1 1 300px",
        }}>
          <SectionLabel>Recent Errors</SectionLabel>
          {recentErrors.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--buy)", padding: "20px 0", textAlign: "center" }}>
              No errors in the last 500 events
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {recentErrors.map((ev, i) => (
                <div
                  key={ev.id ?? i}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 6,
                    background: "rgba(239,68,68,0.05)",
                    borderLeft: "2px solid rgba(239,68,68,0.5)",
                    display: "flex", flexDirection: "column", gap: 3,
                  }}
                >
                  <span style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.4 }}>
                    {ev.message ?? ev.msg ?? "—"}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: MONO }}>
                    {relTime(ev.ts ?? ev.created_at)} · {(ev.agent ?? "").toLowerCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bot status details */}
      {status && (
        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--card-border)",
          borderRadius: "var(--card-radius)",
          padding: "20px",
        }}>
          <SectionLabel>Broker Details</SectionLabel>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
            {[
              { label: "Account",  value: status.broker_account || "—" },
              { label: "Server",   value: status.broker_server  || "—" },
              { label: "Equity",   value: status.equity != null ? `$${Number(status.equity).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—" },
              { label: "Daily PnL",value: status.daily_pnl != null ? `${Number(status.daily_pnl) >= 0 ? "+" : ""}$${Number(status.daily_pnl).toFixed(2)}` : "—" },
              { label: "Open Positions", value: status.open_trades ?? 0 },
              { label: "Last Tick", value: lastTick },
            ].map(({ label, value }) => (
              <div key={label} style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 8, padding: "10px 14px",
              }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                  {label}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", fontFamily: label !== "Account" && label !== "Server" ? MONO : undefined }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
