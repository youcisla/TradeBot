"use client";

import { useEffect, useRef, useState } from "react";

//  Types 

interface AgentEvent {
  id: number;
  agent: string;
  event_type: string;
  message: string;
  created_at: string;
}

//  Agent config 

const AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "#5AC8FA" },
  { key: "market",        label: "Market",    color: "#0A84FF" },
  { key: "analysis",      label: "Analysis",  color: "#E8EAED" },
  { key: "strategy",      label: "Strategy",  color: "#34C759" },
  { key: "neural",        label: "Neural",    color: "#BF5AF2" },
  { key: "council",       label: "Council",   color: "#FF9F0A" },
  { key: "risk",          label: "Risk",      color: "#FF3B30" },
  { key: "execution",     label: "Execution", color: "#E8EAED" },
  { key: "trade_manager", label: "TradeMgr",  color: "#5AC8FA" },
  { key: "learning",      label: "Learning",  color: "#30D158" },
  { key: "model_manager", label: "Models",    color: "#BF5AF2" },
  { key: "logging",       label: "Logging",   color: "rgba(232,234,237,0.35)" },
];

//  Helpers 

function relTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const s  = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m  = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h  = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function agentColor(key: string): string {
  return AGENTS.find(a => a.key === key)?.color ?? "rgba(232,234,237,0.45)";
}

function agentLabel(key: string): string {
  return AGENTS.find(a => a.key === key)?.label ?? key;
}

function healthBadge(lastSeen: string | null): { label: string; color: string } {
  if (!lastSeen) return { label: "DORMANT", color: "rgba(232,234,237,0.20)" };
  const ms   = Date.now() - new Date(lastSeen).getTime();
  const mins = ms / 60_000;
  if (mins < 2)  return { label: "ACTIVE",   color: "#34C759" };
  if (mins < 10) return { label: "IDLE",     color: "#FF9F0A" };
  if (mins < 60) return { label: "SLOW",     color: "#FF9F0A" };
  return { label: "STALE", color: "#FF3B30" };
}

//  Page 

