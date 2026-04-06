"use client";

import { useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id?: number;
  agent: string;
  level?: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

interface MacroIndicator {
  label: string;
  value: string;
  signal: "up" | "down" | "neutral";
  color: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function evMsg(e: AgentEvent): string {
  return e.message ?? e.msg ?? "";
}

function evTs(e: AgentEvent): string {
  return e.ts ?? e.created_at ?? "";
}

function relTime(ts: string): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return `${Math.floor(ms / 1_000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function fmtTime(ts: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    });
  } catch { return "—"; }
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

function FlashAlertBanner({ message }: { message: string }) {
  return (
    <div style={{
      background: "linear-gradient(90deg, rgba(255,59,58,0.15) 0%, rgba(255,59,58,0.08) 100%)",
      border: "1px solid rgba(255,59,58,0.50)",
      borderRadius: "var(--card-radius)",
      padding: "14px 20px",
      marginBottom: 20,
      display: "flex",
      alignItems: "center",
      gap: 12,
      boxShadow: "0 0 24px rgba(255,59,58,0.20)",
    }}>
      <span style={{ fontSize: 20, lineHeight: 1 }}>⚠</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#FF453A", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 2 }}>
          FLASH ALERT — All New Trades Blocked
        </div>
        <div style={{ fontSize: 13, color: "rgba(232,234,237,0.80)" }}>
          {message}
        </div>
      </div>
    </div>
  );
}

function RegimeCard({ regime, yieldCurve, vix }: { regime: string; yieldCurve: string; vix: string }) {
  const regimeColors: Record<string, string> = {
    LOW: "#34C759", NORMAL: "#0A84FF", HIGH: "#FF9F0A", CRISIS: "#FF453A",
  };
  const yieldColors: Record<string, string> = {
    NORMAL: "#34C759", INVERTED: "#FF453A", UNKNOWN: "rgba(232,234,237,0.35)",
  };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "1 1 260px",
    }}>
      <SectionLabel>Regime Summary</SectionLabel>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* GARCH Regime */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>GARCH Regime</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
            color: regimeColors[regime] ?? "rgba(232,234,237,0.45)",
            background: (regimeColors[regime] ?? "rgba(232,234,237,0.45)") + "20",
            padding: "3px 9px", borderRadius: 5,
          }}>
            {regime}
          </span>
        </div>
        {/* Yield Curve */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Yield Curve</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
            color: yieldColors[yieldCurve] ?? "rgba(232,234,237,0.45)",
            background: (yieldColors[yieldCurve] ?? "rgba(232,234,237,0.45)") + "20",
            padding: "3px 9px", borderRadius: 5,
          }}>
            {yieldCurve}
          </span>
        </div>
        {/* VIX */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>VIX</span>
          <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono-stack)" }}>
            {vix ?? "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function MacroIndicatorsGrid({ indicators }: { indicators: MacroIndicator[] }) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "2 1 400px",
    }}>
      <SectionLabel>Key Macro Indicators</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 8 }}>
        {indicators.map(ind => (
          <div
            key={ind.label}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: 8,
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 2 }}>{ind.label}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono-stack)" }}>
                {ind.value}
              </div>
            </div>
            <span style={{
              fontSize: 14,
              color: ind.signal === "up" ? "#34C759" : ind.signal === "down" ? "#FF453A" : "rgba(232,234,237,0.30)",
            }}>
              {ind.signal === "up" ? "↑" : ind.signal === "down" ? "↓" : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CrucixStatusCard({ crucixData }: { crucixData: Record<string, unknown> | null }) {
  const tier     = (crucixData?.risk_tier as string | undefined) ?? "UNKNOWN";
  const lotScale = (crucixData?.lot_scale as number | undefined) ?? 100;
  const isBlackout = (crucixData?.is_blackout as boolean | undefined) ?? false;
  const lastSweep  = (crucixData?.last_sweep as string | undefined);

  const tierColors: Record<string, string> = {
    CLEAR: "#34C759", ROUTINE: "#0A84FF", PRIORITY: "#FF9F0A", FLASH: "#FF453A",
  };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "1 1 260px",
    }}>
      <SectionLabel>Crucix Status</SectionLabel>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Risk tier */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Risk Tier</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
            color: tierColors[tier] ?? "rgba(232,234,237,0.45)",
            background: (tierColors[tier] ?? "rgba(232,234,237,0.45)") + "20",
            padding: "3px 9px", borderRadius: 5,
          }}>
            {tier}
          </span>
        </div>
        {/* Lot scale */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Lot Scale</span>
          <span style={{
            fontSize: 15, fontWeight: 700, color: lotScale < 100 ? "#FF9F0A" : "#34C759",
            fontFamily: "var(--font-mono-stack)",
          }}>
            {lotScale}%
          </span>
        </div>
        {/* Lot scale bar */}
        <div>
          <div style={{ height: 4, background: "rgba(255,255,255,0.08)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{
              height: "100%",
              width: `${lotScale}%`,
              background: lotScale < 100
                ? "linear-gradient(90deg, #FF9F0A, #FF453A)"
                : "#34C759",
              transition: "width 500ms ease",
            }} />
          </div>
        </div>
        {/* Blackout */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Blackout</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
            color: isBlackout ? "#FF453A" : "#34C759",
            background: (isBlackout ? "#FF453A" : "#34C759") + "20",
            padding: "3px 9px", borderRadius: 5,
          }}>
            {isBlackout ? "ACTIVE" : "CLEAR"}
          </span>
        </div>
        {/* Last sweep */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Last Sweep</span>
          <span style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--font-mono-stack)" }}>
            {lastSweep ? relTime(lastSweep) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function SessionBar({ sessions }: {
  sessions: Array<{ key: string; label: string; color: string; hours: string; isActive: boolean }>
}) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "16px 20px",
      marginBottom: 20,
    }}>
      <SectionLabel>Trading Sessions</SectionLabel>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {sessions.map(s => (
          <div
            key={s.key}
            style={{
              flex: "1 1 150px",
              padding: "10px 14px",
              borderRadius: 8,
              outline: s.isActive ? `1px solid ${s.color}44` : "1px solid rgba(255,255,255,0.07)",
              background: s.isActive ? `${s.color}0a` : "rgba(255,255,255,0.03)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <span style={{
                width: 7, height: 7, borderRadius: "50%",
                background: s.isActive ? s.color : "rgba(232,234,237,0.15)",
                boxShadow: s.isActive ? `0 0 6px ${s.color}` : "none",
                flexShrink: 0,
              }} />
              <span style={{
                fontSize: 12, fontWeight: 600, color: s.isActive ? s.color : "rgba(232,234,237,0.40)",
              }}>
                {s.label}
              </span>
              {s.isActive && (
                <span style={{
                  marginLeft: "auto", fontSize: 9, fontWeight: 700, letterSpacing: 0.4,
                  color: s.color, background: `${s.color}20`, borderRadius: 4, padding: "1px 5px",
                }}>
                  LIVE
                </span>
              )}
            </div>
            <div style={{ fontSize: 11, color: "rgba(232,234,237,0.25)", fontFamily: "var(--font-mono-stack)" }}>
              {s.hours}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BlackoutOverlay({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 150,
      background: "rgba(255,59,58,0.08)",
      borderBottom: "1px solid rgba(255,59,58,0.30)",
      padding: "8px 20px",
      display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
      pointerEvents: "none",
    }}>
      <span style={{ fontSize: 16 }}>⛔</span>
      <span style={{ fontSize: 12, fontWeight: 700, color: "#FF453A", letterSpacing: 0.5, textTransform: "uppercase" }}>
        MACRO BLACKOUT — NO NEW TRADES
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MacroPage() {
  const { status: shellStatus } = useAppShell();

  const [events,  setEvents]  = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [nowUtc,  setNowUtc] = useState(new Date());

  // Poll events (for FLASH alerts)
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/events?limit=400");
        const d = await r.json();
        setEvents(Array.isArray(d) ? d : []);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, []);

  // Clock
  useEffect(() => {
    const tick = setInterval(() => setNowUtc(new Date()), 1_000);
    return () => clearInterval(tick);
  }, []);

  // Derived: FLASH alerts from Crucix events
  const flashEvents = useMemo(() =>
    events.filter(e =>
      (e.agent ?? "").toLowerCase() === "crucix" &&
      (severityOf(e) === "error" || /flash|blackout|critical/i.test(evMsg(e)))
    ).slice(0, 5),
    [events]
  );

  const latestFlash = flashEvents[0] ? evMsg(flashEvents[0]) : null;
  const isBlackout  = shellStatus && typeof (shellStatus as unknown as Record<string, unknown>).crucix === "object"
    ? ((shellStatus as unknown as Record<string, unknown>).crucix as Record<string, unknown>)?.is_blackout as boolean
    : false;

  // Mock macro indicators (replace with real API when available)
  const indicators: MacroIndicator[] = useMemo(() => [
    { label: "DGS10 (10Y)",  value: "4.28%",  signal: "down",   color: "#34C759" },
    { label: "DGS2 (2Y)",    value: "4.01%",  signal: "down",   color: "#34C759" },
    { label: "T10Y2Y",       value: "+0.27",  signal: "up",     color: "#34C759" },
    { label: "VIX",          value: "18.4",   signal: "neutral", color: "#0A84FF" },
    { label: "DXY",          value: "104.2",   signal: "down",   color: "#34C759" },
    { label: "WTI Crude",    value: "$78.4",   signal: "up",     color: "#FF9F0A" },
    { label: "GDELT Tone",   value: "2.3",     signal: "neutral", color: "#0A84FF" },
    { label: "EUR/USD",      value: "1.0842",  signal: "up",     color: "#34C759" },
  ], []);

  // Sessions
  const sessions = useMemo(() => {
    const h = new Date().getUTCHours();
    const defs = [
      { key: "sydney",  label: "Sydney",  color: "#5AC8FA", hours: "21:00 – 06:00 UTC" },
      { key: "tokyo",   label: "Tokyo",   color: "#BF5AF2", hours: "00:00 – 09:00 UTC" },
      { key: "london",  label: "London",  color: "#0A84FF", hours: "07:00 – 16:00 UTC" },
      { key: "newyork", label: "New York", color: "#34C759", hours: "12:00 – 21:00 UTC" },
    ];
    return defs.map(s => ({
      ...s,
      isActive: s.key === "sydney"  ? (h >= 21 || h < 6)
              : s.key === "tokyo"   ? (h >= 0  && h < 9)
              : s.key === "london"  ? (h >= 7  && h < 16)
              :                         (h >= 12 && h < 21),
    }));
  }, [nowUtc]);

  const crucixData = shellStatus && typeof shellStatus === "object"
    ? (shellStatus as unknown as Record<string, unknown>).crucix as Record<string, unknown> | null
    : null;

  const regime  = (crucixData?.regime  as string | undefined) ?? "NORMAL";
  const vixVal  = (crucixData?.vix     as string | undefined) ?? "—";
  const yieldCrv = (crucixData?.yield_curve as string | undefined) ?? "UNKNOWN";

  const MONO = "var(--font-mono-stack)";

  return (
    <>
      {/* Blackout overlay */}
      <BlackoutOverlay active={isBlackout} />

      {/* UTC clock strip */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "10px 16px", marginBottom: 20,
        background: "var(--card-bg)", border: "1px solid var(--card-border)",
        borderRadius: "var(--card-radius)",
      }}>
        <span style={{ fontFamily: "Material Symbols Outlined", fontSize: 18, color: "rgba(232,234,237,0.40)", fontWeight: 400 }}>schedule</span>
        <span style={{ fontFamily: MONO, fontSize: 15, color: "var(--text-primary)", letterSpacing: 0.5 }}>
          {nowUtc.toUTCString().slice(0, -4).replace("GMT", "UTC")}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>
          {events.length} events
        </span>
      </div>

      {/* FLASH alert banner */}
      {latestFlash && <FlashAlertBanner message={latestFlash} />}

      {/* Sessions */}
      <SessionBar sessions={sessions} />

      {/* Regime + Crucix cards row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <RegimeCard regime={regime} yieldCurve={yieldCrv} vix={vixVal} />
        <CrucixStatusCard crucixData={crucixData} />
      </div>

      {/* Macro indicators grid */}
      <MacroIndicatorsGrid indicators={indicators} />

      {/* Recent Crucix events */}
      {flashEvents.length > 0 && (
        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--card-border)",
          borderRadius: "var(--card-radius)",
          padding: "20px",
          marginTop: 20,
        }}>
          <SectionLabel>Crucix Event Feed</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {flashEvents.map((ev, i) => (
              <div
                key={ev.id ?? i}
                style={{
                  display: "flex", gap: 12, padding: "9px 12px",
                  borderRadius: 6,
                  background: "rgba(255,59,58,0.04)",
                  borderLeft: "2px solid rgba(255,59,58,0.40)",
                  alignItems: "flex-start",
                }}
              >
                <span style={{ fontSize: 10, color: "rgba(232,234,237,0.25)", fontFamily: MONO, flexShrink: 0, marginTop: 1 }}>
                  {fmtTime(evTs(ev))}
                </span>
                <span style={{ fontSize: 12, color: "rgba(232,234,237,0.80)", flex: 1, lineHeight: 1.5 }}>
                  {evMsg(ev)}
                </span>
                <span style={{ fontSize: 10, color: "#FF453A", fontWeight: 600, flexShrink: 0, textTransform: "uppercase" }}>
                  {severityOf(ev)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
