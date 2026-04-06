"use client";

import { useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";

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

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return `${Math.floor(ms / 1_000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function scoreColor(score: number): string {
  if (score >= 75) return "var(--buy)";
  if (score >= 50) return "var(--health-warn)";
  if (score >= 25) return "var(--sell)";
  return "var(--agent-risk)";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "clean";
  if (score >= 50) return "mixed";
  return "messy";
}

function scoreBg(score: number): string {
  if (score >= 80) return "rgba(34,197,94,0.10)";
  if (score >= 50) return "rgba(255,159,10,0.10)";
  return "rgba(239,68,68,0.10)";
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

function ConfBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          width: `${pct}%`,
          background: scoreColor(value),
          transition: "width 400ms ease",
        }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: scoreColor(value), fontFamily: "var(--font-mono-stack)", minWidth: 32, textAlign: "right" }}>
        {value}
      </span>
    </div>
  );
}

function DriftBanner({ driftScore, threshold }: { driftScore: number; threshold: number }) {
  const pct = Math.min(100, (driftScore / threshold) * 100);
  const status = driftScore < threshold * 0.5 ? "NOMINAL" : driftScore < threshold ? "DRIFTING" : "CRITICAL";

  const statusColors: Record<string, string> = { NOMINAL: "var(--buy)", DRIFTING: "var(--health-warn)", CRITICAL: "var(--sell)" };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "16px 20px",
      marginBottom: 20,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <SectionLabel>Model Drift Detector</SectionLabel>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase",
          color: statusColors[status],
          background: statusColors[status] + "20",
          padding: "3px 9px", borderRadius: 5,
        }}>
          {status}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ flex: 1 }}>
          <div style={{ height: 8, background: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{
              height: "100%",
              width: `${pct}%`,
              background: statusColors[status],
              transition: "width 500ms ease",
            }} />
          </div>
        </div>
        <span style={{ fontFamily: "var(--font-mono-stack)", fontSize: 13, fontWeight: 700, color: statusColors[status] }}>
          {driftScore.toFixed(2)} / {threshold}
        </span>
      </div>
    </div>
  );
}

function ConfidenceTable({ confidences }: { confidences: StrategyConfidence[] }) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "1 1 340px",
    }}>
      <SectionLabel>Strategy Confidence</SectionLabel>
      {confidences.length === 0 ? (
        <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "20px 0", textAlign: "center" }}>
          No confidence data yet
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {confidences.map(c => (
            <div key={c.strategy} style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "12px 14px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{c.strategy}</span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {c.total_trades} trades
                </span>
              </div>
              <ConfBar value={c.confidence} />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Avg score</span>
                <span style={{ fontSize: 11, fontFamily: "var(--font-mono-stack)", color: scoreColor(c.avg_score) }}>
                  {c.avg_score.toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RewardScoringFeed({ scores }: { scores: TradeScore[] }) {
  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "2 1 500px",
    }}>
      <SectionLabel>Reward Scoring Feed · {scores.length} trades</SectionLabel>
      {scores.length === 0 ? (
        <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "20px 0", textAlign: "center" }}>
          No scored trades yet
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {/* Header */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "60px 1fr 80px 80px 70px 90px",
            gap: 8,
            padding: "6px 10px",
            fontSize: 10, fontWeight: 600, color: "var(--text-muted)",
            textTransform: "uppercase", letterSpacing: 0.5,
          }}>
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
                display: "grid",
                gridTemplateColumns: "60px 1fr 80px 80px 70px 90px",
                gap: 8, padding: "9px 10px",
                borderRadius: 7,
                background: scoreBg(s.score),
                border: `1px solid ${scoreColor(s.score)}22`,
                alignItems: "center",
              }}
            >
              {/* Score */}
              <div>
                <ConfBar value={s.score} />
              </div>
              {/* Trade */}
              <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{s.symbol}</span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{s.session} · {s.market_condition}</span>
              </div>
              {/* Strategy */}
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.strategy}</span>
              {/* PnL */}
              <span style={{
                fontSize: 13, fontWeight: 700, fontFamily: "var(--font-mono-stack)",
                color: s.pnl >= 0 ? "var(--buy)" : "var(--sell)",
              }}>
                {s.pnl >= 0 ? "+" : ""}{s.pnl.toFixed(2)}
              </span>
              {/* Quality */}
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: 0.4, textTransform: "uppercase",
                color: scoreColor(s.score),
              }}>
                {scoreLabel(s.score)}
              </span>
              {/* When */}
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {relTime(s.created_at)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PostMortemQuality({ scores }: { scores: TradeScore[] }) {
  const stats = useMemo(() => {
    if (scores.length === 0) return { clean: 0, mixed: 0, messy: 0, avg: 0, total: 0 };
    const clean = scores.filter(s => s.score >= 80).length;
    const mixed = scores.filter(s => s.score >= 50 && s.score < 80).length;
    const messy = scores.filter(s => s.score < 50).length;
    const avg = scores.reduce((sum, s) => sum + s.score, 0) / scores.length;
    return { clean, mixed, messy, avg, total: scores.length };
  }, [scores]);

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--card-border)",
      borderRadius: "var(--card-radius)",
      padding: "20px",
      flex: "1 1 260px",
    }}>
      <SectionLabel>Post-Mortem Quality</SectionLabel>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Avg score */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Average Score</span>
            <span style={{ fontSize: 16, fontWeight: 700, color: scoreColor(stats.avg), fontFamily: "var(--font-mono-stack)" }}>
              {stats.avg.toFixed(1)}
            </span>
          </div>
          <ConfBar value={stats.avg} />
        </div>

        {/* Breakdown */}
        {stats.total > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { label: "Clean", count: stats.clean, color: "var(--buy)" },
              { label: "Mixed", count: stats.mixed, color: "var(--health-warn)" },
              { label: "Messy", count: stats.messy, color: "var(--sell)" },
            ].map(({ label, count, color }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 50, fontSize: 12, color: "var(--text-secondary)" }}>{label}</div>
                <div style={{ flex: 1, height: 6, background: "var(--surface-2)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{
                    height: "100%",
                    width: `${(count / stats.total) * 100}%`,
                    background: color,
                    transition: "width 400ms ease",
                  }} />
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color, fontFamily: "var(--font-mono-stack)", minWidth: 36, textAlign: "right" }}>
                  {count}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Total */}
        <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 4, borderTop: "1px solid var(--border)" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Total scored</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono-stack)" }}>
            {stats.total}
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const { status: shellStatus } = useAppShell();

  const [learningData, setLearningData] = useState<{
    confidences: StrategyConfidence[];
    scores: TradeScore[];
  } | null>(null);
  const [events,  setEvents]  = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);

  // Poll learning data
  useEffect(() => {
    const load = async () => {
      try {
        const [learnRes, eventsRes] = await Promise.all([
          fetch("/api/learning"),
          fetch("/api/events?agent=learning&limit=50"),
        ]);
        const learn = await learnRes.json();
        const evts  = await eventsRes.json();
        setLearningData({
          confidences: Array.isArray(learn.confidences) ? learn.confidences : [],
          scores:      Array.isArray(learn.scores)      ? learn.scores      : [],
        });
        setEvents(Array.isArray(evts) ? evts : []);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 15_000);
    return () => clearInterval(t);
  }, []);

  const confidences = learningData?.confidences ?? [];
  const scores      = learningData?.scores      ?? [];

  // Drift score: use last learning event score or derive from avg
  const lastLearningEvent = events[0];
  const driftScore = 0.18; // placeholder — would come from model_drift table
  const driftThreshold = 0.5;

  // Model training status (from last event)
  const trainingStatus = lastLearningEvent
    ? /training|retrain|fitting/i.test(lastLearningEvent.msg ?? lastLearningEvent.message ?? "")
      ? "TRAINING"
      : "IDLE"
    : "UNKNOWN";

  const MONO = "var(--font-mono-stack)";

  return (
    <>
      {/* Drift banner */}
      <DriftBanner driftScore={driftScore} threshold={driftThreshold} />

      {/* KPI row */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: 12,
        marginBottom: 20,
      }}>
        {[
          { label: "Total Scored",   value: scores.length,      color: "var(--text-primary)" },
          { label: "Avg Score",      value: scores.length > 0 ? (scores.reduce((s, t) => s + t.score, 0) / scores.length).toFixed(1) : "—", color: scoreColor(scores.length > 0 ? scores.reduce((s, t) => s + t.score, 0) / scores.length : 0) },
          { label: "Clean Setups",   value: scores.filter(s => s.score >= 80).length, color: "var(--buy)" },
          { label: "Training",       value: trainingStatus,       color: trainingStatus === "TRAINING" ? "var(--health-warn)" : "var(--buy)" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--card-radius)", padding: "14px 16px",
          }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: MONO, letterSpacing: "-0.5px" }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Confidence + post-mortem row */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        <ConfidenceTable confidences={confidences} />
        <PostMortemQuality scores={scores} />
      </div>

      {/* Reward scoring feed */}
      <RewardScoringFeed scores={scores} />

      {/* Recent learning events */}
      {events.length > 0 && (
        <div style={{
          background: "var(--card-bg)",
          border: "1px solid var(--card-border)",
          borderRadius: "var(--card-radius)",
          padding: "20px",
          marginTop: 20,
        }}>
          <SectionLabel>Learning Agent Feed</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {events.slice(0, 15).map((ev, i) => (
              <div
                key={ev.id ?? i}
                style={{
                  display: "flex", gap: 12, padding: "8px 10px",
                  borderRadius: 6, alignItems: "flex-start",
                  background: /error|critical/i.test(ev.level ?? "") ? "rgba(239,68,68,0.04)" : "transparent",
                  borderLeft: /error|critical/i.test(ev.level ?? "") ? "2px solid rgba(239,68,68,0.4)" : "2px solid transparent",
                }}
              >
                <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: MONO, flexShrink: 0, marginTop: 1 }}>
                  {relTime(ev.ts ?? ev.created_at)}
                </span>
                <span style={{ fontSize: 12, color: "var(--text-secondary)", flex: 1, lineHeight: 1.5 }}>
                  {ev.message ?? ev.msg ?? "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
