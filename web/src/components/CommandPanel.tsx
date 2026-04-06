"use client";

import { useEffect, useRef, useState } from "react";
import ConfirmModal from "@/components/ConfirmModal";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  onCommand?: (cmd: string) => void;
}

interface Feedback {
  msg: string;
  ok:  boolean;
}

interface PendingReviewCommand {
  id: number;
  command: string;
  payload: {
    _meta?: {
      traceId?: string;
      requestedBy?: string;
      requestedAt?: string;
      riskLevel?: string;
    };
  } | null;
  created_at: string;
}

interface CommandHistoryItem {
  id: number;
  command: string;
  status: string;
  result: string | null;
  created_at: string;
  executed_at: string | null;
  review: {
    reviewedBy: string;
    reviewedAt: string;
    decision: string;
    reason: string;
  } | null;
}

// ── Icons (inline SVG) ────────────────────────────────────────────────────────

function IconPause() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6"  y="4" width="4" height="16" rx="1.5" />
      <rect x="14" y="4" width="4" height="16" rx="1.5" />
    </svg>
  );
}

function IconPlay() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,3 19,12 5,21" />
    </svg>
  );
}

function IconStop() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

function IconClose() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <line x1="18" y1="6"  x2="6"  y2="18" />
      <line x1="6"  y1="6"  x2="18" y2="18" />
    </svg>
  );
}

function IconSpinner() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
        <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.75s" repeatCount="indefinite" />
      </path>
    </svg>
  );
}

// ── Button definitions ────────────────────────────────────────────────────────

const ACTIONS = [
  {
    cmd:     "pause",
    label:   "Pause",
    icon:    <IconPause />,
    color:   "var(--health-warn)",
    bg:      "rgba(245,158,11,0.12)",
    border:  "rgba(245,158,11,0.25)",
    danger:  false,
  },
  {
    cmd:     "resume",
    label:   "Resume",
    icon:    <IconPlay />,
    color:   "var(--buy)",
    bg:      "rgba(34,197,94,0.12)",
    border:  "rgba(34,197,94,0.25)",
    danger:  false,
  },
  {
    cmd:     "kill",
    label:   "Kill Bot",
    icon:    <IconStop />,
    color:   "var(--sell)",
    bg:      "rgba(239,68,68,0.12)",
    border:  "rgba(239,68,68,0.25)",
    danger:  true,
  },
  {
    cmd:     "close_all",
    label:   "Close All",
    icon:    <IconClose />,
    color:   "var(--sell)",
    bg:      "rgba(239,68,68,0.12)",
    border:  "rgba(239,68,68,0.25)",
    danger:  true,
  },
] as const;

// ── Keyframes ─────────────────────────────────────────────────────────────────

const KEYFRAMES = `
  @keyframes toastFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes statusPulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }
`;

// ── Component ─────────────────────────────────────────────────────────────────

