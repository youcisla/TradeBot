"use client";

import { useEffect, useMemo, useState } from "react";

//  Types 

interface AgentEvent {
  id?: number;
  agent: string;
  level?: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

//  Helpers 

function evMsg(e: AgentEvent): string {
  return e.message ?? e.msg ?? (typeof e.data?.message === "string" ? e.data.message : "") ?? "";
}

function evTs(e: AgentEvent): string {
  return e.created_at ?? e.ts ?? "";
}

function relTime(ts: string): string {
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function fmtTime(ts: string): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

//  Trading Session 

type Session = { label: string; color: string; hours: string };
const SESSIONS: Record<string, Session> = {
  sydney:  { label: "Sydney",  color: "#5AC8FA", hours: "21:00 – 06:00 UTC" },
  tokyo:   { label: "Tokyo",   color: "#BF5AF2", hours: "00:00 – 09:00 UTC" },
  london:  { label: "London",  color: "#0A84FF", hours: "07:00 – 16:00 UTC" },
  newyork: { label: "New York", color: "#34C759", hours: "12:00 – 21:00 UTC" },
};

function getCurrentSessions(): string[] {
  const h = new Date().getUTCHours();
  const active: string[] = [];
  if (h >= 21 || h < 6)  active.push("sydney");
  if (h >= 0  && h < 9)  active.push("tokyo");
  if (h >= 7  && h < 16) active.push("london");
  if (h >= 12 && h < 21) active.push("newyork");
  return active;
}

//  Symbol extraction from events 

const SYMBOL_RE = /\b([A-Z]{3,6}(?:\/[A-Z]{3})?)(?:\s|:|,|$)/g;

function extractSymbols(events: AgentEvent[]): Map<string, { bullish: number; bearish: number; neutral: number; last: string }> {
  const map = new Map<string, { bullish: number; bearish: number; neutral: number; last: string }>();
  for (const ev of events) {
    const msg = evMsg(ev).toUpperCase();
    let match;
    const seen = new Set<string>();
    SYMBOL_RE.lastIndex = 0;
    while ((match = SYMBOL_RE.exec(msg)) !== null) {
      const sym = match[1].replace("/", "");
      if (sym.length < 3 || sym.length > 8 || seen.has(sym)) continue;
      seen.add(sym);
      const entry = map.get(sym) ?? { bullish: 0, bearish: 0, neutral: 0, last: evTs(ev) };
      if (/bullish|buy|long|upward|breakout|momentum up/i.test(msg)) entry.bullish++;
      else if (/bearish|sell|short|downward|reversal|breakdown/i.test(msg)) entry.bearish++;
      else entry.neutral++;
      if (evTs(ev) > entry.last) entry.last = evTs(ev);
      map.set(sym, entry);
    }
  }
  return map;
}

//  Page 

export default function MarketIntelPage() {
  const [events,   setEvents]   = useState<AgentEvent[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [nowUtc,   setNowUtc]   = useState(new Date());
  const [active,   setActive]   = useState<string[]>([]);
  const [filter,   setFilter]   = useState("ALL");

  // Poll events
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/events?agent=market&limit=100");
        const d = await r.json();
        setEvents(Array.isArray(d) ? d : []);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 15_000);
    return () => clearInterval(t);
  }, []);

  // Clock + session tick
  useEffect(() => {
    const t = setInterval(() => {
      setNowUtc(new Date());
      setActive(getCurrentSessions());
    }, 1_000);
    setActive(getCurrentSessions());
    return () => clearInterval(t);
  }, []);

  const symbolMap  = useMemo(() => extractSymbols(events), [events]);

  const topSymbols = useMemo(() => {
    const arr = Array.from(symbolMap.entries()).map(([sym, v]) => ({
      sym,
      total: v.bullish + v.bearish + v.neutral,
      bias: v.bullish > v.bearish ? "bullish" : v.bearish > v.bullish ? "bearish" : "neutral",
      ...v,
    }));
    return arr.sort((a, b) => b.total - a.total).slice(0, 24);
  }, [symbolMap]);

  const filteredEvents = useMemo(() => {
    if (filter === "ALL") return events;
    return events.filter(e => {
      const msg = evMsg(e).toLowerCase();
      if (filter === "BULLISH") return /bullish|buy|long|upward|breakout/.test(msg);
      if (filter === "BEARISH") return /bearish|sell|short|downward|breakdown/.test(msg);
      return true;
    });
  }, [events, filter]);

