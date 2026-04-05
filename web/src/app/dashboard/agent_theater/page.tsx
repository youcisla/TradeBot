"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import PaginationControls from "@/components/PaginationControls";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id: string;
  agent: string;
  level: string;
  message: string;
  data?: Record<string, unknown>;
  created_at: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FONT = `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO = `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

const AGENT_COLORS: Record<string, string> = {
  crucix:        "#64D2FF",
  market:        "#32ADE6",
  analysis:      "#FFFFFF",
  strategy:      "#30D158",
  neural:        "#BF5AF2",
  council:       "#FF9F0A",
  risk:          "#FF453A",
  execution:     "#FFFFFF",
  trade_manager: "#63E6E2",
  learning:      "#64D2FF",
  logging:       "#636366",
  model_manager: "#5E5CE6",
};

const ALL_AGENTS = [
  "crucix","market","analysis","strategy","neural",
  "council","risk","execution","trade_manager","learning","logging","model_manager",
];

function agentColor(agent: string): string {
  return AGENT_COLORS[agent?.toLowerCase()] ?? "#8E8E93";
}

function levelColor(level: string): string {
  const l = (level ?? "").toUpperCase();
  if (l === "ERROR") return "#FF453A";
  if (l === "WARN")  return "#FF9F0A";
  return "rgba(235,235,245,0.4)";
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8);
  } catch {
    return "00:00:00";
  }
}

// ── Event Row ─────────────────────────────────────────────────────────────────

