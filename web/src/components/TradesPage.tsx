"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Trade {
  id: number;
  symbol: string;
  strategy?: string;
  direction: string;
  entry_price: number;
  lot_size?: number;
  stop_loss?: number;
  take_profit_1?: number;
  take_profit_2?: number;
  take_profit_3?: number;
  take_profit_4?: number;
  tp1_lots?: number;
  tp2_lots?: number;
  tp3_lots?: number;
  tp4_lots?: number;
  tp1_hit?: boolean;
  tp2_hit?: boolean;
  tp3_hit?: boolean;
  tp4_hit?: boolean;
  status: string;
  open_time?: string;
  close_time?: string;
  pnl?: number;
  close_reason?: string;
  commission?: number;
  current_price?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number | undefined): string {
  const n = Number(v ?? 0);
  const f = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (n < 0 ? "-$" : "$") + f;
}

function fmtPrice(v: number | undefined): string {
  const n = Number(v ?? 0);
  if (!n && n !== 0) return "—";
  return n >= 100 ? n.toFixed(2) : n >= 1 ? n.toFixed(4) : n.toFixed(5);
}

function fmtDate(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + " " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function relAge(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000)  return Math.floor(ms / 60_000)    + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return                      Math.floor(ms / 86_400_000) + "d";
}

function dirLabel(d: string): "LONG" | "SHORT" {
  return /buy|long/i.test(d) ? "LONG" : "SHORT";
}

// ── Tokens ─────────────────────────────────────────────────────────────────────

const C = {
  bg:       "var(--card-bg)",
  border:   "var(--card-border)",
  radius:   "var(--card-radius)",
  mono:     "var(--font-mono-stack)",
  label:    "var(--section-label)",
  positive:  "#30D158",
  negative:  "#FF453A",
  warning:   "#FF9F0A",
  cyan:     "#63D4FF",
  textDim:   "rgba(232,234,237,0.30)",
  textMid:   "rgba(232,234,237,0.55)",
};

const MONO = C.mono;

// ── TP Progression Component ────────────────────────────────────────────────────