export default function BrainPage() {
  const [events,     setEvents]     = useState<AgentEvent[]>([]);
  const [filter,     setFilter]     = useState<string>("ALL");
  const [search,     setSearch]     = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [loading,    setLoading]    = useState(true);
  const feedRef = useRef<HTMLDivElement>(null);

  //  Data fetch 

  useEffect(() => {
    const load = async () => {
      try {
        const res  = await fetch("/api/events?limit=300");
        const data = await res.json();
        const evts = Array.isArray(data) ? data : (data.events ?? []);
        setEvents(evts);
      } catch { /* silent */ }
      finally  { setLoading(false); }
    };
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, []);

  // Auto-scroll feed to bottom on new events
  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  //  Agent health grid 

  const agentHealth = AGENTS.map(a => {
    const evts = events.filter(e => e.agent === a.key);
    const last  = evts.length > 0 ? evts[0]?.created_at ?? null : null;
    const badge = healthBadge(last);
    const msg   = evts[0]?.message ?? "—";
    return { ...a, last, badge, msg, count: evts.length };
  });

  //  Filtered feed 

  const filteredEvents = events.filter(e => {
    const matchAgent  = filter === "ALL" || e.agent === filter;
    const matchSearch = !search || e.message?.toLowerCase().includes(search.toLowerCase());
    return matchAgent && matchSearch;
  }).slice(0, 200);

  //  Styles 

  const MONO = '"SF Mono", SFMono-Regular, ui-monospace, monospace';
  const card: React.CSSProperties = {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 12,
  };

  return (
    <>
      {/*  Agent health grid  */}
      <div style={{ ...card, padding: "20px", marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.40)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 16 }}>
          Agent Health · {AGENTS.length} agents
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 10 }}>
          {agentHealth.map(a => (
            <div
              key={a.key}
              onClick={() => setFilter(f => f === a.key ? "ALL" : a.key)}
              style={{
                padding: "12px 14px", borderRadius: 10, cursor: "pointer", transition: "all 0.15s",
                background: filter === a.key ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.04)",
                border: `1px solid ${filter === a.key ? a.color + "55" : "rgba(255,255,255,0.07)"}`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: a.color, textTransform: "uppercase", letterSpacing: 0.3 }}>{a.label}</span>
                <span style={{
                  fontSize: 9, fontWeight: 700, color: a.badge.color, letterSpacing: 0.5,
                  background: a.badge.color + "20", padding: "1px 5px", borderRadius: 4,
                }}>
                  {a.badge.label}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.40)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginBottom: 4 }}>
                {a.msg.slice(0, 40)}{a.msg.length > 40 ? "…" : ""}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 10, color: "rgba(232,234,237,0.25)", fontFamily: MONO }}>{a.count} events</span>
                <span style={{ fontSize: 10, color: "rgba(232,234,237,0.25)" }}>{a.last ? relTime(a.last) : "—"}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/*  Event stream  */}
      <div style={{ ...card, display: "flex", flexDirection: "column", minHeight: 480 }}>
        {/* Header + controls */}
        <div style={{ padding: "18px 20px 14px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.40)", letterSpacing: 0.5, textTransform: "uppercase", flex: 1 }}>
            Event Stream · {filteredEvents.length} shown
          </div>
          {/* Search */}
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search events…"
            style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: 8, padding: "6px 12px", fontSize: 12, color: "#E8EAED",
              outline: "none", width: 180,
            }}
          />
          {/* Agent filter pills */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["ALL", ...AGENTS.map(a => a.key)].slice(0, 8).map(k => {
              const a = AGENTS.find(x => x.key === k);
              return (
                <button
                  key={k}
                  onClick={() => setFilter(k)}
                  style={{
                    padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer", border: "none",
                    background: filter === k ? (a?.color ?? "#E8EAED") + "22" : "rgba(255,255,255,0.05)",
                    color: filter === k ? (a?.color ?? "#E8EAED") : "rgba(232,234,237,0.45)",
                    outline: filter === k ? `1px solid ${a?.color ?? "#E8EAED"}55` : "none",
                    transition: "all 0.1s",
                  }}
                >
                  {k === "ALL" ? "All" : (a?.label ?? k)}
                </button>
              );
            })}
          </div>
          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(s => !s)}
            style={{
              padding: "4px 10px", borderRadius: 6, fontSize: 11, cursor: "pointer", border: "none",
              background: autoScroll ? "rgba(10,132,255,0.15)" : "rgba(255,255,255,0.05)",
              color: autoScroll ? "#0A84FF" : "rgba(232,234,237,0.40)",
              outline: autoScroll ? "1px solid rgba(10,132,255,0.35)" : "none",
              transition: "all 0.1s",
            }}
          >
            {autoScroll ? " Live" : "Paused"}
          </button>
        </div>

        {/* Feed */}
        <div
          ref={feedRef}
          onScroll={() => {
            if (!feedRef.current) return;
            const { scrollTop, scrollHeight, clientHeight } = feedRef.current;
            setAutoScroll(scrollHeight - scrollTop - clientHeight < 40);
          }}
          style={{ flex: 1, overflowY: "auto", padding: "12px 20px", display: "flex", flexDirection: "column", gap: 2 }}
        >
          {loading && (
            <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)", padding: "40px 0", textAlign: "center" }}>Loading events…</div>
          )}
          {!loading && filteredEvents.length === 0 && (
            <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)", padding: "40px 0", textAlign: "center" }}>No events match the current filter</div>
          )}
          {filteredEvents.map(evt => (
            <div
              key={evt.id}
              style={{
                display: "flex", alignItems: "flex-start", gap: 10, padding: "7px 10px",
                borderRadius: 6, transition: "background 0.1s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              {/* Agent badge */}
              <span style={{
                fontSize: 9, fontWeight: 700, color: agentColor(evt.agent), letterSpacing: 0.4,
                background: agentColor(evt.agent) + "18", padding: "2px 6px", borderRadius: 4,
                flexShrink: 0, marginTop: 1, textTransform: "uppercase",
              }}>
                {agentLabel(evt.agent)}
              </span>
              {/* Message */}
              <span style={{ fontSize: 12, color: "rgba(232,234,237,0.75)", flex: 1, lineHeight: 1.5, wordBreak: "break-word" }}>
                {evt.message}
              </span>
              {/* Type tag */}
              {evt.event_type && (
                <span style={{ fontSize: 9, color: "rgba(232,234,237,0.20)", flexShrink: 0, marginTop: 2, fontFamily: MONO, textTransform: "uppercase" }}>
                  {evt.event_type}
                </span>
              )}
              {/* Time */}
              <span style={{ fontSize: 10, color: "rgba(232,234,237,0.20)", flexShrink: 0, marginTop: 2, fontFamily: MONO }}>
                {evt.created_at ? relTime(evt.created_at) : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}