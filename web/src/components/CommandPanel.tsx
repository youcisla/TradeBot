"use client";

import { useEffect, useRef, useState } from "react";

type BotStatus = "running" | "paused" | "unknown";

interface Feedback {
  msg: string;
  ok: boolean;
}

const COMMANDS = [
  {
    cmd:   "pause",
    label: "PAUSE",
    icon: (
      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="4" width="4" height="16" rx="1" />
        <rect x="14" y="4" width="4" height="16" rx="1" />
      </svg>
    ),
    color:   "#facc15",
    danger:  false,
  },
  {
    cmd:   "resume",
    label: "RESUME",
    icon: (
      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
        <polygon points="5,3 19,12 5,21" />
      </svg>
    ),
    color:   "#22c55e",
    danger:  false,
  },
  {
    cmd:   "kill",
    label: "KILL ALL",
    icon: (
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    ),
    color:   "#f87171",
    danger:  true,
  },
] as const;

export default function CommandPanel() {
  const [loading,    setLoading]    = useState<string | null>(null);
  const [feedback,   setFeedback]   = useState<Feedback | null>(null);
  const [botStatus,  setBotStatus]  = useState<BotStatus>("unknown");
  const [armKill,    setArmKill]    = useState(false);

  const feedTO  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const armTO   = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Poll bot status from /api/status
  useEffect(() => {
    async function fetchStatus() {
      try {
        const res  = await fetch("/api/status");
        const data = await res.json();
        const s    = (data?.status ?? data?.bot_status ?? "").toLowerCase();
        if (s === "paused")  setBotStatus("paused");
        else if (s === "running" || s === "active") setBotStatus("running");
        else setBotStatus("unknown");
      } catch { /* ignore */ }
    }
    fetchStatus();
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, []);

  function showFeedback(msg: string, ok: boolean) {
    setFeedback({ msg, ok });
    if (feedTO.current) clearTimeout(feedTO.current);
    feedTO.current = setTimeout(() => setFeedback(null), 4000);
  }

  async function send(command: string) {
    // KILL requires arm → confirm two-tap
    if (command === "kill" && !armKill) {
      setArmKill(true);
      if (armTO.current) clearTimeout(armTO.current);
      armTO.current = setTimeout(() => setArmKill(false), 3500);
      return;
    }
    setArmKill(false);
    setLoading(command);
    try {
      const res  = await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command }),
      });
      const data = await res.json();
      if (data.ok) {
        showFeedback(`✓ ${command} acknowledged`, true);
        if (command === "pause")  setBotStatus("paused");
        if (command === "resume") setBotStatus("running");
      } else {
        showFeedback(`✗ ${data.error ?? "error"}`, false);
      }
    } catch {
      showFeedback("✗ network error", false);
    } finally {
      setLoading(null);
    }
  }

  const statusColor =
    botStatus === "running" ? "#22c55e"
    : botStatus === "paused" ? "#facc15"
    : "#475569";

  const statusLabel =
    botStatus === "running" ? "RUNNING"
    : botStatus === "paused" ? "PAUSED"
    : "UNKNOWN";

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-4 flex flex-col gap-3">

      {/* Header + status */}
      <div className="flex items-center justify-between">
        <span className="text-matrix-dim text-xs uppercase tracking-widest">Command Panel</span>
        <div className="flex items-center gap-1.5">
          <span
            style={{
              display: "inline-block",
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: statusColor,
              boxShadow: botStatus !== "unknown" ? `0 0 6px ${statusColor}` : undefined,
              animation: botStatus === "running" ? "cpulse 2s ease-in-out infinite" : undefined,
            }}
          />
          <span style={{ fontSize: 10, color: statusColor, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Buttons */}
      <div className="flex gap-2 flex-wrap">
        {COMMANDS.map((b) => {
          const isLoading = loading === b.cmd;
          const isArmed   = b.cmd === "kill" && armKill;
          const bg        = isArmed ? b.color : "transparent";
          const textColor = isArmed ? "#000" : b.color;
          const border    = b.color;

          return (
            <button
              key={b.cmd}
              disabled={loading !== null}
              onClick={() => send(b.cmd)}
              title={isArmed ? "Click again to confirm" : undefined}
              style={{
                display:         "flex",
                alignItems:      "center",
                gap:             6,
                padding:         "5px 14px",
                border:          `1px solid ${border}`,
                borderRadius:    4,
                background:      bg,
                color:           textColor,
                fontSize:        11,
                fontFamily:      "'JetBrains Mono', monospace",
                fontWeight:      700,
                letterSpacing:   1,
                cursor:          loading !== null ? "not-allowed" : "pointer",
                opacity:         loading !== null && !isLoading ? 0.35 : 1,
                transition:      "background 0.2s, color 0.2s, box-shadow 0.2s",
                boxShadow:       isArmed ? `0 0 10px ${b.color}` : undefined,
                textTransform:   "uppercase",
              }}
            >
              {isLoading ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
                    <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.7s" repeatCount="indefinite" />
                  </path>
                </svg>
              ) : b.icon}
              {isArmed ? "CONFIRM?" : b.label}
            </button>
          );
        })}
      </div>

      {/* Arm countdown hint */}
      {armKill && (
        <div style={{ fontSize: 10, color: "#f87171", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 0.5 }}>
          ⚠ Click CONFIRM? again to close all trades — arms for 3.5 s
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <div
          style={{
            fontSize:    11,
            fontFamily:  "'JetBrains Mono', monospace",
            color:       feedback.ok ? "#22c55e" : "#f87171",
            borderLeft:  `2px solid ${feedback.ok ? "#22c55e" : "#f87171"}`,
            paddingLeft: 8,
            transition:  "opacity 0.3s",
            letterSpacing: 0.3,
          }}
        >
          {feedback.msg}
        </div>
      )}

      <style>{`
        @keyframes cpulse { 0%,100%{opacity:1} 50%{opacity:0.35} }
      `}</style>
    </div>
  );
}
