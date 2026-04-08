"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

interface ParsedSignal {
  id: number;
  agent: string;
  symbol?: string;
  direction?: "BUY" | "SELL";
  confidence: number;
  reason: string;
  riskVerdict: "APPROVED" | "BLOCKED" | "PENDING" | "NONE";
  blockReason?: string;
  ts: string;
  entry_price?: number;
  sl?: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  tp4?: number;
  macroAlignment?: string;
  entrySnapshot?: {
    spread?: number;
    rsi_aligned?: boolean;
    trend_aligned?: boolean;
    volume_sufficient?: boolean;
    near_news_event?: boolean;
    market_condition?: string;
    session?: string;
  };
  bullCase?: string;
  bearCase?: string;
}

// ── Agent config ───────────────────────────────────────────────────────────────

const AGENTS = [
  { key: "strategy",      label: "Strategy",  color: "var(--agent-strategy)" },
  { key: "council",       label: "Council",   color: "var(--agent-council)" },
  { key: "risk",          label: "Risk",      color: "var(--agent-risk)" },
  { key: "neural",        label: "Neural",    color: "var(--agent-neural)" },
  { key: "crucix",        label: "Crucix",    color: "var(--agent-crucix)" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return Math.floor(ms / 1_000)    + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)   + "m ago";
  return                     Math.floor(ms / 3_600_000) + "h ago";
}

function fmtTime(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  } catch { return "—"; }
}

function agentColor(key: string): string {
  return AGENTS.find(a => a.key === key)?.color ?? "var(--text-3)";
}
function agentLabel(key: string): string {
  return AGENTS.find(a => a.key === key)?.label ?? key;
}

// ── Signal parsing ──────────────────────────────────────────────────────────────

function extractSymbol(msg: string): string | undefined {
  const m = msg.match(/\b([A-Z]{3,6}(?:\/[A-Z]{3})?)\b/);
  return m ? m[1] : undefined;
}

function extractDirection(msg: string): "BUY" | "SELL" | undefined {
  if (/buy|long|bullish|upward|breakout/i.test(msg))  return "BUY";
  if (/sell|short|bearish|downward|breakdown/i.test(msg)) return "SELL";
  return undefined;
}

function extractConfidence(msg: string): number {
  const m = msg.match(/(\d+(?:\.\d+)?)\s*%/);
  if (m) return parseFloat(m[1]);
  const c = msg.match(/confidence[:\s]+(\d+(?:\.\d+)?)/i);
  if (c) return parseFloat(c[1]) * 100;
  return 0;
}

function extractBlockReason(msg: string): string | undefined {
  const m = msg.match(/(?:guard|block|reject)[:\s]+([^.]{3,80})/i);
  return m ? m[1].trim() : undefined;
}

function extractLevels(msg: string) {
  const entry = msg.match(/entry[:\s]+([0-9.]+)/i)?.[1];
  const sl    = msg.match(/(?:sl|stop.los)[:\s]+([0-9.]+)/i)?.[1];
  const tp1   = msg.match(/tp1[:\s]+([0-9.]+)/i)?.[1];
  return {
    entry_price: entry ? parseFloat(entry) : undefined,
    sl:          sl    ? parseFloat(sl)    : undefined,
    tp1:         tp1   ? parseFloat(tp1)   : undefined,
  };
}

function extractRiskVerdict(events: AgentEvent[], symbol: string | undefined, direction: string | undefined, agent: string): "APPROVED" | "BLOCKED" | "PENDING" | "NONE" {
  // Find risk events after this signal
  const riskEvs = events.filter(e => e.agent === "risk" || e.agent === "risk_agent");
  for (const ev of riskEvs) {
    const msg = ev.message ?? ev.msg ?? "";
    if (/block|reject|guard.*fail/i.test(msg)) return "BLOCKED";
    if (/approved|accepted|proceed/i.test(msg)) return "APPROVED";
  }
  return "NONE";
}