function TpProgression({ trade }: { trade: Trade }) {
  const hits = [
    trade.tp1_hit,
    trade.tp2_hit,
    trade.tp3_hit,
    trade.tp4_hit,
  ];

  const lots = [
    trade.tp1_lots,
    trade.tp2_lots,
    trade.tp3_lots,
    trade.tp4_lots,
  ];

  const total = lots.reduce((s: number, v) => s + (v ?? 0), 0) || 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 100 }}>
      {/* TP dots */}
      <div style={{ display: "flex", alignItems: "center", gap: 0, position: "relative" }}>
        {hits.map((hit, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              width: 12, height: 12, borderRadius: "50%",
              background: hit ? C.positive : "rgba(255,255,255,0.10)",
              border: `1.5px solid ${hit ? C.positive : "rgba(255,255,255,0.20)"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 7, fontWeight: 700, color: hit ? "#fff" : "rgba(255,255,255,0.30)",
              flexShrink: 0,
            }}>
              {i + 1}
            </div>
            {i < 3 && (
              <div style={{
                width: 20, height: 2,
                background: hits.slice(0, i + 1).every(Boolean)
                  ? C.positive + "60"
                  : "rgba(255,255,255,0.10)",
                transition: "background .3s",
              }} />
            )}
          </div>
        ))}
      </div>
      {/* Lot bar */}
      <div style={{ display: "flex", height: 3, borderRadius: 2, overflow: "hidden", background: "rgba(255,255,255,0.06)" }}>
        {hits.map((hit, i) => {
          const pct = ((lots[i] ?? 0) / total) * 100;
          return pct > 0 ? (
            <div key={i} style={{
              width: `${pct}%`, height: "100%",
              background: hit ? C.positive : "rgba(255,255,255,0.20)",
              transition: "background .3s",
            }} />
          ) : null;
        })}
      </div>
    </div>
  );
}

// ── Trade Detail Drawer ───────────────────────────────────────────────────────

function TradeDrawer({ trade, onClose }: { trade: Trade; onClose: () => void }) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const isLong = dirLabel(trade.direction) === "LONG";

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

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
        width: 520, maxWidth: "95vw", height: "100vh",
        background: "#0D0F14",
        borderLeft: "1px solid rgba(255,255,255,0.10)",
        overflowY: "auto",
        display: "flex", flexDirection: "column",
        animation: "slideIn .2s ease",
      }}>
        {/* Header */}
        <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid rgba(255,255,255,0.08)", flexShrink: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24, fontWeight: 700, color: "#E8EAED" }}>{trade.symbol}</span>
              <span style={{
                fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
                color: isLong ? C.positive : C.negative,
                background: (isLong ? C.positive : C.negative) + "18",
                padding: "3px 8px", borderRadius: 4,
              }}>
                {isLong ? "LONG" : "SHORT"}
              </span>
              <span style={{
                fontSize: 10, fontWeight: 600,
                color: trade.status === "OPEN" ? C.cyan : C.textMid,
                background: (trade.status === "OPEN" ? C.cyan : "rgba(255,255,255,0.06)") + "18",
                padding: "3px 8px", borderRadius: 4,
              }}>
                {trade.status}
              </span>
            </div>
            <button onClick={onClose} style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: 8, color: "rgba(232,234,237,0.60)", cursor: "pointer",
              width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, fontFamily: "inherit",
            }}>×</button>
          </div>

          {/* PnL */}
          <div style={{ marginTop: 12, display: "flex", gap: 20 }}>
            {[
              { label: "Unrealized P&L", value: trade.pnl != null ? fmtUsd(trade.pnl) : "—", color: (trade.pnl ?? 0) >= 0 ? C.positive : C.negative },
              { label: "Entry", value: fmtPrice(trade.entry_price), color: "#E8EAED" },
              { label: "Current", value: trade.current_price ? fmtPrice(trade.current_price) : "—", color: "#E8EAED" },
              { label: "Strategy", value: trade.strategy || "—", color: C.textMid },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div style={{ fontSize: 10, color: C.label, textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 15, fontWeight: 700, fontFamily: MONO, color }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Entry Levels */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 10 }}>
              Entry Levels
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
              {[
                { label: "Entry",   value: trade.entry_price,    color: "#E8EAED" },
                { label: "SL",       value: trade.stop_loss,     color: C.negative },
                { label: "TP1",      value: trade.take_profit_1,  color: C.positive },
                { label: "TP2",      value: trade.take_profit_2,  color: C.positive },
                { label: "TP3",      value: trade.take_profit_3,  color: C.positive },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "8px 10px", textAlign: "center" }}>
                  <div style={{ fontSize: 10, color: C.textDim, letterSpacing: 0.4, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 12, fontFamily: MONO, fontWeight: 600, color: value ? color : C.textDim }}>
                    {value ? fmtPrice(value) : "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* TP Progression */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 10 }}>
              TP Progression
            </div>
            <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: 10, padding: "14px 16px", border: "1px solid rgba(255,255,255,0.07)" }}>
              <TpProgression trade={trade} />
            </div>
          </div>

          {/* Times */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 10 }}>
              Timing
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              {[
                { label: "Opened", value: fmtDate(trade.open_time) },
                { label: "Closed", value: fmtDate(trade.close_time) || "—" },
                { label: "Age", value: relAge(trade.open_time) },
                { label: "Close Reason", value: trade.close_reason || "—" },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div style={{ fontSize: 10, color: C.textDim, marginBottom: 3 }}>{label}</div>
                  <div style={{ fontSize: 12, fontFamily: MONO, color: "#E8EAED" }}>{value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Result */}
          {(trade.status === "CLOSED" || trade.close_reason) && (
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 10 }}>
                Outcome
              </div>
              <div style={{
                background: (trade.pnl ?? 0) >= 0 ? "rgba(48,209,88,0.08)" : "rgba(255,69,58,0.08)",
                border: `1px solid ${(trade.pnl ?? 0) >= 0 ? "rgba(48,209,88,0.20)" : "rgba(255,69,58,0.20)"}`,
                borderRadius: 10, padding: "12px 14px",
              }}>
                <div style={{ fontSize: 10, color: C.label, textTransform: "uppercase", marginBottom: 6 }}>
                  {trade.close_reason || "Closed"}
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, fontFamily: MONO, color: (trade.pnl ?? 0) >= 0 ? C.positive : C.negative }}>
                  {fmtUsd(trade.pnl)}
                </div>
              </div>
            </div>
          )}
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

export default function TradesPage() {
  const [trades,  setTrades]  = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]  = useState("");
  const [tab,    setTab]     = useState<"OPEN" | "CLOSED" | "ALL">("OPEN");
  const [dirFlt, setDirFlt] = useState<"ALL" | "LONG" | "SHORT">("ALL");
  const [page,   setPage]   = useState(0);
  const [selected, setSelected] = useState<Trade | null>(null);
  const PAGE_SIZE = 25;

  const loadTrades = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/trades?all=true&limit=500");
      const d = await r.json();
      setTrades(Array.isArray(d) ? d : (d.trades ?? []));
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadTrades(); }, [loadTrades]);

  const closed = useMemo(() => trades.filter(t => t.status?.toUpperCase() === "CLOSED"), [trades]);
  const open   = useMemo(() => trades.filter(t => t.status?.toUpperCase() !== "CLOSED"), [trades]);
  const wins   = closed.filter(t => (t.pnl ?? 0) > 0).length;
  const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;
  const totalPnl = closed.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const avgPnl  = closed.length > 0 ? totalPnl / closed.length : 0;

  const filtered = useMemo(() => {
    let list = [...trades]
      .filter(t => tab === "ALL" || t.status?.toUpperCase() === tab)
      .filter(t => dirFlt === "ALL" || dirLabel(t.direction) === dirFlt)
      .filter(t => !search || t.symbol?.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => {
        const ta = b.close_time ?? b.open_time ?? "";
        const tb = a.close_time ?? a.open_time ?? "";
        return tb.localeCompare(ta);
      });
    return list;
  }, [trades, tab, dirFlt, search]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const pageSlice = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  useEffect(() => { setPage(0); }, [tab, dirFlt, search]);

  const card: React.CSSProperties = { background: C.bg, border: `1px solid ${C.border}`, borderRadius: C.radius };

  return (
    <>
      {/* KPI strip */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {loading ? (
          [0,1,2,3].map(i => (
            <div key={i} style={{ ...card, padding: "18px 20px" }}>
              <div className="ios-skeleton" style={{ height: 11, width: "55%", borderRadius: 4, marginBottom: 10 }} />
              <div className="ios-skeleton" style={{ height: 26, width: "70%", borderRadius: 6, marginBottom: 7 }} />
              <div className="ios-skeleton" style={{ height: 12, width: "60%", borderRadius: 4 }} />
            </div>
          ))
        ) : (
          [
            { label: "Total Trades", value: String(trades.length), color: "#E8EAED", sub: `${open.length} open · ${closed.length} closed` },
            { label: "Win Rate",     value: winRate.toFixed(1)+"%", color: winRate >= 50 ? C.positive : C.warning, sub: `${wins}/${closed.length} closed` },
            { label: "Net P&L",     value: fmtUsd(totalPnl), color: totalPnl > 0 ? C.positive : totalPnl < 0 ? C.negative : "#E8EAED", sub: "Closed trades" },
            { label: "Avg P&L",      value: fmtUsd(avgPnl), color: avgPnl > 0 ? C.positive : avgPnl < 0 ? C.negative : "#E8EAED", sub: "Per trade" },
          ].map(({ label, value, color, sub }) => (
            <div key={label} style={{ ...card, padding: "18px 20px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: MONO, letterSpacing: -0.5 }}>{value}</div>
              <div style={{ fontSize: 12, color: C.textDim, marginTop: 4 }}>{sub}</div>
            </div>
          ))
        )}
      </div>

      {/* Filter bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: "0 1 200px" }}>
          <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", fontSize: 18, color: "rgba(232,234,237,0.30)", fontFamily: "Material Symbols Outlined", fontWeight: 400, pointerEvents: "none" }}>search</span>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Symbol…"
            style={{ width: "100%", height: 38, paddingLeft: 36, paddingRight: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 8, color: "#E8EAED", fontSize: 13, fontFamily: "inherit", outline: "none", boxSizing: "border-box" }} />
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4 }}>
          {(["OPEN", "CLOSED", "ALL"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              height: 34, padding: "0 16px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit",
              fontSize: 12, fontWeight: 600,
              background: tab === t ? "rgba(99,212,255,0.15)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${tab === t ? "rgba(99,212,255,0.40)" : "rgba(255,255,255,0.08)"}`,
              color: tab === t ? C.cyan : C.textMid,
              transition: "all .1s",
            }}>
              {t} {t === "OPEN" ? `(${open.length})` : t === "CLOSED" ? `(${closed.length})` : ""}
            </button>
          ))}
        </div>

        {/* Direction */}
        <div style={{ display: "flex", gap: 4 }}>
          {(["ALL", "LONG", "SHORT"] as const).map(d => (
            <button key={d} onClick={() => setDirFlt(d)} style={{
              height: 34, padding: "0 14px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit",
              fontSize: 12, fontWeight: 600,
              background: dirFlt === d ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${dirFlt === d ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.08)"}`,
              color: dirFlt === d ? "#E8EAED" : C.textMid,
              transition: "all .1s",
            }}>
              {d}
            </button>
          ))}
        </div>

        <button onClick={loadTrades} title="Refresh" style={{
          height: 38, width: 38, borderRadius: 8, cursor: "pointer", fontFamily: "Material Symbols Outlined",
          background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
          color: C.textMid, fontSize: 20, fontWeight: 400, display: "flex", alignItems: "center", justifyContent: "center",
        }}>refresh</button>

        <span style={{ fontSize: 12, color: C.textDim, marginLeft: "auto" }}>
          {filtered.length} trade{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      <div style={{ ...card, overflow: "hidden" }}>
        <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
          {/* Header */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "90px 52px 90px 90px 60px 90px 70px 90px 100px",
            gap: 8, padding: "12px 20px", minWidth: 700,
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            fontSize: 10, fontWeight: 600, color: C.label,
            letterSpacing: 0.4, textTransform: "uppercase",
          }}>
            <span>Symbol</span><span>Dir</span><span>Entry</span><span>Exit/SL</span><span>Lots</span>
            <span style={{ textAlign: "right" }}>P&L</span>
            <span>TP Prog</span><span>Strategy</span><span>Time</span>
          </div>

          {/* Rows */}
          {loading ? (
            [0,1,2,3,4,5].map(i => (
              <div key={i} style={{
                display: "grid", gridTemplateColumns: "90px 52px 90px 90px 60px 90px 70px 90px 100px",
                gap: 8, padding: "10px 20px", minWidth: 700, borderBottom: "1px solid rgba(255,255,255,0.04)",
                alignItems: "center",
              }}>
                {[0,1,2,3,4,5,6,7,8].map(j => <div key={j} className="ios-skeleton" style={{ height: 12, borderRadius: 4 }} />)}
              </div>
            ))
          ) : pageSlice.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: C.textDim, fontSize: 13 }}>
              No trades match the current filters
            </div>
          ) : pageSlice.map((t, i) => {
            const isOpen = t.status?.toUpperCase() !== "CLOSED";
            const isLong = dirLabel(t.direction) === "LONG";
            const pnl    = Number(t.pnl ?? 0);
            const pnlColor = !isOpen ? (pnl > 0 ? C.positive : pnl < 0 ? C.negative : C.textMid) : C.textMid;

            return (
              <div
                key={t.id}
                onClick={() => setSelected(t)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "90px 52px 90px 90px 60px 90px 70px 90px 100px",
                  gap: 8, padding: "10px 20px", minWidth: 700,
                  borderBottom: i < pageSlice.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                  alignItems: "center", cursor: "pointer",
                  transition: "background .1s",
                }}
                onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                <span style={{ fontWeight: 600, color: "#E8EAED", fontSize: 13 }}>{t.symbol}</span>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.3, color: isLong ? C.positive : C.negative }}>
                  {isLong ? "LONG" : "SHORT"}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 12, color: "rgba(232,234,237,0.65)" }}>{fmtPrice(t.entry_price)}</span>
                <span style={{ fontFamily: MONO, fontSize: 12, color: "rgba(232,234,237,0.40)" }}>
                  {isOpen ? "—" : fmtPrice(t.stop_loss)}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 12, color: C.textMid }}>
                  {t.lot_size != null ? Number(t.lot_size).toFixed(2) : "—"}
                </span>
                <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 600, color: pnlColor, textAlign: "right" }}>
                  {isOpen ? "—" : fmtUsd(pnl)}
                </span>
                <TpProgression trade={t} />
                <span style={{ fontSize: 11, color: C.textMid, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {t.strategy ?? "—"}
                </span>
                <span style={{ fontSize: 11, color: C.textDim, fontFamily: MONO }}>
                  {fmtDate(t.close_time ?? t.open_time)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{
            height: 32, padding: "0 16px", borderRadius: 8, cursor: page === 0 ? "default" : "pointer",
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
            color: page === 0 ? "rgba(232,234,237,0.20)" : "#E8EAED", fontSize: 13, fontFamily: "inherit",
            opacity: page === 0 ? 0.4 : 1,
          }}>Prev</button>
          <span style={{ fontSize: 13, color: C.textDim }}>{page + 1} / {pageCount}</span>
          <button disabled={page >= pageCount - 1} onClick={() => setPage(p => p + 1)} style={{
            height: 32, padding: "0 16px", borderRadius: 8, cursor: page >= pageCount - 1 ? "default" : "pointer",
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
            color: page >= pageCount - 1 ? "rgba(232,234,237,0.20)" : "#E8EAED", fontSize: 13, fontFamily: "inherit",
            opacity: page >= pageCount - 1 ? 0.4 : 1,
          }}>Next</button>
        </div>
      )}

      {/* Trade drawer */}
      {selected && <TradeDrawer trade={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
