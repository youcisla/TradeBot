"use client";

import { useCallback, useEffect, useState } from "react";

interface WorldData {
  available: boolean;
  riskTier?: string;
  vix?: number | null;
  yieldCurveInverted?: boolean;
  osintSentiment?: string;
  sweepAgeMinutes?: number | null;
  alerts?: Array<{ tier: string; title: string }>;
  sourceCount?: number;
}

const RISK_COLORS: Record<string, string> = {
  CLEAR: "#16A34A",
  ROUTINE: "#D97706",
  PRIORITY: "#DC2626",
  FLASH: "#7C3AED",
};

const VIX_COLOR = (v: number | null | undefined) => {
  if (v === null || v === undefined) return "#9CA3AF";
  if (v > 28) return "#DC2626";
  if (v > 18) return "#D97706";
  return "#16A34A";
};

export default function WorldStrip() {
  const [data, setData] = useState<WorldData>({ available: false });

  const fetch_ = useCallback(async () => {
    try {
      const r = await fetch("/api/world");
      if (r.ok) {
        const d = await r.json();
        setData(d);
      }
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, 15_000);
    return () => clearInterval(id);
  }, [fetch_]);

  const vixColor = VIX_COLOR(data.vix);
  const riskColor = RISK_COLORS[data.riskTier ?? "CLEAR"] ?? "#9CA3AF";

  return (
    <div style={styles.strip}>
      {/* VIX */}
      <div style={styles.cell}>
        <span style={styles.cellLabel}>VIX</span>
        <span style={{ ...styles.cellValue, color: vixColor }}>
          {data.vix != null ? data.vix.toFixed(1) : "—"}
        </span>
      </div>

      <div style={styles.divider} />

      {/* Risk Tier */}
      <div style={styles.cell}>
        <span style={styles.cellLabel}>Risk</span>
        <span style={{ ...styles.riskBadge, background: `${riskColor}18`, color: riskColor }}>
          {data.riskTier ?? "—"}
        </span>
      </div>

      <div style={styles.divider} />

      {/* Yield Curve */}
      <div style={styles.cell}>
        <span style={styles.cellLabel}>Yield</span>
        <span style={{
          ...styles.cellValue,
          color: data.yieldCurveInverted ? "#DC2626" : "#16A34A",
        }}>
          {data.yieldCurveInverted ? "Inverted" : "Normal"}
        </span>
      </div>

      <div style={styles.divider} />

      {/* OSINT Sentiment */}
      <div style={styles.cell}>
        <span style={styles.cellLabel}>Sentiment</span>
        <span style={{
          ...styles.cellValue,
          color: data.osintSentiment === "bullish" ? "#16A34A"
            : data.osintSentiment === "bearish" ? "#DC2626" : "#9CA3AF",
        }}>
          {data.osintSentiment ?? "—"}
        </span>
      </div>

      <div style={styles.divider} />

      {/* Sweep Age */}
      <div style={styles.cell}>
        <span style={styles.cellLabel}>Macro Scan</span>
        <span style={styles.cellValue}>
          {data.sweepAgeMinutes != null
            ? `${data.sweepAgeMinutes}m ago`
            : data.available ? "fresh" : "offline"}
        </span>
      </div>

      {/* Alerts — show top 3 priority */}
      {data.alerts && data.alerts.length > 0 && (
        <>
          <div style={styles.divider} />
          <div style={styles.alerts}>
            {data.alerts.slice(0, 3).map((a, i) => (
              <span
                key={i}
                style={{
                  ...styles.alertChip,
                  background: a.tier === "PRIORITY" ? "rgba(220,38,38,0.08)" : "rgba(217,119,6,0.08)",
                  color: a.tier === "PRIORITY" ? "#DC2626" : "#D97706",
                }}
              >
                {a.title.slice(0, 48)}
              </span>
            ))}
          </div>
        </>
      )}

      {/* Sources */}
      <div style={styles.sources}>
        <span style={styles.sourcesLabel}>sources</span>
        <span style={styles.sourcesVal}>{data.sourceCount ?? "—"}</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  strip: {
    position: "fixed",
    bottom: 0,
    left: 0,
    right: 0,
    height: 32,
    background: "#FFFFFF",
    borderTop: "1px solid #F0F0F0",
    display: "flex",
    alignItems: "center",
    padding: "0 16px",
    gap: 0,
    zIndex: 100,
    flexShrink: 0,
  },
  cell: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "0 12px",
  },
  cellLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  cellValue: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    color: "#111111",
  },
  riskBadge: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    fontWeight: 700,
    padding: "1px 6px",
    borderRadius: 3,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  divider: {
    width: 1,
    height: 14,
    background: "#E5E7EB",
    flexShrink: 0,
  },
  alerts: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    flex: 1,
    overflow: "hidden",
    padding: "0 8px",
  },
  alertChip: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    fontWeight: 600,
    padding: "1px 7px",
    borderRadius: 3,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    maxWidth: 200,
  },
  sources: {
    marginLeft: "auto",
    display: "flex",
    alignItems: "center",
    gap: 4,
    flexShrink: 0,
  },
  sourcesLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
  },
  sourcesVal: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    fontWeight: 700,
    color: "#6B7280",
  },
};
