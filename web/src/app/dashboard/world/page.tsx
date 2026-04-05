"use client";

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type RiskTier = "CLEAR" | "ROUTINE" | "PRIORITY" | "FLASH";

interface WorldAlert {
  tier:      string;
  title:     string;
  source?:   string;
  timestamp?: string;
}

interface WorldData {
  available:           boolean;
  riskTier:            RiskTier;
  vix:                 number | string;
  yieldCurveInverted:  boolean;
  osintSentiment:      string;
  sweepAgeMinutes:     number;
  alerts:              WorldAlert[];
  sourceCount:         number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FONT = `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO = `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

const TIER_COLOR: Record<string, string> = {
  CLEAR:    "#30D158",
  ROUTINE:  "#64D2FF",
  PRIORITY: "#FF9F0A",
  FLASH:    "#FF453A",
};

const TIER_DESC: Record<string, string> = {
  CLEAR:    "All clear — normal trading conditions",
  ROUTINE:  "Background signals — lot sizes reduced 25%",
  PRIORITY: "Significant event — lot sizes reduced 50%",
  FLASH:    "Critical — trading halted by macro blackout",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function alertTierColor(tier: string): string {
  return TIER_COLOR[String(tier ?? "ROUTINE").toUpperCase()] ?? "#8E8E93";
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: string | number;
  color?: string;
  icon?: string;
}) {
  return (
    <div
      style={{
        background:    "#1C1C1E",
        borderRadius:  12,
        padding:       "14px 16px",
        display:       "flex",
        flexDirection: "column",
        gap:           4,
        flex:          1,
        minWidth:      120,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {icon && (
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 15, color: color ?? "rgba(235,235,245,0.4)" }}
          >
            {icon}
          </span>
        )}
        <span style={{ fontSize: 11, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>
          {label}
        </span>
      </div>
      <span
        style={{
          fontSize:   20,
          fontWeight: 700,
          color:      color ?? "#FFFFFF",
          fontFamily: FONT,
        }}
      >
        {value}
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WorldPage() {
  const [data,    setData]    = useState<WorldData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/world")
        .then((r) => r.json())
        .then((d) => {
          if (active) {
            setData(d);
            setLoading(false);
            setLastUpdated(new Date().toLocaleTimeString());
          }
        })
        .catch(() => { if (active) setLoading(false); });
    load();
    const id = setInterval(load, 60_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const available = data?.available === true;
  const tier      = data ? (String(data.riskTier || "CLEAR") as RiskTier) : null;
  const tierColor = tier ? (TIER_COLOR[tier] ?? "#8E8E93") : "#8E8E93";

  return (
    <div
      style={{
        paddingTop:    20,
        paddingBottom: 40,
        fontFamily:    FONT,
        minHeight:     "100vh",
        background:    "#000000",
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize:     28,
          fontWeight:   700,
          color:        "#FFFFFF",
          margin:       "0 0 20px",
          letterSpacing:"-0.5px",
          fontFamily:   FONT,
        }}
      >
        Macro Brief
      </h1>

      {/* Loading */}
      {loading && (
        <div
          style={{
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            padding:        "80px 0",
            color:          "rgba(235,235,245,0.4)",
            fontSize:       14,
            fontFamily:     FONT,
          }}
        >
          Connecting to Crucix…
        </div>
      )}

      {/* Crucix offline */}
      {!loading && !available && (
        <div
          style={{
            background:   "#1C1C1E",
            borderRadius: 12,
            padding:      "24px 20px",
            borderLeft:   "4px solid #FF453A",
            display:      "flex",
            flexDirection:"column",
            gap:          10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 20, color: "#FF453A" }}
            >
              wifi_off
            </span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "#FF453A", fontFamily: FONT }}>
              Crucix offline
            </span>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: "rgba(235,235,245,0.5)", lineHeight: 1.6, fontFamily: FONT }}>
            Start it with:{" "}
            <code
              style={{
                fontFamily:   MONO,
                color:        "#64D2FF",
                background:   "#2C2C2E",
                padding:      "1px 6px",
                borderRadius: 5,
              }}
            >
              cd crucix &amp;&amp; node server.mjs
            </code>
            <br />
            The trading bot continues normally without it.
          </p>
        </div>
      )}

      {/* Main content */}
      {!loading && available && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Risk Tier Hero Card */}
          <div
            style={{
              background:   "#1C1C1E",
              borderRadius: 12,
              padding:      20,
              display:      "flex",
              flexDirection:"column",
              gap:          16,
            }}
          >
            {/* Tier display */}
            <div style={{ display: "flex", alignItems: "flex-start", gap: 20, flexWrap: "wrap" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span
                  style={{
                    fontSize:     11,
                    color:        "rgba(235,235,245,0.4)",
                    letterSpacing:"0.08em",
                    textTransform:"uppercase",
                    fontFamily:   FONT,
                  }}
                >
                  Macro Risk Tier
                </span>
                <span
                  style={{
                    fontSize:   34,
                    fontWeight: 700,
                    color:      tierColor,
                    fontFamily: FONT,
                    lineHeight: 1.1,
                  }}
                >
                  {tier ?? "—"}
                </span>
              </div>

              <div style={{ flex: 1, paddingTop: 6 }}>
                <p style={{ margin: "0 0 10px", fontSize: 13, color: "rgba(235,235,245,0.6)", lineHeight: 1.6, fontFamily: FONT }}>
                  {tier ? TIER_DESC[tier] : "—"}
                </p>
                <div
                  style={{
                    display:     "inline-flex",
                    alignItems:  "center",
                    gap:         6,
                    background:  `${tierColor}15`,
                    border:      `1px solid ${tierColor}40`,
                    borderRadius: 8,
                    padding:     "4px 12px",
                  }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 14, color: tierColor }}
                  >
                    sensors
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: tierColor, fontFamily: FONT }}>
                    {data?.sourceCount ?? 0} intelligence sources
                  </span>
                </div>
              </div>
            </div>

            {/* Sub-row stats */}
            <div
              style={{
                borderTop: "0.5px solid rgba(84,84,88,0.65)",
                paddingTop: 14,
                display:   "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap:       10,
              }}
            >
              <StatCard
                label="VIX"
                value={data?.vix ?? "—"}
                color={(Number(data?.vix) || 0) > 30 ? "#FF453A" : "#30D158"}
                icon="show_chart"
              />
              <StatCard
                label="Yield Curve"
                value={data?.yieldCurveInverted ? "INVERTED" : "Normal"}
                color={data?.yieldCurveInverted ? "#FF453A" : "#30D158"}
                icon="trending_down"
              />
              <StatCard
                label="OSINT Sentiment"
                value={String(data?.osintSentiment ?? "neutral")}
                color="#FFFFFF"
                icon="language"
              />
              <StatCard
                label="Sweep Age"
                value={`${data?.sweepAgeMinutes ?? "?"}m`}
                color={Number(data?.sweepAgeMinutes) > 20 ? "#FF9F0A" : "#30D158"}
                icon="schedule"
              />
            </div>

            {/* Last updated */}
            <div
              style={{
                textAlign:  "right",
                fontSize:   11,
                color:      "rgba(235,235,245,0.3)",
                fontFamily: MONO,
                marginTop:  -8,
              }}
            >
              Updated {lastUpdated} · refreshes every 60s
            </div>
          </div>

          {/* Alert feed */}
          {Array.isArray(data?.alerts) && data.alerts.length > 0 && (
            <div
              style={{
                background:   "#1C1C1E",
                borderRadius: 12,
                overflow:     "hidden",
              }}
            >
              {/* Alert header */}
              <div
                style={{
                  padding:      "12px 16px",
                  borderBottom: "0.5px solid rgba(84,84,88,0.65)",
                  display:      "flex",
                  alignItems:   "center",
                  gap:          8,
                }}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 17, color: "#FF9F0A" }}
                >
                  warning
                </span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#FFFFFF", fontFamily: FONT }}>
                  Active Alerts
                </span>
                <span
                  style={{
                    marginLeft:   "auto",
                    background:   "rgba(255,159,10,0.15)",
                    border:       "1px solid rgba(255,159,10,0.4)",
                    color:        "#FF9F0A",
                    fontSize:     11,
                    fontWeight:   600,
                    padding:      "1px 8px",
                    borderRadius: 6,
                    fontFamily:   FONT,
                  }}
                >
                  {data.alerts.length}
                </span>
              </div>

              {/* Alert rows */}
              {data.alerts.slice(0, 10).map((a, i) => {
                const ac = alertTierColor(a.tier);
                return (
                  <div
                    key={i}
                    style={{
                      display:     "flex",
                      alignItems:  "flex-start",
                      gap:         12,
                      padding:     "12px 16px",
                      borderLeft:  `3px solid ${ac}`,
                      borderBottom: i < data.alerts.length - 1
                        ? "0.5px solid rgba(84,84,88,0.3)"
                        : "none",
                      background:  `${ac}08`,
                    }}
                  >
                    <span
                      style={{
                        fontSize:     10,
                        fontWeight:   700,
                        color:        ac,
                        letterSpacing:"0.07em",
                        textTransform:"uppercase",
                        flexShrink:   0,
                        paddingTop:   2,
                        minWidth:     56,
                        fontFamily:   FONT,
                      }}
                    >
                      {String(a.tier || "ROUTINE").toUpperCase()}
                    </span>

                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontSize: 13, color: "rgba(235,235,245,0.85)", lineHeight: 1.5, fontFamily: FONT }}>
                        {a.title || "Unnamed alert"}
                      </p>
                      {a.source && (
                        <span style={{ fontSize: 11, color: "rgba(235,235,245,0.35)", fontFamily: MONO }}>
                          {a.source}
                        </span>
                      )}
                    </div>

                    {a.timestamp && (
                      <span style={{ fontSize: 11, color: "rgba(235,235,245,0.3)", fontFamily: MONO, flexShrink: 0 }}>
                        {(() => {
                          try { return new Date(a.timestamp!).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
                          catch { return ""; }
                        })()}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* No alerts empty state */}
          {Array.isArray(data?.alerts) && data.alerts.length === 0 && (
            <div
              style={{
                background:   "#1C1C1E",
                borderRadius: 12,
                padding:      "24px 20px",
                display:      "flex",
                alignItems:   "center",
                gap:          12,
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 20, color: "#30D158" }}
              >
                check_circle
              </span>
              <span style={{ fontSize: 13, color: "rgba(235,235,245,0.6)", fontFamily: FONT }}>
                No active alerts — all clear
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
