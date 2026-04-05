"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface WorldData {
  available:          boolean;
  riskTier:           string;
  vix:                number | string;
  yieldCurveInverted: boolean;
  osintSentiment:     string;
  sweepAgeMinutes:    number;
  sourceCount:        number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FONT = `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO = `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

const MARKET_PAIRS = [
  { label: "EUR/USD", region: "Europe",  flag: "🇪🇺" },
  { label: "GBP/USD", region: "London",  flag: "🇬🇧" },
  { label: "USD/JPY", region: "Tokyo",   flag: "🇯🇵" },
  { label: "AUD/USD", region: "Sydney",  flag: "🇦🇺" },
  { label: "USD/CAD", region: "US",      flag: "🇨🇦" },
  { label: "XAU/USD", region: "Global",  flag: "🥇" },
];

// ── Globe fallback ────────────────────────────────────────────────────────────

function GlobeFallback() {
  return (
    <div
      style={{
        width:          "100%",
        minHeight:      520,
        borderRadius:   16,
        border:         "0.5px solid rgba(84,84,88,0.65)",
        background:
          "radial-gradient(circle at 20% 20%, rgba(100, 210, 255, 0.10), transparent 45%), " +
          "radial-gradient(circle at 80% 75%, rgba(191,90,242,0.08), transparent 45%), " +
          "#1C1C1E",
        display:        "flex",
        alignItems:     "center",
        justifyContent: "center",
        padding:        24,
        textAlign:      "center",
        fontFamily:     FONT,
      }}
    >
      <div style={{ maxWidth: 480 }}>
        {/* SVG Globe */}
        <div style={{ marginBottom: 20 }}>
          <svg
            width="80"
            height="80"
            viewBox="0 0 80 80"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            style={{ margin: "0 auto", display: "block" }}
          >
            <circle cx="40" cy="40" r="36" stroke="#64D2FF" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.5" />
            <circle cx="40" cy="40" r="26" stroke="#64D2FF" strokeWidth="1" opacity="0.3" />
            <ellipse cx="40" cy="40" rx="14" ry="36" stroke="#64D2FF" strokeWidth="1" opacity="0.25" />
            <ellipse cx="40" cy="40" rx="36" ry="14" stroke="#64D2FF" strokeWidth="1" opacity="0.25" />
            <circle cx="40" cy="40" r="4" fill="#64D2FF" opacity="0.7" />
            <circle cx="40" cy="40" r="8" stroke="#64D2FF" strokeWidth="1" opacity="0.35" />
            {/* Dots for major cities */}
            <circle cx="30" cy="30" r="2.5" fill="#30D158" opacity="0.85" />
            <circle cx="55" cy="35" r="2" fill="#FF9F0A" opacity="0.75" />
            <circle cx="22" cy="48" r="2" fill="#64D2FF" opacity="0.75" />
            <circle cx="62" cy="52" r="2" fill="#BF5AF2" opacity="0.75" />
            <circle cx="45" cy="22" r="2" fill="#FF453A" opacity="0.65" />
          </svg>
        </div>

        <h2
          style={{
            margin:     "0 0 8px",
            fontSize:   20,
            fontWeight: 700,
            color:      "#FFFFFF",
            fontFamily: FONT,
          }}
        >
          Global Markets
        </h2>
        <p
          style={{
            margin:   "0 0 6px",
            color:    "rgba(235,235,245,0.4)",
            fontSize: 13,
            lineHeight: 1.6,
            fontFamily: FONT,
          }}
        >
          3D globe renderer unavailable in this environment
        </p>
        <p
          style={{
            margin:   0,
            color:    "rgba(235,235,245,0.25)",
            fontSize: 12,
            fontFamily: MONO,
          }}
        >
          Interactive globe coming soon
        </p>
      </div>
    </div>
  );
}

// ── Market pair chip ──────────────────────────────────────────────────────────

function MarketChip({ label, region, flag }: { label: string; region: string; flag: string }) {
  return (
    <div
      style={{
        background:    "#1C1C1E",
        borderRadius:  12,
        padding:       "12px 14px",
        display:       "flex",
        flexDirection: "column",
        gap:           4,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 16 }}>{flag}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color: "#FFFFFF", fontFamily: FONT }}>
          {label}
        </span>
      </div>
      <span style={{ fontSize: 11, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>
        {region}
      </span>
    </div>
  );
}

