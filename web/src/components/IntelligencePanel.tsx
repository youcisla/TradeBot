"use client";

import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// ── Types ─────────────────────────────────────────────────────────────────────

interface AlertEvent {
  id: number;
  agent: string;
  level: string;
  message: string;
  created_at: string;
}

interface Intelligence {
  session: string;
  sessionLabel: string;
  nextSession: string;
  nextSessionIn: number;
  spreadCondition: string;
  spreadPips: number;
  marketRegime: string;
  vix: number;
  dailyLossPct: number;
  equityDrawdownPct: number;
  todayPnl: number;
  winRate: number;
  tradesToday: number;
  openTrades: number;
  totalTrades: number;
  recentAlerts: AlertEvent[];
  alertCount: number;
  intelligence: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number): string {
  const f = Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "+$") + f;
}

function fmtTime(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false, timeZone: "Europe/Paris",
    });
  } catch { return "—"; }
}

// ── Session config ────────────────────────────────────────────────────────────

const SESSION_COLORS: Record<string, string> = {
  asian:   "#9333EA",
  london:  "#2563EB",
  overlap: "#16A34A",
  newyork: "#D97706",
};

function SessionChip({ session, label, next, nextIn }: {
  session: string; label: string; next: string; nextIn: number;
}) {
  const color = SESSION_COLORS[session] ?? "#6B7280";
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 2,
      background: `${color}14`, border: `1px solid ${color}40`,
      borderRadius: 8, padding: "8px 12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: color, display: "inline-block",
          boxShadow: `0 0 6px ${color}`,
        }} />
        <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: "'IBM Plex Mono', monospace" }}>
          {label}
        </span>
      </div>
      <div style={{ fontSize: 10, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace" }}>
        Next: {next} in ~{nextIn}m
      </div>
    </div>
  );
}

// ── Spread indicator ─────────────────────────────────────────────────────────

const SPREAD_COLORS: Record<string, string> = {
  low:    "#16A34A",
  normal: "#00D2FD",
  high:   "#D97706",
  extreme: "#DC2626",
};

function SpreadStrip({ condition, pips }: { condition: string; pips: number | undefined }) {
  const color = SPREAD_COLORS[condition] ?? "#6B7280";
  const isExtreme = condition === "extreme";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "6px 12px",
      background: isExtreme ? "rgba(220,38,38,0.12)" : `${color}14`,
      border: `1px solid ${color}40`,
      borderRadius: 8,
      animation: isExtreme ? "spreadPulse 1.5s ease-in-out infinite" : undefined,
    }}>
      <style>{`@keyframes spreadPulse { 0%,100%{opacity:1} 50%{opacity:0.6} }`}</style>
      <span style={{ fontSize: 11, fontWeight: 700, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace" }}>
        SPREAD
      </span>
      <span style={{
        fontSize: 13, fontWeight: 700, color,
        fontFamily: "'IBM Plex Mono', monospace",
      }}>
        {(pips ?? 0).toFixed(1)} pips
      </span>
      <span style={{
        fontSize: 10, fontWeight: 600, color,
        background: `${color}28`, borderRadius: 4, padding: "1px 6px",
        fontFamily: "'IBM Plex Mono', monospace",
        textTransform: "uppercase", letterSpacing: "0.05em",
      }}>
        {condition}
      </span>
    </div>
  );
}

// ── Regime badge ──────────────────────────────────────────────────────────────

const REGIME_META: Record<string, { label: string; color: string }> = {
  high_volume: { label: "HIGH VOLUME", color: "#16A34A" },
  volatile:    { label: "VOLATILE",    color: "#DC2626" },
  quiet:        { label: "QUIET",        color: "#9333EA" },
  normal:       { label: "NORMAL",       color: "#6B7280" },
};

function RegimeBadge({ regime }: { regime: string }) {
  const meta = REGIME_META[regime] ?? REGIME_META.normal;
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      background: `${meta.color}18`, border: `1px solid ${meta.color}40`,
      borderRadius: 6, padding: "3px 10px",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: meta.color, display: "inline-block",
      }} />
      <span style={{
        fontSize: 10, fontWeight: 700, color: meta.color,
        fontFamily: "'IBM Plex Mono', monospace",
        letterSpacing: "0.06em",
      }}>
        {meta.label}
      </span>
    </div>
  );
}

// ── Mini gauge ───────────────────────────────────────────────────────────────

