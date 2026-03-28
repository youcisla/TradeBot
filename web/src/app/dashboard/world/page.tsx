"use client";

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type Tier = "FLASH" | "PRIORITY" | "ROUTINE" | "CLEAR";

const TIER_COLOR: Record<string, string> = {
  FLASH:    "#ff716c",
  PRIORITY: "#ffb86c",
  ROUTINE:  "#00d2fd",
  CLEAR:    "#00fd87",
};

const TIER_DESC: Record<string, string> = {
  FLASH:    "Critical — trading halted by macro blackout",
  PRIORITY: "Significant event — lot sizes reduced 50%",
  ROUTINE:  "Background signals — lot sizes reduced 25%",
  CLEAR:    "All clear — normal trading conditions",
};

// ── Page ──────────────────────────────────────────────────────────────────────

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
    const id = setInterval(load, 60_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const available  = data?.available === true;
  const tier       = data ? (String(data.riskTier || "CLEAR") as Tier) : null;
  const tierColor  = tier ? (TIER_COLOR[tier] || "#adaaaa") : "#adaaaa";

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-4 border-secondary pl-6 py-2 bg-surface-container-low">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-secondary text-[10px] font-bold tracking-[0.2em] uppercase">OSINT · MACRO · GEOPOLITICAL</span>
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tighter uppercase mb-2">
          World Intelligence
        </h1>
        <p className="text-on-surface-variant text-sm font-mono">
          Powered by Crucix — live geopolitical + macro risk feed
        </p>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="w-6 h-6 border-2 border-outline-variant border-t-primary-fixed rounded-full animate-spin" />
          <span className="text-[9px] text-outline tracking-[0.3em] uppercase">Connecting to Crucix…</span>
        </div>
      )}

      {/* ── Crucix Offline ── */}
      {!loading && !available && (
        <div className="bg-surface-container-low border border-outline-variant/10 border-l-4 border-l-error p-6">
          <div className="text-error font-bold text-sm mb-2">Crucix not running</div>
          <div className="text-on-surface-variant text-[11px] leading-relaxed">
            Start it with:{" "}
            <span className="text-primary-fixed font-bold">cd crucix && node server.mjs</span>
            <br />
            The trading bot continues normally without it.
          </div>
        </div>
      )}

      {/* ── Data ── */}
      {!loading && available && (
        <>
          {/* Risk Tier Banner */}
          <div
            className="p-6 border-t-4 bg-surface-container-low flex items-start gap-8"
            style={{ borderTopColor: tierColor }}
          >
            <div>
              <div className="text-[9px] text-outline tracking-[0.2em] uppercase mb-2">MACRO RISK TIER</div>
              <div className="text-5xl font-extrabold tracking-tighter" style={{ color: tierColor }}>
                {tier}
              </div>
            </div>
            <div className="flex-1 pt-2">
              <p className="text-on-surface-variant text-sm leading-relaxed">
                {tier ? TIER_DESC[tier] : "—"}
              </p>
              <div
                className="mt-4 inline-block text-[10px] font-bold px-3 py-1 border"
                style={{
                  color: tierColor,
                  borderColor: `${tierColor}40`,
                  background: `${tierColor}10`,
                }}
              >
                {String(data?.sourceCount ?? 27)} INTELLIGENCE SOURCES
              </div>
            </div>
          </div>

          {/* KPI Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-1 bg-outline-variant/10">
            {[
              {
                label: "VIX",
                value: String(data?.vix ?? "—"),
                color: (Number(data?.vix) || 0) > 30 ? "#ff716c" : "#00fd87",
              },
              {
                label: "YIELD CURVE",
                value: data?.yieldCurveInverted ? "INVERTED" : "Normal",
                color: data?.yieldCurveInverted ? "#ff716c" : "#00fd87",
              },
              {
                label: "OSINT SENTIMENT",
                value: String(data?.osintSentiment ?? "neutral"),
                color: "#adaaaa",
              },
              {
                label: "SWEEP AGE",
                value: `${data?.sweepAgeMinutes ?? "?"}m`,
                color: Number(data?.sweepAgeMinutes) > 20 ? "#ffb86c" : "#00fd87",
              },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-surface p-5">
                <div className="text-[9px] text-outline tracking-[0.2em] uppercase mb-1">{label}</div>
                <div className="text-2xl font-extrabold" style={{ color }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Active Alerts */}
          {Array.isArray(data?.alerts) && (data.alerts as unknown[]).length > 0 && (
            <div className="bg-surface-container-low border border-outline-variant/10 p-6">
              <h3 className="text-[9px] font-bold tracking-[0.3em] text-outline uppercase mb-4 pb-3 border-b border-outline-variant/15">
                Active Alerts
              </h3>
              <div className="flex flex-col gap-2">
                {(data.alerts as Array<{ tier: string; title: string }>).slice(0, 8).map((a, i) => {
                  const ac = TIER_COLOR[String(a.tier || "ROUTINE").toUpperCase()] || "#adaaaa";
                  return (
                    <div
                      key={i}
                      className="flex items-center gap-4 p-2.5 border-l-2"
                      style={{
                        borderLeftColor: ac,
                        background: `${ac}0a`,
                      }}
                    >
                      <span
                        className="text-[9px] font-bold tracking-[0.1em] shrink-0 w-16"
                        style={{ color: ac }}
                      >
                        {String(a.tier || "ROUTINE").toUpperCase()}
                      </span>
                      <span className="text-[11px] text-on-surface-variant">{a.title || "Unnamed alert"}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="text-right text-[9px] text-outline tracking-widest">
            Refreshes every 60s
          </div>
        </>
      )}
    </div>
  );
}
