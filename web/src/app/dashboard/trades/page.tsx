"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

//  Types 

interface Trade {
  id: number;
  symbol: string;
  strategy?: string;
  direction: string;
  entry_price: number;
  lot_size?: number;
  stop_loss?: number;
  take_profit_1?: number;
  status: string;
  open_time?: string;
  close_time?: string;
  pnl?: number;
  close_reason?: string;
}

//  Helpers 

function fmtUsd(v: number | undefined): string {
  const n = Number(v ?? 0);
  const abs = Math.abs(n);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (n < 0 ? "-$" : "$") + f;
}

function fmtPrice(v: number): string {
  const n = Number(v);
  if (!n && n !== 0) return "—";
  if (n >= 100) return n.toFixed(2);
  if (n >= 1)   return n.toFixed(4);
  return n.toFixed(5);
}

function fmtDate(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + " " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function dirLabel(d: string): "LONG" | "SHORT" {
  return /buy|long/i.test(d) ? "LONG" : "SHORT";
}

//  Page 

const PAGE_SIZE = 25;

export default function TradeBookPage() {
  const [trades,    setTrades]    = useState<Trade[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [search,    setSearch]    = useState("");
  const [statusFlt, setStatusFlt] = useState<"ALL" | "OPEN" | "CLOSED">("ALL");
  const [dirFlt,    setDirFlt]    = useState<"ALL" | "LONG" | "SHORT">("ALL");
  const [page,      setPage]      = useState(0);

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

  //  Derived stats (closed trades only)
  const closed     = useMemo(() => trades.filter(t => t.status?.toUpperCase() === "CLOSED"), [trades]);
  const open_      = useMemo(() => trades.filter(t => t.status?.toUpperCase() !== "CLOSED"), [trades]);
  const wins       = closed.filter(t => (t.pnl ?? 0) > 0).length;
  const winRate    = closed.length > 0 ? (wins / closed.length) * 100 : 0;
  const totalPnl   = closed.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const avgPnl     = closed.length > 0 ? totalPnl / closed.length : 0;

  //  Filtered + sorted list
  const filtered = useMemo(() => {
    let list = [...trades].sort((a, b) => {
      const ta = a.close_time ?? a.open_time ?? "";
      const tb = b.close_time ?? b.open_time ?? "";
      return tb.localeCompare(ta);
    });
    if (search)           list = list.filter(t => t.symbol?.toLowerCase().includes(search.toLowerCase()));
    if (statusFlt !== "ALL") list = list.filter(t => t.status?.toUpperCase() === statusFlt);
    if (dirFlt    !== "ALL") list = list.filter(t => dirLabel(t.direction) === dirFlt);
    return list;
  }, [trades, search, statusFlt, dirFlt]);

  const pageCount   = Math.ceil(filtered.length / PAGE_SIZE);
  const pageSlice   = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Reset to page 0 on filter change
  useEffect(() => { setPage(0); }, [search, statusFlt, dirFlt]);

  //  Styles
  const card: React.CSSProperties = {
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)", borderRadius: 12,
  };
  const kpiLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.55)",
    letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6,
  };
  const MONO = '"SF Mono", SFMono-Regular, ui-monospace, monospace';

  function FilterBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
    return (
      <button
        onClick={onClick}
        style={{
          height: 30, padding: "0 14px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit",
          fontSize: 12, fontWeight: 600,
          background: active ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.04)",
          border:     active ? "1px solid rgba(255,255,255,0.25)" : "1px solid rgba(255,255,255,0.08)",
          color:      active ? "#E8EAED" : "rgba(232,234,237,0.45)",
        }}
      >
        {label}
      </button>
    );
  }

  return (
    <>
      {/*  Filter bar  */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        {/* Symbol search */}
        <div style={{ position: "relative", flex: "1 1 180px", maxWidth: 260 }}>
          <span style={{
            position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)",
            fontSize: 18, color: "rgba(232,234,237,0.30)", fontFamily: "Material Symbols Outlined",
            fontWeight: 400, pointerEvents: "none",
          }}>
            search
          </span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Symbol…"
            style={{
              width: "100%", height: 38, paddingLeft: 36, paddingRight: 12,
              background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)",
              borderRadius: 8, color: "#E8EAED", fontSize: 13, fontFamily: "inherit",
              outline: "none", boxSizing: "border-box",
            }}
          />
        </div>

        {/* Status filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {(["ALL", "OPEN", "CLOSED"] as const).map(s => (
            <FilterBtn key={s} label={s} active={statusFlt === s} onClick={() => setStatusFlt(s)} />
          ))}
        </div>

        {/* Direction filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {(["ALL", "LONG", "SHORT"] as const).map(d => (
            <FilterBtn key={d} label={d} active={dirFlt === d} onClick={() => setDirFlt(d)} />
          ))}
        </div>

        {/* Refresh */}
        <button
          onClick={loadTrades}
          style={{
            height: 38, width: 38, borderRadius: 8, cursor: "pointer", fontFamily: "Material Symbols Outlined",
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
            color: "rgba(232,234,237,0.55)", fontSize: 20, fontWeight: 400,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
          title="Refresh"
        >
          refresh
        </button>

        <span style={{ fontSize: 12, color: "rgba(232,234,237,0.30)", marginLeft: "auto" }}>
          {filtered.length} trade{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/*  Summary KPIs  */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Total Trades",  value: String(trades.length),            color: "#E8EAED",                              sub: `${open_.length} open` },
          { label: "Win Rate",      value: winRate.toFixed(1) + "%",          color: winRate >= 50 ? "#34C759" : "#FF9F0A", sub: `${wins} / ${closed.length} closed` },
          { label: "Net P&L",       value: fmtUsd(totalPnl),                  color: totalPnl > 0 ? "#34C759" : totalPnl < 0 ? "#FF3B30" : "#E8EAED", sub: "Closed trades" },
          { label: "Avg P&L / Trade", value: fmtUsd(avgPnl),                  color: avgPnl > 0 ? "#34C759" : avgPnl < 0 ? "#FF3B30" : "#E8EAED",    sub: "Per closed trade" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} style={{ ...card, padding: "18px 20px" }}>
            <div style={kpiLabel}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: MONO, letterSpacing: -0.5 }}>{value}</div>
            <div style={{ fontSize: 12, color: "rgba(232,234,237,0.30)", marginTop: 4 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/*  Trade Table  */}
      <div style={{ ...card, overflow: "hidden" }}>
        {/* Table header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "120px 60px 110px 110px 70px 90px 80px 1fr 120px",
          gap: 8, padding: "12px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.40)",
          letterSpacing: 0.4, textTransform: "uppercase",
        }}>
          <span>Symbol</span>
          <span>Dir</span>
          <span>Entry</span>
          <span>Exit/SL</span>
          <span>Lots</span>
          <span style={{ textAlign: "right" }}>P&L</span>
          <span>Status</span>
          <span>Strategy</span>
          <span>Time</span>
        </div>

        {/* Rows */}
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "rgba(232,234,237,0.30)", fontSize: 14 }}>
            Loading…
          </div>
        ) : pageSlice.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "rgba(232,234,237,0.30)", fontSize: 14 }}>
            No trades match the current filters
          </div>
        ) : pageSlice.map((t, i) => {
          const isOpen   = t.status?.toUpperCase() !== "CLOSED";
          const isLong   = dirLabel(t.direction) === "LONG";
          const pnl      = t.pnl ?? 0;
          const pnlColor = pnl > 0 ? "#34C759" : pnl < 0 ? "#FF3B30" : "rgba(232,234,237,0.40)";
          return (
            <div
              key={t.id}
              style={{
                display: "grid",
                gridTemplateColumns: "120px 60px 110px 110px 70px 90px 80px 1fr 120px",
                gap: 8,
                padding: "10px 20px",
                borderBottom: i < pageSlice.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                alignItems: "center",
                opacity: isOpen ? 1 : 0.75,
              }}
            >
              <span style={{ color: "#E8EAED", fontWeight: 600, fontSize: 13 }}>{t.symbol}</span>
              <span style={{
                fontSize: 11, fontWeight: 700, letterSpacing: 0.3,
                color: isLong ? "#34C759" : "#FF3B30",
              }}>
                {isLong ? "LONG" : "SHORT"}
              </span>
              <span style={{ fontFamily: MONO, fontSize: 12, color: "rgba(232,234,237,0.65)" }}>
                {fmtPrice(t.entry_price)}
              </span>
              <span style={{ fontFamily: MONO, fontSize: 12, color: "rgba(232,234,237,0.40)" }}>
                {isOpen ? "—" : fmtPrice(t.stop_loss ?? 0)}
              </span>
              <span style={{ fontFamily: MONO, fontSize: 12, color: "rgba(232,234,237,0.55)" }}>
                {t.lot_size != null ? Number(t.lot_size).toFixed(2) : "—"}
              </span>
              <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 600, color: pnlColor, textAlign: "right" }}>
                {isOpen ? "—" : fmtUsd(pnl)}
              </span>
              <span>
                <span style={{
                  display: "inline-block",
                  padding: "2px 8px", borderRadius: 4,
                  fontSize: 11, fontWeight: 600, letterSpacing: 0.2,
                  background: isOpen ? "rgba(10,132,255,0.12)" : "rgba(255,255,255,0.06)",
                  color:      isOpen ? "#0A84FF"              : "rgba(232,234,237,0.40)",
                }}>
                  {isOpen ? "OPEN" : "CLOSED"}
                </span>
              </span>
              <span style={{ fontSize: 12, color: "rgba(232,234,237,0.40)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {t.strategy ?? "—"}
              </span>
              <span style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", fontFamily: MONO }}>
                {fmtDate(t.close_time ?? t.open_time)}
              </span>
            </div>
          );
        })}
      </div>

      {/*  Pagination  */}
      {pageCount > 1 && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 16 }}>
          <button
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
            style={{
              height: 32, padding: "0 16px", borderRadius: 8, cursor: page === 0 ? "default" : "pointer",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
              color: page === 0 ? "rgba(232,234,237,0.20)" : "#E8EAED", fontSize: 13, fontFamily: "inherit",
              opacity: page === 0 ? 0.4 : 1,
            }}
          > Prev</button>
          <span style={{ fontSize: 13, color: "rgba(232,234,237,0.40)" }}>
            {page + 1} / {pageCount}
          </span>
          <button
            disabled={page >= pageCount - 1}
            onClick={() => setPage(p => p + 1)}
            style={{
              height: 32, padding: "0 16px", borderRadius: 8, cursor: page >= pageCount - 1 ? "default" : "pointer",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.09)",
              color: page >= pageCount - 1 ? "rgba(232,234,237,0.20)" : "#E8EAED", fontSize: 13, fontFamily: "inherit",
              opacity: page >= pageCount - 1 ? 0.4 : 1,
            }}
          >Next </button>
        </div>
      )}
    </>
  );
}