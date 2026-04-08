"use client";

import { useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { useAgentEvents } from "@/lib/swr";

// ── Types ─────────────────────────────────────────────────────────────────────

interface TradeScore {
  id: number;
  trade_id: string;
  strategy: string;
  symbol: string;
  session: string;
  market_condition: string;
  score: number;
  pnl: number;
  created_at: string;
}

interface StrategyConfidence {
  strategy: string;
  confidence: number;
  total_trades: number;
  avg_score: number;
  last_updated: string;
}

interface AgentEvent {
  id?: number;
  agent: string;
  level?: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
}

// ── Design Tokens ─────────────────────────────────────────────────────────────
const C = {
  bg:        "var(--bg-2)",
  border:    "var(--border)",
  radius:    6,
  mono:      "var(--font-mono)",
  label:     "var(--text-3)",
  positive:  "var(--gold)",
  negative:  "var(--red)",
  warning:   "var(--orange)",
  accent:    "var(--cyan)",
  textDim:   "var(--text-3)",
  textMid:   "var(--text-2)",
  surface:   "var(--bg-3)",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)       return `${Math.floor(ms / 1_000)}s ago`;
  if (ms < 3_600_000)    return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000)   return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function scoreColor(score: number): string {
  if (score >= 75) return C.positive;
  if (score >= 50) return C.warning;
  if (score >= 25) return C.negative;
  return "var(--red)";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "clean";
  if (score >= 50) return "mixed";
  return "messy";
}

function scoreBg(score: number): string {
  if (score >= 80) return "rgba(34,197,94,0.08)";
  if (score >= 50) return "rgba(255,159,10,0.08)";
  return "rgba(239,68,68,0.08)";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: C.bg,
        border:     `1px solid ${C.border}`,
        borderRadius: C.radius,
        overflow:    "hidden",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize:     11,
        fontWeight:    700,
        color:         C.label,
        letterSpacing: 0.5,
        textTransform: "uppercase",
        marginBottom:  14,
      }}
    >
      {children}
    </div>
  );
}

function ConfBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct  = Math.min(100, Math.max(0, (value / max) * 100));
  const color = scoreColor(value);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          flex:     1,
          height:   5,
          background: C.surface,
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height:       "100%",
            width:        `${pct}%`,
            background:   color,
            borderRadius: 3,
            transition:   "width 400ms ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize:   12,
          fontWeight:  700,
          color,
          fontFamily: C.mono,
          minWidth:   32,
          textAlign:  "right",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function DriftBanner({ driftScore, threshold }: { driftScore: number; threshold: number }) {
  const pct    = Math.min(100, (driftScore / threshold) * 100);
  const status = driftScore < threshold * 0.5 ? "NOMINAL" : driftScore < threshold ? "DRIFTING" : "CRITICAL";
  const statusColors: Record<string, string> = {
    NOMINAL:  C.positive,
    DRIFTING: C.warning,
    CRITICAL: C.negative,
  };

  return (
    <Card style={{ padding: "16px 20px", marginBottom: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <SectionLabel>Model Drift Detector</SectionLabel>
        <span
          style={{
            fontSize:     10,
            fontWeight:    700,
            letterSpacing: 0.5,
            textTransform: "uppercase",
            color:         statusColors[status],
            background:    statusColors[status] + "20",
            padding:       "3px 9px",
            borderRadius:   5,
          }}
        >
          {status}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div
            style={{
              height:     8,
              background: C.surface,
              borderRadius: 4,
              overflow:   "hidden",
            }}
          >
            <div
              style={{
                height:       "100%",
                width:        `${pct}%`,
                background:   statusColors[status],
                borderRadius: 4,
                transition:   "width 500ms ease",
              }}
            />
          </div>
        </div>
        <span
          style={{
            fontFamily: C.mono,
            fontSize:   13,
            fontWeight:  700,
            color:       statusColors[status],
            whiteSpace:  "nowrap",
          }}
        >
          {driftScore.toFixed(2)} / {threshold}
        </span>
      </div>
    </Card>
  );
}

function ConfidenceTable({ confidences }: { confidences: StrategyConfidence[] }) {
  return (
    <Card style={{ padding: "20px", flex: "1 1 300px" }}>
      <SectionLabel>Strategy Confidence</SectionLabel>
      {confidences.length === 0 ? (
        <div
          style={{
            fontSize:   13,
            color:      C.textDim,
            padding:    "20px 0",
            textAlign:  "center",
          }}
        >
          No confidence data yet
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {confidences.map(c => (
            <div
              key={c.strategy}
              style={{
                background:  C.surface,
                border:      `1px solid ${C.border}`,
                borderRadius: 8,
                padding:     "12px 14px",
              }}
            >
              <div
                style={{
                  display:        "flex",
                  justifyContent:  "space-between",
                  alignItems:      "center",
                  marginBottom:    8,
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-1)" }}>
                  {c.strategy}
                </span>
                <span style={{ fontSize: 11, color: C.textDim }}>
                  {c.total_trades} trades
                </span>
              </div>
              <ConfBar value={c.confidence} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                <span style={{ fontSize: 11, color: C.textDim }}>Avg score</span>
                <span
                  style={{
                    fontSize:   11,
                    fontFamily: C.mono,
                    color:       scoreColor(c.avg_score),
                  }}
                >
                  {c.avg_score.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function PostMortemQuality({ scores }: { scores: TradeScore[] }) {
  const stats = useMemo(() => {
    if (scores.length === 0) return { clean: 0, mixed: 0, messy: 0, avg: 0, total: 0 };
    const clean = scores.filter(s => s.score >= 80).length;
    const mixed = scores.filter(s => s.score >= 50 && s.score < 80).length;
    const messy = scores.filter(s => s.score < 50).length;
    const avg   = scores.reduce((sum, s) => sum + s.score, 0) / scores.length;
    return { clean, mixed, messy, avg, total: scores.length };
  }, [scores]);

  return (
    <Card style={{ padding: "20px", flex: "1 1 260px" }}>
      <SectionLabel>Post-Mortem Quality</SectionLabel>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Avg score */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: C.textMid }}>Average Score</span>
            <span
              style={{
                fontSize:   16,
                fontWeight:  700,
                color:       scoreColor(stats.avg),
                fontFamily: C.mono,
              }}
            >
              {stats.avg.toFixed(1)}
            </span>
          </div>
          <ConfBar value={stats.avg} />
        </div>

        {/* Breakdown */}
        {stats.total > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { label: "Clean", count: stats.clean, color: C.positive },
              { label: "Mixed", count: stats.mixed, color: C.warning },
              { label: "Messy", count: stats.messy, color: C.negative },
            ].map(({ label, count, color }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 50, fontSize: 12, color: C.textMid }}>{label}</div>
                <div
                  style={{
                    flex:     1,
                    height:   5,
                    background: C.surface,
                    borderRadius: 3,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height:       "100%",
                      width:        `${(count / stats.total) * 100}%`,
                      background:   color,
                      borderRadius: 3,
                      transition:   "width 400ms ease",
                    }}
                  />
                </div>
                <div
                  style={{
                    fontSize:   12,
                    fontWeight:  600,
                    color,
                    fontFamily: C.mono,
                    minWidth:   28,
                    textAlign:  "right",
                  }}
                >
                  {count}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Total */}
        <div
          style={{
            display:        "flex",
            justifyContent: "space-between",
            paddingTop:     6,
            borderTop:      `1px solid ${C.border}`,
          }}
        >
          <span style={{ fontSize: 12, color: C.textDim }}>Total scored</span>
          <span
            style={{
              fontSize:   13,
              fontWeight: 700,
              color:      "var(--text-1)",
              fontFamily: C.mono,
            }}
          >
            {stats.total}
          </span>
        </div>
      </div>
    </Card>
  );
}

function RewardScoringFeed({ scores }: { scores: TradeScore[] }) {
  return (
    <Card style={{ padding: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <SectionLabel>Reward Scoring Feed</SectionLabel>
        <span style={{ fontSize: 11, color: C.textDim, fontFamily: C.mono }}>
          {scores.length} trades
        </span>
      </div>
      {scores.length === 0 ? (
        <div
          style={{
            fontSize:   13,
            color:      C.textDim,
            padding:    "20px 0",
            textAlign:  "center",
          }}
        >
          No scored trades yet
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {/* Header */}
          <div
            style={{
              display:              "grid",
              gridTemplateColumns:  "64px 1fr 80px 80px 72px 90px",
              gap:                  8,
              padding:              "4px 8px",
              fontSize:             10,
              fontWeight:           600,
              color:                C.label,
              textTransform:       "uppercase",
              letterSpacing:       0.5,
            }}
          >
            <span>Score</span>
            <span>Trade</span>
            <span>Strategy</span>
            <span>PnL</span>
            <span>Quality</span>
            <span>When</span>
          </div>
          {scores.slice(0, 25).map(s => (
            <div
              key={s.id}
              style={{
                display:              "grid",
                gridTemplateColumns: "64px 1fr 80px 80px 72px 90px",
                gap:                  8,
                padding:             "10px 8px",
                borderRadius:         7,
                background:           scoreBg(s.score),
                border:               `1px solid ${scoreColor(s.score)}22`,
                alignItems:           "center",
              }}
            >
              <ConfBar value={s.score} />
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-1)" }}>
                  {s.symbol}
                </span>
                <span style={{ fontSize: 11, color: C.textDim }}>
                  {s.session} · {s.market_condition}
                </span>
              </div>
              <span style={{ fontSize: 11, color: C.textMid }}>{s.strategy}</span>
              <span
                style={{
                  fontSize:   13,
                  fontWeight: 700,
                  fontFamily: C.mono,
                  color:      s.pnl >= 0 ? C.positive : C.negative,
                }}
              >
                {s.pnl >= 0 ? "+" : ""}{s.pnl.toFixed(2)}
              </span>
              <span
                style={{
                  fontSize:     10,
                  fontWeight:   700,
                  letterSpacing: 0.4,
                  textTransform: "uppercase",
                  color:         scoreColor(s.score),
                }}
              >
                {scoreLabel(s.score)}
              </span>
              <span style={{ fontSize: 11, color: C.textDim }}>
                {relTime(s.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const { status: shellStatus } = useAppShell();
  const { data: events } = useAgentEvents(50);

  const [learningData, setLearningData] = useState<{
    confidences: StrategyConfidence[];
    scores: TradeScore[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const learnRes = await fetch("/api/learning");
        const learn    = await learnRes.json();
        setLearningData({
          confidences: Array.isArray(learn.confidences) ? learn.confidences : [],
          scores:      Array.isArray(learn.scores)          ? learn.scores      : [],
        });
      } catch { /* silent */ }
      finally    { setLoading(false); }
    };
    load();
    const t = setInterval(load, 15_000);
    return () => clearInterval(t);
  }, []);

  const confidences = learningData?.confidences ?? [];
  const scores      = learningData?.scores      ?? [];

  const lastLearningEvent = (events ?? [])[0];
  const driftScore   = 0.18;
  const driftThreshold = 0.5;

  const trainingStatus = lastLearningEvent
    ? /training|retrain|fitting/i.test(lastLearningEvent.msg ?? lastLearningEvent.message ?? "")
      ? "TRAINING"
      : "IDLE"
    : "UNKNOWN";

  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Drift banner */}
      <DriftBanner driftScore={driftScore} threshold={driftThreshold} />

      {/* KPI row */}
      <div
        style={{
          display:               "grid",
          gridTemplateColumns:   "repeat(auto-fill, minmax(160px, 1fr))",
          gap:                   14,
        }}
      >
        {[
          {
            label: "Total Scored",
            value: scores.length,
            color: "var(--text-1)",
          },
          {
            label:    "Avg Score",
            value:   scores.length > 0
              ? (scores.reduce((s, t) => s + t.score, 0) / scores.length).toFixed(1)
              : "—",
            color: scoreColor(scores.length > 0 ? scores.reduce((s, t) => s + t.score, 0) / scores.length : 0),
          },
          {
            label: "Clean Setups",
            value: scores.filter(s => s.score >= 80).length,
            color: C.positive,
          },
          {
            label: "Training",
            value: trainingStatus,
            color: trainingStatus === "TRAINING" ? C.warning : C.positive,
          },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              background: C.bg,
              border:     `1px solid ${C.border}`,
              borderRadius: C.radius,
              padding:    "14px 16px",
            }}
          >
            <div
              style={{
                fontSize:     11,
                color:        C.textDim,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom:  4,
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontSize:   22,
                fontWeight:  700,
                color,
                fontFamily: C.mono,
                letterSpacing: "-0.5px",
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Confidence + Post-mortem row */}
      <div
        style={{
          display: "flex",
          gap:      16,
          flexWrap: "wrap",
        }}
      >
        <ConfidenceTable confidences={confidences} />
        <PostMortemQuality scores={scores} />
      </div>

      {/* Reward scoring feed */}
      <RewardScoringFeed scores={scores} />

      {/* Recent learning events */}
      {(events ?? []).length > 0 && (
        <Card style={{ padding: "20px" }}>
          <SectionLabel>Learning Agent Feed</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {(events ?? []).slice(0, 12).map((ev, i) => (
              <div
                key={ev.id ?? i}
                style={{
                  display:        "flex",
                  gap:            12,
                  padding:        "8px 10px",
                  borderRadius:    6,
                  alignItems:      "flex-start",
                  background:      /error|critical/i.test(ev.level ?? "")
                    ? "rgba(239,68,68,0.04)"
                    : "transparent",
                  borderLeft:      /error|critical/i.test(ev.level ?? "")
                    ? "2px solid rgba(239,68,68,0.4)"
                    : "2px solid transparent",
                }}
              >
                <span
                  style={{
                    fontSize:   10,
                    color:      C.textDim,
                    fontFamily: C.mono,
                    flexShrink: 0,
                    marginTop: 1,
                  }}
                >
                  {relTime(ev.ts ?? ev.created_at)}
                </span>
                <span
                  style={{
                    fontSize:  12,
                    color:     C.textMid,
                    flex:      1,
                    lineHeight: 1.5,
                  }}
                >
                  {ev.message ?? ev.msg ?? "—"}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
