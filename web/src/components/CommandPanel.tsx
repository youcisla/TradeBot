"use client";

import { useEffect, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  onCommand?: (cmd: string) => void;
}

interface Feedback {
  msg: string;
  ok:  boolean;
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
    color:   "#FF9F0A",
    bg:      "rgba(255,159,10,0.12)",
    border:  "rgba(255,159,10,0.25)",
    danger:  false,
  },
  {
    cmd:     "resume",
    label:   "Resume",
    icon:    <IconPlay />,
    color:   "#30D158",
    bg:      "rgba(48,209,88,0.12)",
    border:  "rgba(48,209,88,0.25)",
    danger:  false,
  },
  {
    cmd:     "kill",
    label:   "Kill Bot",
    icon:    <IconStop />,
    color:   "#FF453A",
    bg:      "rgba(255,69,58,0.12)",
    border:  "rgba(255,69,58,0.25)",
    danger:  true,
  },
  {
    cmd:     "close_all",
    label:   "Close All",
    icon:    <IconClose />,
    color:   "#FF453A",
    bg:      "rgba(255,69,58,0.12)",
    border:  "rgba(255,69,58,0.25)",
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

  function showFeedback(msg: string, ok: boolean) {
    setFeedback({ msg, ok });
    if (feedTO.current) clearTimeout(feedTO.current);
    feedTO.current = setTimeout(() => setFeedback(null), 4_000);
  }

  async function send(cmd: string, danger: boolean) {
    if (danger && !window.confirm(`Are you sure you want to ${cmd.replace("_", " ")}?`)) return;
    setLoading(cmd);
    try {
      const r = await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command: cmd }),
      });
      const d = await r.json();
      if (d?.ok !== false) {
        showFeedback(`${cmd} acknowledged`, true);
        if (cmd === "pause")  setBotState("paused");
        if (cmd === "resume") setBotState("running");
        onCommand?.(cmd);
      } else {
        showFeedback(d.error ?? "Command failed", false);
      }
    } catch {
      showFeedback("Network error", false);
    } finally {
      setLoading(null);
    }
  }

  const stateColor =
    botState === "running" ? "#30D158"
    : botState === "paused" ? "#FF9F0A"
    : "#8E8E93";

  const stateLabel =
    botState === "running" ? "Running"
    : botState === "paused" ? "Paused"
    : "Unknown";

  return (
    <div style={{
      background:    "#1C1C1E",
      borderRadius:  12,
      padding:       16,
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
        <span style={{ fontSize: 15, fontWeight: 700, color: "#FFFFFF" }}>
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
                background:     disabled && !isLoading ? "rgba(44,44,46,0.5)" : action.bg,
                border:         `0.5px solid ${disabled && !isLoading ? "rgba(84,84,88,0.3)" : action.border}`,
                borderRadius:   10,
                color:          disabled && !isLoading ? "rgba(235,235,245,0.25)" : action.color,
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
          background:   feedback.ok ? "rgba(48,209,88,0.12)" : "rgba(255,69,58,0.12)",
          borderRadius: 8,
          border:       `0.5px solid ${feedback.ok ? "rgba(48,209,88,0.3)" : "rgba(255,69,58,0.3)"}`,
          fontSize:     13,
          fontWeight:   500,
          color:        feedback.ok ? "#30D158" : "#FF453A",
          animation:    "toastFadeIn 0.2s ease",
        }}>
          {feedback.ok ? "✓ " : "✗ "}{feedback.msg}
        </div>
      )}
    </div>
  );
}