function parseSignal(ev: AgentEvent, events: AgentEvent[]): ParsedSignal {
  const msg = ev.message ?? ev.msg ?? "";
  const agent = (ev.agent ?? "strategy").toLowerCase();
  const symbol = extractSymbol(msg);
  const direction = extractDirection(msg);
  const confidence = extractConfidence(msg);
  const blockReason = extractBlockReason(msg);
  const levels = extractLevels(msg);
  const riskVerdict = extractRiskVerdict(events, symbol, direction, agent);
  const ts = ev.created_at ?? ev.ts ?? "";

  // Extract bull/bear case from council events
  let bullCase: string | undefined;
  let bearCase: string | undefined;
  if (agent === "council") {
    const bullMatch = msg.match(/bull[:\s]+([^.]{10,200})/i);
    const bearMatch = msg.match(/bear[:\s]+([^.]{10,200})/i);
    bullCase = bullMatch?.[1]?.trim();
    bearCase = bearMatch?.[1]?.trim();
  }

  // Extract macro alignment
  let macroAlignment: string | undefined;
  if (/macro.*align|htf.*bias|aligned.*macro/i.test(msg)) macroAlignment = "Aligned";
  else if (/macro.*oppose|opposed.*macro/i.test(msg)) macroAlignment = "Opposed";
  else macroAlignment = "Neutral";

  return {
    id: ev.id ?? Math.random(),
    agent,
    symbol,
    direction,
    confidence,
    reason: msg,
    riskVerdict,
    blockReason,
    ts,
    ...levels,
    macroAlignment,
    bullCase,
    bearCase,
  };
}

// ── Style tokens ────────────────────────────────────────────────────────────────

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
  surface2:  "var(--bg-4)",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: C.radius, overflow: "hidden", ...style }}>
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 14 }}>
      {children}
    </div>
  );
}

/** Confidence bar with tier coloring */
function ConfBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color = pct >= 85 ? C.positive : pct >= 65 ? C.accent : pct >= 40 ? C.warning : C.negative;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, width: 120 }}>
      <div style={{ flex: 1, height: 4, background: "var(--bg-4)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2, transition: "width .3s" }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: C.mono, color, fontWeight: 600, minWidth: 36, textAlign: "right" }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

/** Verdict badge */
function VerdictBadge({ verdict, reason }: { verdict: ParsedSignal["riskVerdict"]; reason?: string }) {
  if (verdict === "APPROVED") return (
    <span style={{ fontSize: 10, fontWeight: 700, color: C.positive, background: "var(--gold-dim)", padding: "3px 8px", borderRadius: 4, letterSpacing: 0.4 }}>
      APPROVED
    </span>
  );
  if (verdict === "BLOCKED") return (
    <span title={reason} style={{ fontSize: 10, fontWeight: 700, color: C.negative, background: "var(--red-dim)", padding: "3px 8px", borderRadius: 4, letterSpacing: 0.4, cursor: "help" }}>
      BLOCKED
    </span>
  );
  if (verdict === "PENDING") return (
    <span style={{ fontSize: 10, fontWeight: 700, color: C.warning, background: "rgba(245,158,11,0.12)", padding: "3px 8px", borderRadius: 4, letterSpacing: 0.4 }}>
      PENDING
    </span>
  );
  return null;
}

/** Direction badge */
function DirBadge({ dir }: { dir: "BUY" | "SELL" | undefined }) {
  if (!dir) return null;
  const color = dir === "BUY" ? C.positive : C.negative;
  return (
    <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.5, color, background: "var(--bg-3)", padding: "2px 7px", borderRadius: 4 }}>
      {dir}
    </span>
  );
}

/** Agent badge */
function AgentBadge({ agent }: { agent: string }) {
  const color = agentColor(agent);
  return (
    <span style={{ fontSize: 9, fontWeight: 700, color: color, background: "var(--bg-3)", padding: "2px 6px", borderRadius: 4, letterSpacing: 0.4, textTransform: "uppercase" }}>
      {agentLabel(agent)}
    </span>
  );
}

// ── Signal Detail Drawer ───────────────────────────────────────────────────────

