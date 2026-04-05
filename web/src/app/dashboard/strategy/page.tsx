"use client";

import { useEffect, useMemo, useState } from "react";

interface StrategyConfidence {
  strategy: string;
  confidence: number;
  total_trades: number;
  total_score: number;
  last_updated: string;
}

interface BotStatus {
  state?: string;
  active_strategies?: string[];
  equity?: number;
  balance?: number;
}

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
}

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO =
  `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

const PIPELINE_AGENTS = [
  "crucix", "market", "analysis", "strategy", "neural",
  "council", "risk", "execution", "trade_manager",
];

const PIPELINE_STYLE = `
  @keyframes strategyFlow {
    0% { transform: translateX(-95%); opacity: 0; }
    30% { opacity: 1; }
    100% { transform: translateX(120%); opacity: 0; }
  }
  @keyframes strategyLift {
    0%, 100% { transform: translateY(0px) rotateX(0deg) rotateY(0deg); }
    50% { transform: translateY(-4px) rotateX(2deg) rotateY(-2deg); }
  }
  @keyframes strategyAura {
    0%, 100% { opacity: 0.35; }
    50% { opacity: 0.85; }
  }
`;

function formatStrategy(raw: string): string {
  const model = raw.includes(":") ? raw.split(":").pop()! : raw;
  return model.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function confBarColor(conf: number): string {
  if (conf > 0.7) return "#30D158";
  if (conf > 0.4) return "#FF9F0A";
  return "#FF453A";
}

function confLabel(conf: number): string {
  if (conf >= 0.7) return "Full";
  if (conf >= 0.4) return "Reduced";
  if (conf >= 0.2) return "Low";
  return "Disabled";
}

type RecencyTier = "fresh" | "warm" | "stale" | "cold";

function eventTs(ev: AgentEvent | undefined): string | undefined {
  if (!ev) return undefined;
  return ev.created_at ?? ev.ts;
}

function recencyTier(ts: string | undefined): RecencyTier {
  if (!ts) return "cold";
  const ageMs = Date.now() - new Date(ts).getTime();
  if (ageMs < 60_000) return "fresh";
  if (ageMs < 5 * 60_000) return "warm";
  return "stale";
}

export default function StrategyPage() {
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);

  useEffect(() => {
    let active = true;
    const load = () => {
      Promise.allSettled([
        fetch("/api/learning").then((r) => r.json()),
        fetch("/api/status").then((r) => r.json()),
        fetch("/api/events?limit=60").then((r) => r.json()),
      ]).then(([l, s, e]) => {
        if (!active) return;
        if (l.status === "fulfilled") setConfidences(l.value?.confidences ?? []);
        if (s.status === "fulfilled") setBotStatus(s.value ?? null);
        if (e.status === "fulfilled") setEvents(Array.isArray(e.value) ? e.value : (e.value?.events ?? []));
      });
    };
    load();
    const id = setInterval(load, 8_000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const activeStrategies: string[] = useMemo(() => {
    if (botStatus?.active_strategies?.length) return botStatus.active_strategies;
    return ["neural", "ict", "sma_crossover"];
  }, [botStatus]);

  const isRunning = botStatus?.state === "running" || botStatus?.state === "RUNNING";

  const agentLatest = useMemo(() => {
    const map: Record<string, AgentEvent> = {};
    for (const ev of events) {
      const key = ev.agent?.toLowerCase();
      if (key && !map[key]) map[key] = ev;
    }
    return map;
  }, [events]);

  return (
    <div
      style={{
        fontFamily: FONT,
        paddingTop: 20,
        paddingLeft: 20,
        paddingRight: 20,
        paddingBottom: 40,
        maxWidth: 1200,
        margin: "0 auto",
      }}
    >
      <style>{PIPELINE_STYLE}</style>

      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          marginBottom: 28,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: "#FFFFFF",
            margin: 0,
          }}
        >
          Automation
        </h1>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "#1C1C1E",
            borderRadius: 10,
            padding: "8px 14px",
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: isRunning ? "#30D158" : "#FF453A",
              boxShadow: isRunning ? "0 0 6px #30D158" : "none",
            }}
          />
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: isRunning ? "#30D158" : "#FF453A",
            }}
          >
            {isRunning ? "Automation Online" : "Automation Paused"}
          </span>
        </div>
      </div>

      {/* Pipeline Flow */}
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "16px 20px",
          marginBottom: 24,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 14,
          }}
        >
          Agent Pipeline
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 0,
            overflowX: "auto",
            paddingBottom: 4,
            scrollbarWidth: "none",
            perspective: 900,
            position: "relative",
          }}
        >
          {PIPELINE_AGENTS.map((agent, idx) => {
            const ev = agentLatest[agent];
            const tier = recencyTier(eventTs(ev));
            const isActive = tier === "fresh";
            const isLast = idx === PIPELINE_AGENTS.length - 1;
            return (
              <div
                key={agent}
                style={{
                  display: "flex",
                  alignItems: "center",
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    background: isActive
                      ? "rgba(10,132,255,0.15)"
                      : "rgba(120,120,128,0.24)",
                    borderRadius: 8,
                    padding: "6px 12px",
                    fontSize: 12,
                    fontWeight: 600,
                    color: isActive ? "#0A84FF" : "rgba(235,235,245,0.3)",
                    whiteSpace: "nowrap",
                    fontFamily: MONO,
                    position: "relative",
                    overflow: "hidden",
                    border: isActive
                      ? "0.5px solid rgba(10,132,255,0.45)"
                      : tier === "warm"
                      ? "0.5px solid rgba(10,132,255,0.28)"
                      : "0.5px solid rgba(84,84,88,0.4)",
                    boxShadow: isActive
                      ? "0 8px 22px rgba(10,132,255,0.18), inset 0 1px 0 rgba(255,255,255,0.07)"
                      : tier === "warm"
                      ? "0 5px 14px rgba(10,132,255,0.12), inset 0 1px 0 rgba(255,255,255,0.04)"
                      : "inset 0 1px 0 rgba(255,255,255,0.03)",
                    transformStyle: "preserve-3d",
                    transform: isActive ? "translateZ(10px)" : tier === "warm" ? "translateZ(5px)" : "translateZ(0px)",
                    animation: (isActive || tier === "warm") ? `strategyLift 2.1s ease-in-out ${idx * 0.1}s infinite` : undefined,
                    transition: "transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease",
                  }}
                  title={ev?.message ?? ev?.msg ?? "No recent events"}
                >
                  {(isActive || tier === "warm") && (
                    <span
                      style={{
                        position: "absolute",
                        inset: 0,
                        background: "linear-gradient(120deg, transparent 0%, rgba(10,132,255,0.32) 48%, transparent 78%)",
                        animation: `strategyAura 1.7s ease-in-out ${idx * 0.06}s infinite`,
                        pointerEvents: "none",
                      }}
                    />
                  )}
                  {agent}
                </div>
                {!isLast && (
                  <div
                    style={{
                      width: 18,
                      height: 8,
                      borderRadius: 999,
                      background: isActive ? "rgba(10,132,255,0.24)" : "rgba(235,235,245,0.15)",
                      margin: "0 4px",
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    {(isActive || tier === "warm") && (
                      <span
                        style={{
                          position: "absolute",
                          inset: 0,
                          background: "linear-gradient(90deg, transparent 0%, #0A84FF 50%, transparent 100%)",
                          animation: `strategyFlow ${isActive ? "1.25s" : "1.9s"} linear ${idx * 0.08}s infinite`,
                        }}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div style={{
          fontSize: 11,
          color: "rgba(235,235,245,0.35)",
          marginTop: 8,
        }}>
          Desliza horizontalmente para ver todo el pipeline.
        </div>
      </div>

      {/* Active Strategies */}
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "16px 20px",
          marginBottom: 24,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 14,
          }}
        >
          Active Strategies
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {activeStrategies.map((s) => (
            <span
              key={s}
              style={{
                background: "rgba(48,209,88,0.15)",
                color: "#30D158",
                borderRadius: 8,
                padding: "6px 14px",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: MONO,
              }}
            >
              {formatStrategy(s)}
            </span>
          ))}
        </div>
      </div>

      {/* Strategy Confidence List */}
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "rgba(235,235,245,0.6)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: 14,
        }}
      >
        Confidence Scores
      </div>

      {confidences.length === 0 ? (
        <div
          style={{
            background: "#1C1C1E",
            borderRadius: 12,
            padding: "40px 24px",
            textAlign: "center",
            color: "rgba(235,235,245,0.3)",
            fontSize: 15,
          }}
        >
          No confidence data available
        </div>
      ) : (
        <div
          style={{
            background: "#1C1C1E",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {confidences.map((c, idx) => {
            const pct = Math.max(0, Math.min(100, Number(c.confidence) * 100));
            const color = confBarColor(Number(c.confidence));
            const label = confLabel(Number(c.confidence));
            const isLast = idx === confidences.length - 1;
            return (
              <div
                key={c.strategy}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: "16px 20px",
                  borderBottom: isLast
                    ? "none"
                    : "0.5px solid rgba(84,84,88,0.3)",
                }}
              >
                {/* Name + meta */}
                <div style={{ minWidth: 160, flexShrink: 0 }}>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: "#FFFFFF",
                      marginBottom: 3,
                    }}
                  >
                    {formatStrategy(c.strategy)}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "rgba(235,235,245,0.3)",
                    }}
                  >
                    {Number(c.total_trades)} trades · score{" "}
                    {Number(c.total_score) >= 0 ? "+" : ""}
                    {Number(c.total_score)}
                  </div>
                </div>

                {/* Bar */}
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      height: 4,
                      background: "rgba(120,120,128,0.36)",
                      borderRadius: 2,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${pct}%`,
                        background: color,
                        borderRadius: 2,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>

                {/* Percent */}
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    fontFamily: MONO,
                    color,
                    minWidth: 48,
                    textAlign: "right",
                  }}
                >
                  {pct.toFixed(0)}%
                </div>

                {/* Label badge */}
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color,
                    background: `${color}18`,
                    borderRadius: 6,
                    padding: "3px 10px",
                    minWidth: 64,
                    textAlign: "center",
                    flexShrink: 0,
                  }}
                >
                  {label}
                </div>

                {/* Chevron */}
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 18, color: "rgba(235,235,245,0.2)", flexShrink: 0 }}
                >
                  chevron_right
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
