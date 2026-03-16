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
  { key: "market",       label: "Market",       color: "#00ccff" },
  { key: "analysis",     label: "Analysis",     color: "#ffcc00" },
  { key: "strategy",     label: "Strategy",     color: "#ff9900" },
  { key: "risk",         label: "Risk",         color: "#ff4444" },
  { key: "execution",    label: "Execution",    color: "#00ff88" },
  { key: "trademanager", label: "TradeManager", color: "#ff44ff" },
  { key: "learning",     label: "Learning",     color: "#aa44ff" },
  { key: "logging",      label: "Logging",      color: "#0904ff" },
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
    <div style={{ minHeight: "100vh", background: "#0a0f0a", color: "#00ff88", fontFamily: "'Courier New', monospace" }}>
      <h1 style={{ marginTop: 32, color: "#00ff88", fontSize: "2rem", textAlign: "center" }}>Agent Theater</h1>
      <div className="theater" style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 56, marginTop: 72, marginBottom: 48 }}>
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
                style={{ position: "absolute", top: -56, left: "50%", transform: "translateX(-50%)", background: "#111", color: "#00ff88", border: "2px solid #00ff88", borderRadius: 8, padding: "6px 14px", fontSize: 12, fontFamily: "'Courier New', monospace", whiteSpace: "nowrap", opacity: speechBubbles[agent.key] ? 1 : 0, pointerEvents: "none", transition: "opacity 0.3s", zIndex: 2, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}
              >
                {speechBubbles[agent.key]}
              </div>
              {crewmateSVG()}
              <div className="agent-label" style={{ marginTop: 10, fontSize: 13, color: "#00ff88", textAlign: "center", textShadow: "0 0 2px #000", letterSpacing: 1 }}>{agent.label}</div>
            </div>
          );
        })}
      </div>
      <div className="status-bar" style={{ width: "100vw", background: "#111", color: "#00ff88", fontFamily: "'Courier New', monospace", fontSize: 14, padding: "10px 0 8px 0", display: "flex", justifyContent: "center", gap: 32, borderTop: "2px solid #00ff88", position: "fixed", bottom: 0, left: 0, zIndex: 10 }}>
        {AGENTS.map((agent) => {
          const lastTs = lastEventTimestamps[agent.key];
          const lastLevel = lastEventsRef.current[agent.key]?.level ?? "idle";
          let dotClass = "idle";
          if (lastLevel === "warn") dotClass = "warn";
          else if (lastLevel === "error") dotClass = "error";
          else if (lastLevel === "info") dotClass = "";
          return (
            <span key={agent.key}>
              <span className={`status-dot ${dotClass}`} style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", marginRight: 6, verticalAlign: "middle", background: dotClass === "warn" ? "#ffcc00" : dotClass === "error" ? "#ff4444" : dotClass === "idle" ? "#444" : "#00ff88", boxShadow: `0 0 4px ${dotClass === "warn" ? "#ffcc00" : dotClass === "error" ? "#ff4444" : dotClass === "idle" ? "#222" : "#00ff88"}` }} />
              <span className="status-label" style={{ color: "#00ff88", fontSize: 13, marginLeft: 2 }}>{agent.label}: {timeAgo(lastTs)}</span>
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
