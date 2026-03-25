"use client";

import { useEffect, useState } from "react";

type Tier = "FLASH" | "PRIORITY" | "ROUTINE" | "CLEAR" | null;

const TIER_COLOR: Record<string, string> = {
  FLASH:    "#ff4455",
  PRIORITY: "#f5c518",
  ROUTINE:  "#00d4ff",
  CLEAR:    "#00ff88",
};

const TIER_BG: Record<string, string> = {
  FLASH:    "rgba(255,68,85,0.1)",
  PRIORITY: "rgba(245,197,24,0.1)",
  ROUTINE:  "rgba(0,212,255,0.08)",
  CLEAR:    "rgba(0,255,136,0.06)",
};

function Kpi({ label, value, color = "#9aa8b8" }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <div style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", color: "#607888", letterSpacing: "0.16em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 16, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function Alert({ title, tier }: { title: string; tier: string }) {
  const c = TIER_COLOR[tier] || "#9aa8b8";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 12px", background: TIER_BG[tier] || "transparent", borderLeft: `2px solid ${c}`, borderRadius: "0 4px 4px 0", marginBottom: 4 }}>
      <span style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: c, letterSpacing: "0.1em", minWidth: 56 }}>{tier}</span>
      <span style={{ fontSize: 10.5, fontFamily: "'JetBrains Mono', monospace", color: "#9aa8b8" }}>{title}</span>
    </div>
  );
}

export default function WorldIntelPage() {
  const [data, setData]       = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/world")
        .then((r) => r.json())
        .then((d) => { if (active) { setData(d); setLoading(false); } })
        .catch(() => { if (active) setLoading(false); });
    load();
    const id = setInterval(load, 60_000);   // refresh every 60s
    return () => { active = false; clearInterval(id); };
  }, []);

  const available = data?.available === true;
  const tier = (data as Record<string, unknown> | null)
    ? (String((data as Record<string, unknown>).riskTier || "CLEAR")) as Tier
    : null;
  const tierColor = tier ? (TIER_COLOR[tier] || "#9aa8b8") : "#607888";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Header */}
      <div>
        <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase" }}>OSINT · Macro · Geopolitical</div>
        <h1 style={{ fontSize: 20, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: "#00d4ff", textShadow: "0 0 20px rgba(0,212,255,0.3)", marginTop: 2 }}>World Intelligence</h1>
      </div>

      {/* Status */}
      {loading && (
        <div style={{ padding: "40px 20px", textAlign: "center", fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: "0.2em", textTransform: "uppercase", color: "#607888" }}>
          <div style={{ width: 20, height: 20, border: "1.5px solid #1c1c28", borderTop: "1.5px solid #00ff88", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
          connecting to crucix…
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {!loading && !available && (
        <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "24px 20px", fontFamily: "'JetBrains Mono', monospace" }}>
          <div style={{ fontSize: 11, color: "#ff4455", marginBottom: 8 }}>Crucix not running</div>
          <div style={{ fontSize: 9.5, color: "#607888", lineHeight: 1.7 }}>
            Start it with: <span style={{ color: "#00ff88" }}>cd crucix && node server.mjs</span><br />
            The trading bot continues normally without it.
          </div>
        </div>
      )}

      {!loading && available && (
        <>
          {/* Risk tier */}
          <div style={{ background: "#0a0a12", border: `1px solid ${tierColor}40`, borderTop: `2px solid ${tierColor}`, borderRadius: 8, padding: "16px 20px", display: "flex", alignItems: "center", gap: 20 }}>
            <div>
              <div style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", color: "#607888", letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 4 }}>Macro risk tier</div>
              <div style={{ fontSize: 28, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: tierColor }}>{tier}</div>
            </div>
            <div style={{ fontSize: 9.5, fontFamily: "'JetBrains Mono', monospace", color: "#607888", lineHeight: 1.8 }}>
              {tier === "FLASH"    && "Critical — trading halted by macro blackout"}
              {tier === "PRIORITY" && "Significant event — lot sizes reduced 50%"}
              {tier === "ROUTINE"  && "Background signals — lot sizes reduced 25%"}
              {tier === "CLEAR"    && "All clear — normal trading conditions"}
            </div>
          </div>

          {/* KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "14px 16px" }}>
              <Kpi label="VIX" value={String((data as Record<string, unknown> | null)?.vix ?? "—")} color={(Number((data as Record<string, unknown> | null)?.vix) || 0) > 30 ? "#ff4455" : "#00ff88"} />
            </div>
            <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "14px 16px" }}>
              <Kpi label="Yield curve" value={(data as Record<string, unknown> | null)?.yieldCurveInverted ? "INVERTED" : "Normal"} color={(data as Record<string, unknown> | null)?.yieldCurveInverted ? "#ff4455" : "#00ff88"} />
            </div>
            <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "14px 16px" }}>
              <Kpi label="OSINT sentiment" value={String((data as Record<string, unknown> | null)?.osintSentiment ?? "neutral")} color="#9aa8b8" />
            </div>
            <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "14px 16px" }}>
              <Kpi label="Sweep age" value={`${(data as Record<string, unknown> | null)?.sweepAgeMinutes ?? "?"}m`} color={Number((data as Record<string, unknown> | null)?.sweepAgeMinutes) > 20 ? "#f5c518" : "#00ff88"} />
            </div>
          </div>

          {/* Active alerts */}
          {Array.isArray((data as Record<string, unknown> | null)?.alerts) && ((data as Record<string, unknown>).alerts as unknown[]).length > 0 && (
            <div style={{ background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8, padding: "16px 20px" }}>
              <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "#607888", letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 12, paddingBottom: 10, borderBottom: "1px solid #1c1c28" }}>Active alerts</div>
              {((data as Record<string, unknown>).alerts as Array<{ tier: string; title: string }>).slice(0, 8).map((a, i) => (
                <Alert key={i} title={a.title || "Unnamed alert"} tier={String(a.tier || "ROUTINE").toUpperCase()} />
              ))}
            </div>
          )}

          <div style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", color: "#607888", textAlign: "right" }}>
            Powered by Crucix — {(data as Record<string, unknown> | null)?.sourceCount ?? 27} intelligence sources · refreshes every 60s
          </div>
        </>
      )}
    </div>
  );
}