function SignalDrawer({ signal, onClose }: { signal: ParsedSignal; onClose: () => void }) {
  const overlayRef = useRef<HTMLDivElement>(null);

  // Close on overlay click
  const handleOverlayClick = useCallback((e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  }, [onClose]);

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      style={{
        position: "fixed", inset: 0, zIndex: 100,
        background: "rgba(0,0,0,0.5)",
        display: "flex", justifyContent: "flex-end",
        animation: "fadeIn .2s ease",
      }}
    >
      <div style={{
        width: 480, maxWidth: "95vw", height: "100vh",
        background: "var(--bg-3)",
        borderLeft: "1px solid var(--border)",
        overflowY: "auto",
        display: "flex", flexDirection: "column",
        animation: "slideIn .2s ease",
      }}>
        {/* Header */}
        <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexShrink: 0 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              {signal.symbol && <span style={{ fontSize: 22, fontWeight: 700, color: "var(--text-1)" }}>{signal.symbol}</span>}
              <DirBadge dir={signal.direction} />
              <AgentBadge agent={signal.agent} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <ConfBar value={signal.confidence} />
              <VerdictBadge verdict={signal.riskVerdict} reason={signal.blockReason} />
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "var(--bg-3)", border: "1px solid var(--border)",
            borderRadius: 8, color: "var(--text-2)", cursor: "pointer",
            width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, fontFamily: "inherit",
          }}>×</button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Timestamp */}
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.textDim }}>
            <span style={{ fontFamily: C.mono }}>{fmtTime(signal.ts)}</span>
            <span>{relTime(signal.ts)}</span>
          </div>

          {/* Block reason */}
          {signal.riskVerdict === "BLOCKED" && signal.blockReason && (
            <div style={{ background: "var(--red-dim)", border: "1px solid var(--red)", borderRadius: 10, padding: "12px 14px" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: C.negative, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>Block Reason</div>
              <div style={{ fontSize: 13, color: "var(--text-1)", lineHeight: 1.5 }}>{signal.blockReason}</div>
            </div>
          )}

          {/* Entry levels */}
          {(signal.entry_price || signal.sl || signal.tp1) && (
            <div>
              <SectionLabel>Entry Levels</SectionLabel>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
                {[
                  { label: "Entry", value: signal.entry_price, color: "var(--text-1)" },
                  { label: "SL",    value: signal.sl,           color: C.negative },
                  { label: "TP1",   value: signal.tp1,           color: C.positive },
                  { label: "TP2",   value: signal.tp2,           color: C.positive },
                  { label: "TP3",   value: signal.tp3,           color: C.positive },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ background: "var(--bg-4)", borderRadius: 8, padding: "8px 10px", textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: C.textDim, letterSpacing: 0.4, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 12, fontFamily: C.mono, fontWeight: 600, color: value ? color : C.textDim }}>
                      {value ? (Number(value)).toFixed(5) : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full reasoning */}
          <div>
            <SectionLabel>Reasoning</SectionLabel>
            <div style={{
              background: "var(--bg-4)", borderRadius: 10,
              border: "1px solid var(--border)",
              padding: "12px 14px", fontSize: 13, color: "var(--text-1)",
              lineHeight: 1.6, maxHeight: 200, overflowY: "auto",
            }}>
              {signal.reason || "—"}
            </div>
          </div>

          {/* Bull / Bear case */}
          {(signal.bullCase || signal.bearCase) && (
            <div>
              <SectionLabel>LLM Debate</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {signal.bullCase && (
                  <div style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.20)", borderRadius: 8, padding: "10px 12px" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: C.positive, letterSpacing: 0.4, textTransform: "uppercase", marginBottom: 5 }}>Bull Case</div>
                    <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.5 }}>{signal.bullCase}</div>
                  </div>
                )}
                {signal.bearCase && (
                  <div style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.20)", borderRadius: 8, padding: "10px 12px" }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: C.negative, letterSpacing: 0.4, textTransform: "uppercase", marginBottom: 5 }}>Bear Case</div>
                    <div style={{ fontSize: 12, color: "var(--text-1)", lineHeight: 1.5 }}>{signal.bearCase}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Macro alignment */}
          {signal.macroAlignment && (
            <div>
              <SectionLabel>Macro Alignment</SectionLabel>
              <div style={{ display: "flex", gap: 8 }}>
                {["Aligned", "Neutral", "Opposed"].map(m => {
                  const active = signal.macroAlignment === m;
                  const color = m === "Aligned" ? C.positive : m === "Opposed" ? C.negative : C.textMid;
                  return (
                    <div key={m} style={{
                      padding: "6px 12px", borderRadius: 8,
                      background: active ? "var(--bg-4)" : "var(--bg-3)",
                      border: `1px solid ${active ? color : "var(--border)"}`,
                      fontSize: 12, fontWeight: active ? 600 : 400,
                      color: active ? color : C.textMid,
                    }}>
                      {m}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Approval chain */}
          <div>
            <SectionLabel>Approval Chain</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {["strategy", "neural", "council", "risk"].map((ag, i) => {
                const isLast = i === 3;
                const agentConfig = AGENTS.find(a => a.key === ag);
                const color = agentConfig?.color ?? "rgba(232,234,237,0.45)";
                let verdict: "pass" | "fail" | "skip" = "skip";
                if (ag === "strategy" || ag === "neural") verdict = "pass";
                if (ag === "risk" && signal.riskVerdict === "BLOCKED") verdict = "fail";
                if (ag === "risk" && signal.riskVerdict === "APPROVED") verdict = "pass";

                return (
                  <div key={ag} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
                      <div style={{
                        width: 28, height: 28, borderRadius: "50%",
                        background: verdict === "pass" ? "var(--bg-4)" : verdict === "fail" ? "var(--red-dim)" : "var(--bg-3)",
                        border: `1.5px solid ${verdict === "pass" ? color : verdict === "fail" ? C.negative : "var(--border)"}`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 10, fontWeight: 700,
                        color: verdict === "pass" ? color : verdict === "fail" ? C.negative : C.textDim,
                        flexShrink: 0,
                      }}>
                        {verdict === "pass" ? "✓" : verdict === "fail" ? "⊘" : "—"}
                      </div>
                      {!isLast && (
                        <div style={{ width: 1, height: 12, background: verdict !== "skip" ? color : "var(--border)" }} />
                      )}
                    </div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: verdict !== "skip" ? color : C.textDim }}>{agentLabel(ag)}</div>
                      <div style={{ fontSize: 11, color: verdict === "fail" ? C.negative : C.textDim }}>
                        {verdict === "pass" ? "Approved" : verdict === "fail" ? (signal.blockReason || "Rejected") : "Not reached"}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
      `}</style>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SignalsPage() {
  const [events,  setEvents]  = useState<AgentEvent[]>([]);
  const [filter,  setFilter]  = useState<"ALL" | "BUY" | "SELL">("ALL");
  const [verdict, setVerdict] = useState<"ALL" | "APPROVED" | "BLOCKED">("ALL");
  const [search,  setSearch]  = useState("");
  const [selected, setSelected] = useState<ParsedSignal | null>(null);

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await fetch("/api/events?limit=200");
        const d = await r.json();
        if (active) setEvents(Array.isArray(d) ? d : (d.events ?? []));
      } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 10_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Parse events into signals
  const signals = useMemo(() => {
    const relevant = events.filter(e => {
      const agent = (e.agent ?? "").toLowerCase();
      return ["strategy", "council", "risk", "neural", "crucix"].includes(agent);
    });
    return relevant.map(ev => parseSignal(ev, events)).slice(0, 50);
  }, [events]);

  // Filter
  const filtered = useMemo(() => {
    return signals.filter(s => {
      if (filter !== "ALL" && s.direction !== filter) return false;
      if (verdict !== "ALL" && s.riskVerdict !== verdict) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!s.symbol?.toLowerCase().includes(q) && !s.reason.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [signals, filter, verdict, search]);

  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Filters bar */}
      <div style={{
        display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
        marginBottom: 4,
      }}>
        {/* Search */}
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search signals…"
          style={{
            background: "var(--bg-3)", border: "1px solid var(--border)",
            borderRadius: 8, padding: "8px 14px", fontSize: 13, color: "var(--text-1)",
            outline: "none", minWidth: 180, flex: "1 1 180px", fontFamily: "inherit",
          }}
        />

        {/* Direction filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {(["ALL", "BUY", "SELL"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600,
              cursor: "pointer", border: "none",
              background: filter === f ? "var(--cyan-dim)" : "var(--bg-3)",
              color: filter === f ? C.accent : C.textMid,
              outline: filter === f ? `1px solid var(--border-active)` : "none",
              fontFamily: "inherit", transition: "all .1s",
            }}>
              {f}
            </button>
          ))}
        </div>

        {/* Verdict filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {(["ALL", "APPROVED", "BLOCKED"] as const).map(f => (
            <button key={f} onClick={() => setVerdict(f as typeof verdict)} style={{
              padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600,
              cursor: "pointer", border: "none",
              background: verdict === f
                ? f === "APPROVED" ? "var(--gold-dim)" : f === "BLOCKED" ? "var(--red-dim)" : "var(--cyan-dim)"
                : "var(--bg-3)",
              color: verdict === f
                ? f === "APPROVED" ? C.positive : f === "BLOCKED" ? C.negative : C.accent
                : C.textMid,
              outline: verdict === f ? `1px solid ${f === "APPROVED" ? "var(--gold)" : f === "BLOCKED" ? "var(--red)" : "var(--cyan)"}` : "none",
              fontFamily: "inherit", transition: "all .1s",
            }}>
              {f}
            </button>
          ))}
        </div>

        <span style={{ fontSize: 12, color: C.textDim, marginLeft: "auto" }}>
          {filtered.length} signals
        </span>
      </div>

      {/* Table */}
      <Card style={{ padding: 0 }}>
        {/* Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "80px 60px 90px 1fr 130px 110px 90px",
          gap: 8,
          padding: "10px 16px",
          fontSize: 10, color: C.label, letterSpacing: 0.4, textTransform: "uppercase",
          borderBottom: `1px solid ${C.border}`,
        }}>
          <span>Symbol</span>
          <span>Dir</span>
          <span>Source</span>
          <span>Message</span>
          <span>Confidence</span>
          <span>Verdict</span>
          <span style={{ textAlign: "right" }}>Age</span>
        </div>

        {/* Rows */}
        {filtered.length === 0 ? (
          <div style={{ padding: "40px 0", textAlign: "center", fontSize: 13, color: C.textDim }}>
            No signals match the current filters
          </div>
        ) : (
          filtered.map((sig, i) => (
            <div
              key={sig.id}
              onClick={() => setSelected(sig)}
              className="signal-row"
            >
              {/* Symbol */}
              <span style={{ fontWeight: 600, color: "var(--text-1)", fontSize: 13 }}>
                {sig.symbol || "—"}
              </span>

              {/* Direction */}
              <DirBadge dir={sig.direction} />

              {/* Agent */}
              <AgentBadge agent={sig.agent} />

              {/* Message preview */}
              <span style={{ fontSize: 12, color: C.textMid, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {sig.reason.slice(0, 80)}{sig.reason.length > 80 ? "…" : ""}
              </span>

              {/* Confidence */}
              <ConfBar value={sig.confidence} />

              {/* Verdict */}
              <VerdictBadge verdict={sig.riskVerdict} reason={sig.blockReason} />

              {/* Age */}
              <span style={{ fontSize: 11, color: C.textDim, textAlign: "right", fontFamily: C.mono }}>
                {relTime(sig.ts)}
              </span>
            </div>
          ))
        )}
      </Card>

      <style>{`
        .signal-row {
          display: grid;
          grid-template-columns: 80px 60px 90px 1fr 130px 110px 90px;
          gap: 8;
          padding: 11px 16px;
          font-size: 13;
          align-items: center;
          border-bottom: 1px solid var(--border);
          cursor: pointer;
          transition: background 0.15s ease;
        }
        .signal-row:last-child { border-bottom: none; }
        .signal-row:hover { background: var(--bg-4); }
      `}</style>

      {/* Detail drawer */}
      {selected && (
        <SignalDrawer signal={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