  //  Styles
  const MONO = "var(--font-mono-stack)";
  const card: React.CSSProperties = {
    background: "var(--card-bg)", border: "1px solid var(--card-border)", borderRadius: "var(--card-radius)",
  };
  const sectionLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: "var(--section-label)",
    letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 12,
  };

  return (
    <>
      {/*  Session bar  */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {Object.entries(SESSIONS).map(([key, s]) => {
          const isActive = active.includes(key);
          return (
            <div key={key} style={{
              ...card,
              padding: "16px 18px",
              outline: isActive ? `1px solid ${s.color}44` : "none",
              background: isActive ? `${s.color}0a` : "rgba(255,255,255,0.04)",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: isActive ? s.color : "rgba(232,234,237,0.15)",
                  boxShadow: isActive ? `0 0 6px ${s.color}` : "none",
                  flexShrink: 0,
                }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: isActive ? s.color : "rgba(232,234,237,0.40)" }}>
                  {s.label}
                </span>
                {isActive && (
                  <span style={{
                    marginLeft: "auto", fontSize: 10, fontWeight: 700, letterSpacing: 0.3,
                    color: s.color, background: `${s.color}20`, borderRadius: 4, padding: "2px 6px",
                  }}>
                    LIVE
                  </span>
                )}
              </div>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", fontFamily: MONO }}>{s.hours}</div>
            </div>
          );
        })}
      </div>

      {/*  UTC clock strip  */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20, padding: "10px 16px", ...card }}>
        <span style={{ fontFamily: "Material Symbols Outlined", fontSize: 18, color: "rgba(232,234,237,0.40)", fontWeight: 400 }}>schedule</span>
        <span style={{ fontFamily: MONO, fontSize: 15, color: "#E8EAED", letterSpacing: 0.5 }}>
          {nowUtc.toUTCString().replace("GMT", "UTC").slice(0, -4)}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "rgba(232,234,237,0.30)" }}>
          {events.length} events loaded
        </span>
      </div>

      {/*  Main grid  */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>

        {/* Symbol grid */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...card, padding: "20px" }}>
            <div style={sectionLabel}>Symbol Momentum · Last 100 market events</div>
            {topSymbols.length === 0 ? (
              <div style={{ fontSize: 13, color: "rgba(232,234,237,0.25)", padding: "24px 0", textAlign: "center" }}>
                {loading ? "Analysing…" : "No symbol data in recent events"}
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: 8 }}>
                {topSymbols.map(({ sym, bullish, bearish, neutral, total, bias }) => {
                  const biasColor = bias === "bullish" ? "#34C759" : bias === "bearish" ? "#FF3B30" : "rgba(232,234,237,0.45)";
                  const bullPct   = total > 0 ? (bullish / total) * 100 : 0;
                  const bearPct   = total > 0 ? (bearish / total) * 100 : 0;
                  return (
                    <div key={sym} style={{
                      background: "rgba(255,255,255,0.05)", borderRadius: 8, padding: "10px 12px",
                      border: `1px solid ${biasColor}22`,
                    }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: biasColor, marginBottom: 6 }}>{sym}</div>
                      {/* Bar */}
                      <div style={{ height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)", overflow: "hidden", marginBottom: 6 }}>
                        <div style={{ height: "100%", display: "flex" }}>
                          <div style={{ width: `${bullPct}%`, background: "#34C759" }} />
                          <div style={{ width: `${bearPct}%`, background: "#FF3B30" }} />
                        </div>
                      </div>
                      <div style={{ fontSize: 10, color: "rgba(232,234,237,0.30)", fontFamily: MONO }}>
                        {total} mention{total !== 1 ? "s" : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Event feed */}
        <div style={{ width: 340, flexShrink: 0 }}>
          <div style={{ ...card, overflow: "hidden" }}>
            <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ ...sectionLabel, marginBottom: 0 }}>Market Feed</span>
              <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
                {(["ALL", "BULLISH", "BEARISH"] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    style={{
                      height: 24, padding: "0 10px", borderRadius: 5, cursor: "pointer", fontFamily: "inherit",
                      fontSize: 10, fontWeight: 600, letterSpacing: 0.4,
                      background: filter === f ? "rgba(255,255,255,0.12)" : "transparent",
                      border: filter === f ? "1px solid rgba(255,255,255,0.20)" : "1px solid transparent",
                      color: filter === f ? "#E8EAED" : "rgba(232,234,237,0.35)",
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ maxHeight: 520, overflowY: "auto" }}>
              {loading ? (
                <div style={{ padding: 24, textAlign: "center", color: "rgba(232,234,237,0.25)", fontSize: 13 }}>Loading…</div>
              ) : filteredEvents.length === 0 ? (
                <div style={{ padding: 24, textAlign: "center", color: "rgba(232,234,237,0.25)", fontSize: 13 }}>No events found</div>
              ) : filteredEvents.slice(0, 40).map((ev, i) => {
                const msg       = evMsg(ev);
                const ts        = evTs(ev);
                const isBull    = /bullish|buy|long|upward|breakout/i.test(msg);
                const isBear    = /bearish|sell|short|downward|breakdown/i.test(msg);
                const dotColor  = isBull ? "#34C759" : isBear ? "#FF3B30" : "rgba(232,234,237,0.25)";
                return (
                  <div key={ev.id ?? i} style={{
                    padding: "10px 16px",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    display: "flex", gap: 10, alignItems: "flex-start",
                  }}>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: dotColor, flexShrink: 0, marginTop: 5 }} />
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{
                        fontSize: 12, color: "rgba(232,234,237,0.75)", lineHeight: 1.5,
                        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                      }}>
                        {msg || "—"}
                      </div>
                      <div style={{ fontSize: 10, color: "rgba(232,234,237,0.25)", marginTop: 3, fontFamily: MONO }}>
                        {fmtTime(ts)} · {ts ? relTime(ts) : ""}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}