// ── Dynamic globe import ──────────────────────────────────────────────────────

const ForexGlobe = dynamic(
  () =>
    import("./ForexGlobe").catch(() => {
      return { default: GlobeFallback };
    }),
  {
    ssr:     false,
    loading: () => (
      <div
        style={{
          width:          "100%",
          height:         520,
          display:        "flex",
          alignItems:     "center",
          justifyContent: "center",
          background:     "#1C1C1E",
          borderRadius:   16,
          color:          "rgba(235,235,245,0.35)",
          fontSize:       13,
          letterSpacing:  "0.06em",
          fontFamily:     FONT,
        }}
      >
        Loading globe…
      </div>
    ),
  }
);

// ── Page ──────────────────────────────────────────────────────────────────────

export default function GlobePage() {
  const [world, setWorld] = useState<WorldData | null>(null);

  useEffect(() => {
    fetch("/api/world")
      .then((r) => r.json())
      .then((d) => setWorld(d))
      .catch(() => {});
  }, []);

  const tierColors: Record<string, string> = {
    CLEAR:    "#30D158",
    ROUTINE:  "#64D2FF",
    PRIORITY: "#FF9F0A",
    FLASH:    "#FF453A",
  };
  const tier      = world?.available ? String(world.riskTier ?? "CLEAR").toUpperCase() : null;
  const tierColor = tier ? (tierColors[tier] ?? "#8E8E93") : "#8E8E93";

  return (
    <div
      style={{
        paddingTop:    20,
        paddingBottom: 40,
        fontFamily:    FONT,
        minHeight:     "100vh",
        background:    "#000000",
        display:       "flex",
        flexDirection: "column",
        gap:           20,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1
            style={{
              margin:       "0 0 4px",
              fontSize:     28,
              fontWeight:   700,
              color:        "#FFFFFF",
              letterSpacing:"-0.5px",
              fontFamily:   FONT,
            }}
          >
            Market Globe
          </h1>
          <p style={{ margin: 0, fontSize: 13, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>
            Live session activity across global financial centers
          </p>
        </div>

        {/* Live indicator */}
        <div
          style={{
            display:      "flex",
            alignItems:   "center",
            gap:          6,
            padding:      "6px 14px",
            background:   "rgba(48,209,88,0.12)",
            border:       "1px solid rgba(48,209,88,0.35)",
            borderRadius: 20,
            fontSize:     12,
            fontWeight:   600,
            color:        "#30D158",
            letterSpacing:"0.07em",
            fontFamily:   FONT,
          }}
        >
          <span
            style={{
              width:        6,
              height:       6,
              borderRadius: "50%",
              background:   "#30D158",
              boxShadow:    "0 0 5px #30D158",
              flexShrink:   0,
            }}
          />
          LIVE
        </div>
      </div>

      {/* Macro status strip — shows if Crucix is available */}
      {world?.available && tier && (
        <div
          style={{
            background:   "#1C1C1E",
            borderRadius: 10,
            padding:      "10px 16px",
            display:      "flex",
            alignItems:   "center",
            gap:          12,
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 18, color: tierColor }}
          >
            public
          </span>
          <span style={{ fontSize: 13, color: "rgba(235,235,245,0.6)", fontFamily: FONT }}>
            Macro Risk:
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color: tierColor, fontFamily: FONT }}>
            {tier}
          </span>
          <span style={{ fontSize: 12, color: "rgba(235,235,245,0.3)", marginLeft: "auto", fontFamily: MONO }}>
            VIX {world.vix ?? "—"} · {world.sourceCount ?? 0} sources
          </span>
        </div>
      )}

      {/* 3D Globe */}
      <ForexGlobe />

      {/* Markets grid */}
      <div>
        <h2
          style={{
            margin:       "0 0 12px",
            fontSize:     15,
            fontWeight:   600,
            color:        "rgba(235,235,245,0.6)",
            letterSpacing:"0.02em",
            fontFamily:   FONT,
          }}
        >
          Major FX Pairs
        </h2>
        <div
          style={{
            display:             "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
            gap:                 10,
          }}
        >
          {MARKET_PAIRS.map((p) => (
            <MarketChip key={p.label} {...p} />
          ))}
        </div>
      </div>
    </div>
  );
}
