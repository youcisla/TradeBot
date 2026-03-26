"use client";
import React, { useEffect } from "react";

type AgentEvent = {
  agent: string;
  level: string;
  msg: string;
  ts: string | null;
  [k: string]: unknown;
};

const AGENTS = [
  { key: "market",        label: "Market",      color: "#00d4ff" },
  { key: "analysis",      label: "Analysis",    color: "#f5c518" },
  { key: "strategy",      label: "Strategy",    color: "#00ff88" },
  { key: "deepseek",      label: "DeepSeek",    color: "#d500f9" },
  { key: "council",       label: "Council",     color: "#ff9d00" },
  { key: "risk",          label: "Risk",        color: "#ff4455" },
  { key: "execution",     label: "Execution",   color: "#f0f0f0" },
  { key: "trade_manager", label: "TradeMgr",    color: "#bf7fff" },
  { key: "learning",      label: "Learning",    color: "#4da6ff" },
  { key: "logging",       label: "Logging",     color: "#5c6a78" },
];

function timeAgo(ts: string | number | null | undefined): string {
  if (!ts) return "idle";
  const now = Date.now();
  const t = typeof ts === "string" ? new Date(ts).getTime() : ts;
  const s = Math.floor((now - t) / 1000);
  if (s < 2) return "just now";
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  return Math.floor(s / 3600) + "h ago";
}

function crewmateSVG() {
  return (
    <svg className="crewmate" viewBox="0 0 60 80" width="72" height="96">
      <ellipse className="crewmate-body" cx="30" cy="38" rx="22" ry="30" fill="var(--agent-color)" stroke="#222" strokeWidth="3" />
      <rect x="16" y="22" width="28" height="12" rx="6" fill="#fff" stroke="#222" strokeWidth="2" />
      <ellipse cx="30" cy="70" rx="10" ry="6" fill="#222" />
      <ellipse cx="20" cy="76" rx="5" ry="3" fill="#222" />
      <ellipse cx="40" cy="76" rx="5" ry="3" fill="#222" />
    </svg>
  );
}