function MiniGauge({ label, value, max, color }: {
  label: string; value: number; max: number; color: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {label}
        </span>
        <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: "'IBM Plex Mono', monospace" }}>
          {value.toFixed(1)}%
        </span>
      </div>
      <div style={{ height: 4, background: "#F3F4F6", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`, background: color,
          borderRadius: 2, transition: "width 0.5s ease",
        }} />
      </div>
    </div>
  );
}

// ── Alert row ────────────────────────────────────────────────────────────────

function AlertRow({ ev }: { ev: AlertEvent }) {
  const isError = ev.level === "error" || ev.level === "critical";
  const bg = isError ? "rgba(220,38,38,0.07)" : "rgba(217,119,6,0.07)";
  const accent = isError ? "#DC2626" : "#D97706";
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 6,
      padding: "5px 8px", background: bg,
      borderRadius: 4, borderLeft: `2px solid ${accent}`,
    }}>
      <span style={{
        fontSize: 9, fontWeight: 700, color: accent,
        fontFamily: "'IBM Plex Mono', monospace",
        textTransform: "uppercase", letterSpacing: "0.04em",
        flexShrink: 0, minWidth: 52,
      }}>
        {ev.agent}
      </span>
      <span style={{
        fontSize: 10, color: "#374151", fontFamily: "'IBM Plex Mono', monospace",
        flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {String(ev.message ?? "").slice(0, 60)}
      </span>
      <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace", flexShrink: 0 }}>
        {fmtTime(ev.created_at)}
      </span>
    </div>
  );
}

// ── KPI chip ─────────────────────────────────────────────────────────────────

function KpiChip({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 2,
      background: "#FAFAFA", borderRadius: 6, padding: "6px 10px",
    }}>
      <span style={{ fontSize: 9, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace", textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {label}
      </span>
      <span style={{ fontSize: 13, fontWeight: 700, color: color ?? "#111827", fontFamily: "'IBM Plex Mono', monospace" }}>
        {value}
      </span>
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function IntelligencePanel() {
  const { data } = useSWR<Intelligence>("/api/intelligence", fetcher, {
    refreshInterval: 8_000,
    revalidateOnFocus: true,
    keepPreviousData: true,
    errorRetryCount: 3,
  });

  if (!data) {
    return (
      <aside style={styles.panel}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1 }}>
          <span style={{ fontSize: 12, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace" }}>
            Loading intelligence…
          </span>
        </div>
      </aside>
    );
  }

  const spreadColor = SPREAD_COLORS[data.spreadCondition] ?? "#6B7280";
  const pnlColor = data.todayPnl >= 0 ? "#16A34A" : "#DC2626";

  return (
    <aside style={styles.panel}>
      <style>{`
        @keyframes feedPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>

      {/* ── Session ── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Session</div>
        <SessionChip
          session={data.session}
          label={data.sessionLabel}
          next={data.nextSession}
          nextIn={data.nextSessionIn}
        />
      </div>

      {/* ── Spread ── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Spread</div>
        <SpreadStrip condition={data.spreadCondition} pips={data.spreadPips} />
      </div>

      {/* ── Regime + VIX ── */}
      <div style={styles.section}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <RegimeBadge regime={data.marketRegime} />
          {data.vix > 0 && (
            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              background: data.vix > 30 ? "rgba(220,38,38,0.1)" : "rgba(37,99,235,0.1)",
              border: `1px solid ${data.vix > 30 ? "rgba(220,38,38,0.3)" : "rgba(37,99,235,0.3)"}`,
              borderRadius: 6, padding: "3px 8px",
            }}>
              <span style={{ fontSize: 10, color: "#9CA3AF", fontFamily: "'IBM Plex Mono', monospace" }}>VIX</span>
              <span style={{
                fontSize: 11, fontWeight: 700,
                color: data.vix > 30 ? "#DC2626" : "#2563EB",
                fontFamily: "'IBM Plex Mono', monospace",
              }}>
                {data.vix.toFixed(1)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Risk gauges ── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Risk Exposure</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <MiniGauge
            label="Daily Loss"
            value={(data.dailyLossPct ?? 0) * 100}
            max={5}
            color="#DC2626"
          />
          <MiniGauge
            label="Equity Drawdown"
            value={(data.equityDrawdownPct ?? 0) * 100}
            max={20}
            color="#9333EA"
          />
        </div>
      </div>

      {/* ── KPIs ── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Today</div>
        <div style={styles.kpiGrid}>
          <KpiChip
            label="P&L"
            value={fmtUsd(data.todayPnl)}
            color={pnlColor}
          />
          <KpiChip
            label="Win%"
            value={data.tradesToday > 0 ? `${data.winRate.toFixed(0)}%` : "—"}
            color={data.winRate >= 50 ? "#16A34A" : "#DC2626"}
          />
          <KpiChip
            label="Trades"
            value={String(data.tradesToday)}
          />
          <KpiChip
            label="Open"
            value={String(data.openTrades)}
            color={data.openTrades > 0 ? "#D97706" : undefined}
          />
        </div>
      </div>

      {/* ── Alerts ── */}
      {data.alertCount > 0 && (
        <div style={{ ...styles.section, background: "rgba(220,38,38,0.04)" }}>
          <div style={{ ...styles.sectionLabel, color: "#DC2626" }}>
            Active Alerts ({data.alertCount})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {data.recentAlerts.slice(0, 5).map((ev) => (
              <AlertRow key={ev.id} ev={ev} />
            ))}
          </div>
        </div>
      )}

      {/* ── AI Insight ── */}
      <div style={{ ...styles.section, background: "linear-gradient(135deg, rgba(13,17,23,0.95) 0%, rgba(19,24,32,0.98) 100%)", borderRadius: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#00fd87", fontFamily: "'IBM Plex Mono', monospace" }}>
            INSIGHT
          </span>
          <span style={{
            width: 6, height: 6, borderRadius: "50%", background: "#00fd87",
            display: "inline-block",
            boxShadow: "0 0 5px #00fd87",
            animation: "feedPulse 2s ease-in-out infinite",
          }} />
        </div>
        <p style={{
          fontSize: 11, color: "rgba(229,239,253,0.82)",
          fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.6,
          margin: 0,
        }}>
          {data.intelligence}
        </p>
      </div>
    </aside>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: "fixed",
    top: 48,
    right: 0,
    bottom: 32,
    width: 264,
    background: "#FFFFFF",
    borderLeft: "1px solid #F0F0F0",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    zIndex: 90,
    flexShrink: 0,
  },
  section: {
    padding: "10px 14px",
    borderBottom: "1px solid #F8F8F8",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  sectionLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    fontWeight: 700,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 6,
  },
};