function EventRow({
  ev,
  isExpanded,
  onToggle,
}: {
  ev: AgentEvent;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const aColor   = agentColor(ev.agent);
  const lColor   = levelColor(ev.level);
  const hasData  = ev.data && Object.keys(ev.data).length > 0;
  const lvlUpper = (ev.level ?? "INFO").toUpperCase();

  return (
    <div
      style={{
        display:       "flex",
        flexDirection: "column",
        borderBottom:  "0.5px solid rgba(84,84,88,0.3)",
        cursor:        hasData ? "pointer" : "default",
        minHeight:     52,
      }}
      onClick={hasData ? onToggle : undefined}
    >
      <div
        style={{
          display:    "flex",
          alignItems: "center",
          gap:        10,
          padding:    "10px 14px",
          borderLeft: `3px solid ${aColor}`,
        }}
      >
        {/* Agent badge */}
        <span
          style={{
            background:    `${aColor}22`,
            border:        `1px solid ${aColor}55`,
            color:         aColor,
            fontSize:      10,
            fontWeight:    700,
            letterSpacing: "0.07em",
            padding:       "2px 7px",
            borderRadius:  6,
            flexShrink:    0,
            textTransform: "uppercase",
            fontFamily:    FONT,
            minWidth:      72,
            textAlign:     "center",
          }}
        >
          {ev.agent}
        </span>

        {/* Level badge */}
        <span
          style={{
            color:         lColor,
            fontSize:      10,
            fontWeight:    600,
            letterSpacing: "0.06em",
            padding:       "2px 7px",
            background:    `${lColor}18`,
            border:        `1px solid ${lColor}40`,
            borderRadius:  6,
            flexShrink:    0,
            textTransform: "uppercase",
            fontFamily:    FONT,
            minWidth:      46,
            textAlign:     "center",
          }}
        >
          {lvlUpper}
        </span>

        {/* Message */}
        <span
          style={{
            color:      lvlUpper === "ERROR" ? "#FF6B6B" : "rgba(235,235,245,0.85)",
            fontSize:   13,
            fontFamily: MONO,
            flex:       1,
            lineHeight: 1.4,
            wordBreak:  "break-word",
          }}
        >
          {ev.message}
        </span>

        {/* Timestamp */}
        <span
          style={{
            color:      "rgba(235,235,245,0.3)",
            fontFamily: MONO,
            fontSize:   11,
            flexShrink: 0,
          }}
        >
          {fmtTime(ev.created_at)}
        </span>

        {/* Expand chevron */}
        {hasData && (
          <span
            className="material-symbols-outlined"
            style={{
              fontSize:   16,
              color:      "rgba(235,235,245,0.3)",
              flexShrink: 0,
              transform:  isExpanded ? "rotate(90deg)" : "rotate(0deg)",
              transition: "transform 0.15s",
            }}
          >
            chevron_right
          </span>
        )}
      </div>

      {/* Expanded JSON */}
      {isExpanded && hasData && (
        <div
          style={{
            margin:       "0 14px 10px 17px",
            background:   "#2C2C2E",
            borderRadius: 8,
            padding:      "10px 12px",
            maxHeight:    200,
            overflowY:    "auto",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <pre
            style={{
              margin:     0,
              fontFamily: MONO,
              fontSize:   11,
              color:      "#64D2FF",
              whiteSpace: "pre-wrap",
              wordBreak:  "break-word",
            }}
          >
            {JSON.stringify(ev.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Stat Chip ─────────────────────────────────────────────────────────────────

function StatChip({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div
      style={{
        background:   "#1C1C1E",
        borderRadius: 10,
        padding:      "8px 14px",
        display:      "flex",
        flexDirection:"column",
        gap:          2,
      }}
    >
      <span style={{ fontSize: 11, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>{label}</span>
      <span style={{ fontSize: 17, fontWeight: 700, color: color ?? "#FFFFFF", fontFamily: FONT }}>{value}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AgentTheaterPage() {
  const [events,      setEvents]      = useState<AgentEvent[]>([]);
  const [expanded,    setExpanded]    = useState<Set<string>>(new Set());
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [textFilter,  setTextFilter]  = useState("");
  const [page,        setPage]        = useState(1);
  const [pageSize,    setPageSize]    = useState(20);
  const logRef = useRef<HTMLDivElement>(null);

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/events?limit=100")
        .then((r) => r.json())
        .then((d) => { if (active && Array.isArray(d)) setEvents(d); })
        .catch(() => {});
    load();
    const id = setInterval(load, 5_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const filteredEvents = useMemo(
    () => {
      const byAgent = agentFilter === "all"
        ? events
        : events.filter((e) => e.agent === agentFilter);

      const query = textFilter.trim().toLowerCase();
      if (!query) return byAgent;

      return byAgent.filter((event) => {
        const haystack = [
          event.agent,
          event.level,
          event.message,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      });
    },
    [events, agentFilter, textFilter]
  );

  const pagedEvents = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredEvents.slice(start, start + pageSize);
  }, [filteredEvents, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [agentFilter, textFilter, pageSize]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredEvents.length / pageSize));
    setPage((prev) => Math.min(prev, totalPages));
  }, [filteredEvents.length, pageSize]);

  const uniqueAgents = useMemo(
    () => Array.from(new Set(events.map((e) => e.agent))).filter(Boolean).sort(),
    [events]
  );

  // Stats
  const today = new Date().toDateString();
  const todayEvents = useMemo(
    () => events.filter((e) => new Date(e.created_at).toDateString() === today),
    [events, today]
  );
  const todayErrors = useMemo(
    () => todayEvents.filter((e) => (e.level ?? "").toUpperCase() === "ERROR").length,
    [todayEvents]
  );
  const mostActiveAgent = useMemo(() => {
    const counts: Record<string, number> = {};
    events.forEach((e) => { counts[e.agent] = (counts[e.agent] ?? 0) + 1; });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    return sorted[0]?.[0] ?? "—";
  }, [events]);

  // Pill agents to show: always show ALL_AGENTS if present in events, otherwise just seen agents
  const pillAgents = useMemo(() => {
    const seen = new Set(events.map((e) => e.agent));
    return ALL_AGENTS.filter((a) => seen.has(a));
  }, [events]);

  return (
    <div
      style={{
        paddingTop:    20,
        paddingBottom: 40,
        paddingLeft:   0,
        paddingRight:  0,
        fontFamily:    FONT,
        minHeight:     "100vh",
        background:    "#000000",
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize:     28,
          fontWeight:   700,
          color:        "#FFFFFF",
          margin:       "0 0 20px",
          letterSpacing:"-0.5px",
          fontFamily:   FONT,
        }}
      >
        Activity Feed
      </h1>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <StatChip label="Events Today"     value={todayEvents.length}  color="#FFFFFF" />
        <StatChip label="Errors Today"     value={todayErrors}         color={todayErrors > 0 ? "#FF453A" : "#30D158"} />
        <StatChip label="Most Active"      value={mostActiveAgent}     color={agentColor(mostActiveAgent)} />
        <StatChip label="Total in Feed"    value={events.length}       color="rgba(235,235,245,0.6)" />
      </div>

      {/* Agent selector pills */}
      <div
        style={{
          display:       "flex",
          gap:           8,
          overflowX:     "auto",
          paddingBottom: 4,
          marginBottom:  14,
          scrollbarWidth:"none",
        }}
      >
        {/* All pill */}
        <button
          onClick={() => setAgentFilter("all")}
          style={{
            height:        32,
            padding:       "0 14px",
            borderRadius:  20,
            border:        agentFilter === "all" ? "1.5px solid rgba(235,235,245,0.6)" : "1.5px solid rgba(84,84,88,0.65)",
            background:    agentFilter === "all" ? "rgba(235,235,245,0.12)" : "rgba(118,118,128,0.18)",
            color:         agentFilter === "all" ? "#FFFFFF" : "rgba(235,235,245,0.5)",
            fontSize:      12,
            fontWeight:    600,
            cursor:        "pointer",
            flexShrink:    0,
            fontFamily:    FONT,
            letterSpacing: "0.03em",
            transition:    "all 0.15s",
          }}
        >
          All
        </button>

        {(pillAgents.length > 0 ? pillAgents : uniqueAgents).map((a) => {
          const active = agentFilter === a;
          const c = agentColor(a);
          return (
            <button
              key={a}
              onClick={() => setAgentFilter(active ? "all" : a)}
              style={{
                height:        32,
                padding:       "0 14px",
                borderRadius:  20,
                border:        active ? `1.5px solid ${c}` : "1.5px solid rgba(84,84,88,0.65)",
                background:    active ? `${c}25` : "rgba(118,118,128,0.18)",
                color:         active ? c : "rgba(235,235,245,0.5)",
                fontSize:      12,
                fontWeight:    600,
                cursor:        "pointer",
                flexShrink:    0,
                fontFamily:    FONT,
                letterSpacing: "0.03em",
                transition:    "all 0.15s",
              }}
            >
              {a}
            </button>
          );
        })}
      </div>

      <div style={{ marginBottom: 14 }}>
        <input
          value={textFilter}
          onChange={(e) => setTextFilter(e.target.value)}
          placeholder="Filter events..."
          style={{
            width: "100%",
            height: 34,
            borderRadius: 10,
            border: "1px solid rgba(84,84,88,0.65)",
            background: "rgba(118,118,128,0.2)",
            color: "#FFFFFF",
            padding: "0 12px",
            fontSize: 13,
            fontWeight: 500,
            fontFamily: FONT,
            outline: "none",
          }}
        />
      </div>

      {/* Event feed card */}
      <div
        style={{
          background:   "#1C1C1E",
          borderRadius: 12,
          overflow:     "hidden",
        }}
      >
        {/* Card header */}
        <div
          style={{
            display:        "flex",
            alignItems:     "center",
            justifyContent: "space-between",
            padding:        "12px 16px",
            borderBottom:   "0.5px solid rgba(84,84,88,0.65)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 18, color: "#30D158" }}
            >
              stream
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#FFFFFF" }}>
              Event Feed
            </span>
            <span
              style={{
                background: "rgba(48,209,88,0.18)",
                border:     "1px solid rgba(48,209,88,0.4)",
                color:      "#30D158",
                fontSize:   10,
                fontWeight: 700,
                padding:    "1px 7px",
                borderRadius: 6,
                letterSpacing: "0.08em",
              }}
            >
              LIVE
            </span>
          </div>
          <span style={{ fontSize: 12, color: "rgba(235,235,245,0.3)", fontFamily: MONO }}>
            {filteredEvents.length} events
          </span>
        </div>

        {/* Rows */}
        <div
          ref={logRef}
          style={{
            maxHeight: 600,
            overflowY: "auto",
          }}
        >
          {filteredEvents.length === 0 ? (
            <div
              style={{
                padding:    "48px 20px",
                textAlign:  "center",
                color:      "rgba(235,235,245,0.3)",
                fontSize:   14,
                fontFamily: FONT,
              }}
            >
              {events.length === 0
                ? "Awaiting events…"
                : `No events from agent: ${agentFilter}`}
            </div>
          ) : (
            pagedEvents.map((ev) => (
              <EventRow
                key={ev.id}
                ev={ev}
                isExpanded={expanded.has(ev.id)}
                onToggle={() => toggleExpanded(ev.id)}
              />
            ))
          )}
        </div>

        {filteredEvents.length > 0 && (
          <div style={{ padding: "10px 12px 12px" }}>
            <PaginationControls
              page={page}
              totalItems={filteredEvents.length}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              label="events"
            />
          </div>
        )}
      </div>
    </div>
  );
}