export default function CommandPanel({ onCommand }: Props) {
  const [loading,   setLoading]   = useState<string | null>(null);
  const [feedback,  setFeedback]  = useState<Feedback | null>(null);
  const [botState,  setBotState]  = useState<"running" | "paused" | "unknown">("unknown");
  const [pendingReviews, setPendingReviews] = useState<PendingReviewCommand[]>([]);
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [history, setHistory] = useState<CommandHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [pendingDanger, setPendingDanger] = useState<string | null>(null);
  const feedTO                    = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Poll bot state
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const r = await fetch("/api/status");
        const d = await r.json();
        if (!active) return;
        const s = (d?.state ?? d?.status ?? "").toLowerCase();
        if (s === "running" || s === "active") setBotState("running");
        else if (s === "paused") setBotState("paused");
        else setBotState("unknown");
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, 5_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Poll pending high-risk commands awaiting approval
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const r = await fetch("/api/commands?limit=20");
        const d = await r.json();
        if (!active) return;
        const items = Array.isArray(d?.items)
          ? (d.items as PendingReviewCommand[])
          : [];
        setPendingReviews(items);
      } catch {
        if (active) setPendingReviews([]);
      }
    };
    poll();
    const id = setInterval(poll, 8_000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  function showFeedback(msg: string, ok: boolean) {
    setFeedback({ msg, ok });
    if (feedTO.current) clearTimeout(feedTO.current);
    feedTO.current = setTimeout(() => setFeedback(null), 4_000);
  }

  async function send(cmd: string, danger: boolean) {
    if (danger) { setPendingDanger(cmd); return; }
    setLoading(cmd);
    try {
      const r = await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command: cmd, payload: { source: "dashboard-ui" } }),
      });
      const d = await r.json();
      if (d?.ok !== false) {
        showFeedback(d?.requiresApproval ? `${cmd} queued for approval` : `${cmd} acknowledged`, true);
        if (cmd === "pause")  setBotState("paused");
        if (cmd === "resume") setBotState("running");
        onCommand?.(cmd);
      } else {
        showFeedback(d?.error?.message ?? d?.error ?? "Command failed", false);
      }
    } catch {
      showFeedback("Network error", false);
    } finally {
      setLoading(null);
    }
  }

  async function executeDangerous(cmd: string) {
    setPendingDanger(null);
    setLoading(cmd);
    try {
      const payload: Record<string, unknown> = {
        source: "dashboard-ui",
        confirmed: true,
        reason: `Manual confirmation from dashboard for ${cmd}`,
      };

      const r = await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command: cmd, payload }),
      });
      const d = await r.json();
      if (d?.ok !== false) {
        const ack = d?.requiresApproval
          ? `${cmd} queued for approval`
          : `${cmd} acknowledged`;
        showFeedback(ack, true);
        if (cmd === "pause")  setBotState("paused");
        if (cmd === "resume") setBotState("running");
        onCommand?.(cmd);
      } else {
        const msg = d?.error?.message ?? d?.error ?? "Command failed";
        showFeedback(msg, false);
      }
    } catch {
      showFeedback("Network error", false);
    } finally {
      setLoading(null);
    }
  }

  async function reviewCommand(id: number, decision: "approve" | "deny") {
    const defaultReason =
      decision === "approve"
        ? "Approved from dashboard review queue"
        : "Denied from dashboard review queue";
    const reason = window.prompt(
      `Reason for ${decision} (min 5 chars):`,
      defaultReason
    );
    if (!reason) return;

    setReviewingId(id);
    try {
      const r = await fetch("/api/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: decision, id, reason }),
      });
      const d = await r.json();
      if (d?.ok) {
        setPendingReviews((prev) => prev.filter((item) => item.id !== id));
        showFeedback(`Command #${id} ${decision}d`, true);
        // Refresh history after a review action
        fetchHistory();
      } else {
        const msg = d?.error?.message ?? d?.error ?? "Review failed";
        showFeedback(msg, false);
      }
    } catch {
      showFeedback("Network error while reviewing command", false);
    } finally {
      setReviewingId(null);
    }
  }

  async function fetchHistory() {
    try {
      const r = await fetch("/api/commands?history=1&limit=5");
      const d = await r.json();
      setHistory(Array.isArray(d?.items) ? (d.items as CommandHistoryItem[]) : []);
    } catch {
      setHistory([]);
    }
  }

  const stateColor =
    botState === "running" ? "var(--buy)"
    : botState === "paused" ? "#FF9F0A"
    : "var(--text-muted)";

  const stateLabel =
    botState === "running" ? "Running"
    : botState === "paused" ? "Paused"
    : "Unknown";

  return (
    <div style={{
      background: "linear-gradient(180deg, rgba(19,24,32,0.92) 0%, rgba(12,15,20,0.96) 100%)",
      borderRadius: 14,
      border: "1px solid var(--border)",
      padding:       16,
      boxShadow: "0 20px 34px rgba(0,0,0,0.35)",
      fontFamily:    '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
    }}>
      <style>{KEYFRAMES}</style>

      {/* Header row */}
      <div style={{
        display:        "flex",
        alignItems:     "center",
        justifyContent: "space-between",
        marginBottom:   16,
      }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
          Bot Controls
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{
            width:        7,
            height:       7,
            borderRadius: "50%",
            background:   stateColor,
            display:      "inline-block",
            flexShrink:   0,
            animation:    botState === "running" ? "statusPulse 2s ease-in-out infinite" : undefined,
          }} />
          <span style={{ fontSize: 13, color: stateColor, fontWeight: 600 }}>
            {stateLabel}
          </span>
        </div>
      </div>

      {/* 2×2 button grid */}
      <div style={{
        display:             "grid",
        gridTemplateColumns: "1fr 1fr",
        gap:                 10,
      }}>
        {ACTIONS.map((action) => {
          const isLoading = loading === action.cmd;
          const disabled  = loading !== null;

          return (
            <button
              key={action.cmd}
              disabled={disabled}
              onClick={() => !disabled && send(action.cmd, action.danger)}
              style={{
                display:        "flex",
                flexDirection:  "column",
                alignItems:     "center",
                justifyContent: "center",
                gap:            6,
                height:         56,
                background:     disabled && !isLoading ? "var(--surface-3)" : action.bg,
                border:         `0.5px solid ${disabled && !isLoading ? "var(--border)" : action.border}`,
                borderRadius:   12,
                color:          disabled && !isLoading ? "var(--text-muted)" : action.color,
                cursor:         disabled ? "not-allowed" : "pointer",
                fontSize:       13,
                fontWeight:     600,
                fontFamily:     "inherit",
                transition:     "opacity 0.15s, transform 0.1s",
                opacity:        disabled && !isLoading ? 0.5 : 1,
              }}
              onMouseEnter={(e) => {
                if (!disabled) (e.currentTarget as HTMLButtonElement).style.opacity = "0.75";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.opacity = disabled && !isLoading ? "0.5" : "1";
              }}
              onMouseDown={(e) => {
                if (!disabled) (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.97)";
              }}
              onMouseUp={(e) => {
                (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)";
              }}
            >
              {isLoading ? <IconSpinner /> : action.icon}
              <span>{isLoading ? "..." : action.label}</span>
            </button>
          );
        })}
      </div>

      {/* Feedback toast */}
      {feedback && (
        <div style={{
          marginTop:    12,
          padding:      "10px 14px",
          background:   feedback.ok ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)",
          borderRadius: 8,
          border:       `0.5px solid ${feedback.ok ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
          fontSize:     13,
          fontWeight:   500,
          color:        feedback.ok ? "var(--buy)" : "var(--sell)",
          animation:    "toastFadeIn 0.2s ease",
        }}>
          {feedback.ok ? "✓ " : "✗ "}{feedback.msg}
        </div>
      )}

      {pendingReviews.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "var(--health-warn)",
              marginBottom: 8,
            }}
          >
            Pending High-Risk Reviews ({pendingReviews.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pendingReviews.slice(0, 3).map((item) => {
              const trace = item.payload?._meta?.traceId ?? "-";
              const risk = item.payload?._meta?.riskLevel ?? "high";
              const createdAt = new Date(item.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              });
              const busy = reviewingId === item.id;

              return (
                <div
                  key={item.id}
                  style={{
                    borderRadius: 10,
                    border: "1px solid rgba(245, 158, 11, 0.3)",
                    background: "rgba(245, 158, 11, 0.08)",
                    padding: 8,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 600 }}>
                      #{item.id} {item.command}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--health-warn)" }}>{risk}</span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-primary)", marginTop: 4 }}>
                    {createdAt} · {trace}
                  </div>
                  <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                    <button
                      disabled={busy}
                      onClick={() => reviewCommand(item.id, "approve")}
                      style={{
                        flex: 1,
                        height: 30,
                        borderRadius: 8,
                        border: "1px solid rgba(34,197,94,0.35)",
                        background: "rgba(34,197,94,0.16)",
                        color: "var(--buy)",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: busy ? "not-allowed" : "pointer",
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      Approve
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => reviewCommand(item.id, "deny")}
                      style={{
                        flex: 1,
                        height: 30,
                        borderRadius: 8,
                        border: "1px solid rgba(239,68,68,0.35)",
                        background: "rgba(239,68,68,0.16)",
                        color: "var(--sell)",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: busy ? "not-allowed" : "pointer",
                        opacity: busy ? 0.6 : 1,
                      }}
                    >
                      Deny
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Command history toggle */}
      <div style={{ marginTop: 12 }}>
        <button
          onClick={() => {
            const next = !showHistory;
            setShowHistory(next);
            if (next) fetchHistory();
          }}
          style={{
            background: "none",
            border: "none",
            color: "var(--text-secondary)",
            fontSize: 12,
            cursor: "pointer",
            padding: 0,
            textDecoration: "underline",
            fontFamily: "inherit",
          }}
        >
          {showHistory ? "Hide history" : "Show recent history"}
        </button>

        {showHistory && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
            {history.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                No resolved commands in the last 24 hours.
              </div>
            ) : (
              history.map((item) => {
                const isDone = item.status === "done";
                const badge = isDone ? "✅" : "❌";
                const resolvedAt = item.executed_at
                  ? new Date(item.executed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : "—";
                return (
                  <div
                    key={item.id}
                    style={{
                      borderRadius: 8,
                      border: `1px solid ${isDone ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
                      background: isDone ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)",
                      padding: "6px 8px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 12 }}>{badge}</span>
                      <span style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 600 }}>
                        #{item.id} {item.command}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: "auto" }}>
                        {resolvedAt}
                      </span>
                    </div>
                    {item.review && (
                      <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 3 }}>
                        {item.review.decision} by {item.review.reviewedBy}
                        {item.review.reason ? ` · ${item.review.reason.slice(0, 60)}` : ""}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Danger confirmation modal */}
      <ConfirmModal
        open={pendingDanger !== null}
        title={pendingDanger === "kill" ? "Kill Bot?" : pendingDanger === "close_all" ? "Close All Positions?" : "Confirm Action"}
        body={
          pendingDanger === "kill"
            ? "This will immediately terminate the trading bot. All open positions will remain open until the broker closes them. Are you sure?"
            : pendingDanger === "close_all"
            ? "This will send close commands to all open positions at market price. This action cannot be undone. Are you sure?"
            : `Are you sure you want to execute ${pendingDanger}?`
        }
        confirmLabel={pendingDanger === "kill" ? "Kill Bot" : pendingDanger === "close_all" ? "Close All" : "Confirm"}
        danger
        onConfirm={() => pendingDanger && executeDangerous(pendingDanger)}
        onCancel={() => setPendingDanger(null)}
      />
    </div>
  );
}