export default function AgentTheater() {
  const lastEventsRef = React.useRef<Record<string, AgentEvent>>({});
  const [lastEventTimestamps, setLastEventTimestamps] = React.useState<Record<string, number>>({});
  const [agentStates, setAgentStates] = React.useState<Record<string, string>>({});
  const [speechBubbles, setSpeechBubbles] = React.useState<Record<string, string>>({});

  const animationTimeouts = React.useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const speechTimeouts = React.useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // Poll events
  useEffect(() => {
    async function pollEvents() {
      try {
        const res = await fetch("/api/events?limit=20");
        const data = await res.json();
        const rawEvents = Array.isArray(data) ? data : (data.events ?? []);
        if (!rawEvents.length) return;

        const events: AgentEvent[] = rawEvents.map((ev: Record<string, unknown>) => ({
          ...ev,
          msg: (ev.msg ?? ev.message ?? "") as string,
          ts: (ev.ts ?? ev.created_at ?? null) as string | null,
        }));
        const latest: Record<string, AgentEvent> = {};
        events.forEach((ev: AgentEvent) => {
          const key = (ev.agent || "").toLowerCase();
          if (!latest[key]) latest[key] = ev;
        });
        AGENTS.forEach((agent) => {
          const key = agent.key;
          const ev = latest[key];
          if (ev && (!lastEventsRef.current[key] || lastEventsRef.current[key].ts !== ev.ts)) {
            lastEventsRef.current[key] = ev;
            setLastEventTimestamps((prev) => ({ ...prev, [key]: ev.ts ? new Date(ev.ts).getTime() : Date.now() }));
            let state = "idle";
            if (ev.level === "warn" || ev.level === "error") state = "alert";
            else if (ev.level === "info") state = "active";
            setAgentStates((prev) => ({ ...prev, [key]: state }));
            if (ev.msg) {
              setSpeechBubbles((prev) => ({ ...prev, [key]: ev.msg.length > 60 ? ev.msg.slice(0, 57) + "..." : ev.msg }));
              clearTimeout(speechTimeouts.current[key]);
              speechTimeouts.current[key] = setTimeout(() => {
                setSpeechBubbles((prev) => ({ ...prev, [key]: "" }));
              }, 3000);
            }
            clearTimeout(animationTimeouts.current[key]);
            animationTimeouts.current[key] = setTimeout(() => {
              setAgentStates((prev) => ({ ...prev, [key]: "idle" }));
            }, state === "active" ? 800 : state === "alert" ? 1200 : 2000);
          }
        });
      } catch {
        // Network error, do nothing
      }
    }
    const interval = setInterval(pollEvents, 800);
    pollEvents();
    return () => {
      clearInterval(interval);
      Object.values(animationTimeouts.current).forEach((id) => clearTimeout(id));
      Object.values(speechTimeouts.current).forEach((id) => clearTimeout(id));
    };
  }, []);

  // Idle fallback
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      AGENTS.forEach((agent) => {
        const key = agent.key;
        if (!lastEventTimestamps[key] || now - lastEventTimestamps[key] > 3000) {
          setAgentStates((prev) => ({ ...prev, [key]: "idle" }));
        }
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [lastEventTimestamps]);

  return (
    <div style={{ minHeight: "100vh", background: "#080808", color: "#c0ccd8", fontFamily: "'JetBrains Mono', monospace" }}>
      {/* Page header */}
      <div style={{ marginTop: 32, textAlign: "center" }}>
        <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase" }}>
          Visualisation
        </div>
        <h1 style={{ fontSize: 20, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: "#00ff88", textShadow: "0 0 20px rgba(0,255,136,0.3)", marginTop: 2 }}>
          Agent Theater
        </h1>
      </div>

      <div className="theater" style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 56, marginTop: 72, marginBottom: 48, flexWrap: "wrap" }}>
        {AGENTS.map((agent) => {
          const state = agentStates[agent.key] || "idle";
          return (
            <div
              key={agent.key}
              className={`agent ${agent.label} ${state}`}
              id={`agent-${agent.key}`}
              style={{ position: "relative", width: 90, display: "flex", flexDirection: "column", alignItems: "center", "--agent-color": agent.color } as React.CSSProperties}
            >
              <div
                className={`speech-bubble${speechBubbles[agent.key] ? " active" : ""}`}
                style={{
                  position: "absolute", top: -56, left: "50%", transform: "translateX(-50%)",
                  background: "#0a0a12", color: agent.color,
                  border: `1px solid rgba(${hexToRgb(agent.color)},0.4)`,
                  borderRadius: 8, padding: "6px 14px",
                  fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                  whiteSpace: "nowrap",
                  opacity: speechBubbles[agent.key] ? 1 : 0,
                  pointerEvents: "none", transition: "opacity 0.3s",
                  zIndex: 2, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis",
                }}
              >
                {speechBubbles[agent.key]}
              </div>
              {crewmateSVG()}
              <div style={{ marginTop: 10, fontSize: 11, color: agent.color, textAlign: "center", textShadow: "0 0 2px #000", letterSpacing: 1 }}>{agent.label}</div>
            </div>
          );
        })}
      </div>

      {/* Status bar */}
      <div style={{
        width: "100%", background: "#0a0a12",
        borderTop: "1px solid #1c1c28",
        fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
        padding: "10px 24px", display: "flex", justifyContent: "center",
        gap: 24, flexWrap: "wrap",
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 10,
      }}>
        {AGENTS.map((agent) => {
          const lastTs = lastEventTimestamps[agent.key];
          const lastLevel = lastEventsRef.current[agent.key]?.level ?? "idle";
          let dotBg = "#00ff88";
          let dotShadow = "#00ff88";
          if (lastLevel === "warn") { dotBg = "#f5c518"; dotShadow = "#f5c518"; }
          else if (lastLevel === "error") { dotBg = "#ff4455"; dotShadow = "#ff4455"; }
          else if (lastLevel === "idle" || !lastTs) { dotBg = "#1c1c28"; dotShadow = "rgba(28,28,40,0)"; }
          return (
            <span key={agent.key}>
              <span style={{
                display: "inline-block", width: 10, height: 10, borderRadius: "50%",
                marginRight: 6, verticalAlign: "middle",
                background: dotBg,
                boxShadow: `0 0 4px ${dotShadow}`,
              }} />
              <span style={{ color: agent.color, fontSize: 9, marginLeft: 2 }}>{agent.label}: {timeAgo(lastTs)}</span>
            </span>
          );
        })}
      </div>

      <style>{`
        .crewmate-body { transition: filter 0.2s; }
        .agent.idle .crewmate { animation: float 2s ease-in-out infinite; }
        .agent.active .crewmate { animation: bounce 0.5s cubic-bezier(.5,1.8,.5,1) 1; }
        .agent.alert .crewmate { animation: shake 0.5s linear 2, flash 0.5s linear 2; }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
        @keyframes bounce { 0% { transform: translateY(0);} 30% { transform: translateY(-18px);} 60% { transform: translateY(0);} 100% { transform: translateY(-6px);} }
        @keyframes shake { 0%, 100% { transform: translateX(0);} 20% { transform: translateX(-6px);} 40% { transform: translateX(6px);} 60% { transform: translateX(-6px);} 80% { transform: translateX(6px);} }
        @keyframes flash { 0%, 100% { filter: brightness(1);} 50% { filter: brightness(2);} }
      `}</style>
    </div>
  );
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `${r},${g},${b}`;
}
