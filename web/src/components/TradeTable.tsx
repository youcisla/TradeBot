"use client";

import { useCallback, useEffect, useState } from "react";

interface Trade {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  pnl?: number;
  status: string;
  open_time: string;
  close_time?: string;
}

function fmtPrice(v: number | string | undefined): string {
  const n = typeof v === "string" ? parseFloat(v) : v as number;
  if (!n && n !== 0) return "—";
  if (n >= 100) return n.toFixed(2);
  if (n >= 1) return n.toFixed(4);
  return n.toFixed(5);
}

function fmtUsd(v: number | undefined | string): string {
  const n = typeof v === "string" ? parseFloat(v) : (v as number) ?? 0;
  if (isNaN(n)) return "—";
  const abs = Math.abs(n);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (n < 0 ? "-$" : "$") + f;
}

function relAge(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000) return Math.floor(ms / 60_000) + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return Math.floor(ms / 86_400_000) + "d";
}

type Filter = "ALL" | "OPEN" | "CLOSED";

export default function TradeTable() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filter, setFilter] = useState<Filter>("CLOSED");
  const [symbolFilter, setSymbolFilter] = useState("ALL");

  const fetchTrades = useCallback(async () => {
    try {
      const r = await fetch("/api/broker/trades?days=30");
      if (r.ok) {
        const data = await r.json();
        if (Array.isArray(data)) setTrades(data);
      }
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    fetchTrades();
    const id = setInterval(fetchTrades, 8_000);
    return () => clearInterval(id);
  }, [fetchTrades]);

  const filtered = trades.filter((t) => {
    if (filter === "OPEN") return t.status === "OPEN" || t.status === "PARTIAL";
    if (filter === "CLOSED") return t.status === "CLOSED";
    return true;
  });

  const bySymbol = symbolFilter === "ALL"
    ? filtered
    : filtered.filter((t) => t.symbol === symbolFilter);

  const symbols = Array.from(new Set(trades.map((t) => t.symbol))).sort();

  // Today's closed stats
  const today = new Date().toDateString();
  const todayClosed = bySymbol.filter(
    (t) => t.status === "CLOSED" && t.close_time && new Date(t.close_time).toDateString() === today
  );
  const todayPnl = todayClosed.reduce((s, t) => s + parseFloat(String(t.pnl ?? 0)), 0);
  const wins = todayClosed.filter((t) => parseFloat(String(t.pnl ?? 0)) > 0).length;
  const losses = todayClosed.filter((t) => parseFloat(String(t.pnl ?? 0)) < 0).length;
  const winRate = todayClosed.length > 0 ? (wins / todayClosed.length) * 100 : 0;

  return (
    <div style={styles.widget}>
      {/* Header row */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.title}>Trades</span>
          {todayPnl !== 0 && (
            <span style={{ ...styles.chip, color: todayPnl >= 0 ? "#16A34A" : "#DC2626" }}>
              {todayPnl >= 0 ? "+" : ""}{fmtUsd(todayPnl)}
            </span>
          )}
        </div>

        {/* Symbol filter */}
        <div style={styles.symFilter}>
          <button
            onClick={() => setSymbolFilter("ALL")}
            style={{ ...styles.symBtn, ...(symbolFilter === "ALL" ? styles.symBtnActive : {}) }}
          >
            ALL
          </button>
          {symbols.map((s) => (
            <button
              key={s}
              onClick={() => setSymbolFilter(s)}
              style={{ ...styles.symBtn, ...(symbolFilter === s ? styles.symBtnActive : {}) }}
            >
              {s.replace("USD", "").replace(".s", "")}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <div style={styles.filters}>
          {(["ALL", "OPEN", "CLOSED"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{ ...styles.tab, ...(filter === f ? styles.tabActive : {}) }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Stats strip */}
      <div style={styles.stats}>
        <span style={styles.stat}>
          <span style={styles.statVal}>{winRate.toFixed(0)}%</span>
          <span style={styles.statLabel}>win</span>
        </span>
        <span style={styles.stat}>
          <span style={styles.statVal}>{wins}W</span>
          <span style={styles.statLabel}>{losses}L</span>
        </span>
        <span style={styles.stat}>
          <span style={{ ...styles.statVal, color: "#111111" }}>{bySymbol.length}</span>
          <span style={styles.statLabel}>trades</span>
        </span>
      </div>

      {/* Table */}
      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr style={styles.thRow}>
              <th style={styles.th}>Symbol</th>
              <th style={styles.th}>Dir</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Lot</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Entry</th>
              <th style={{ ...styles.th, textAlign: "right" }}>SL</th>
              <th style={{ ...styles.th, textAlign: "right" }}>P&L</th>
              <th style={{ ...styles.th, textAlign: "right" }}>Age</th>
            </tr>
          </thead>
          <tbody>
            {bySymbol.length === 0 ? (
              <tr>
                <td colSpan={7} style={styles.empty}>No trades</td>
              </tr>
            ) : (
              bySymbol.slice(0, 50).map((t) => {
                const pnl = parseFloat(String(t.pnl ?? 0));
                return (
                  <tr key={t.id} style={styles.row}>
                    <td style={styles.td}><span style={styles.sym}>{t.symbol}</span></td>
                    <td style={styles.td}>
                      <span style={{ ...styles.dir, color: t.direction === "BUY" ? "#16A34A" : "#DC2626" }}>
                        {t.direction === "BUY" ? "▲" : "▼"}
                      </span>
                    </td>
                    <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>
                      {String(t.lot_size ?? "—")}
                    </td>
                    <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>
                      {fmtPrice(t.entry_price)}
                    </td>
                    <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#DC2626" }}>
                      {t.stop_loss ? fmtPrice(t.stop_loss) : "—"}
                    </td>
                    <td style={{
                      ...styles.td,
                      textAlign: "right",
                      fontFamily: "'IBM Plex Mono', monospace",
                      fontSize: 11,
                      fontWeight: 700,
                      color: t.status === "OPEN" ? "#111111" : pnl > 0 ? "#16A34A" : pnl < 0 ? "#DC2626" : "#9CA3AF",
                    }}>
                      {t.status === "OPEN" ? "—" : (pnl >= 0 ? "+" : "") + fmtUsd(pnl)}
                    </td>
                    <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#9CA3AF" }}>
                      {relAge(t.close_time ?? t.open_time)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  widget: {
    background: "#FFFFFF",
    display: "flex",
    flexDirection: "column",
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 12px 6px",
    borderBottom: "1px solid #F0F0F0",
    flexShrink: 0,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexShrink: 0,
  },
  title: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    color: "#111111",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  chip: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    fontWeight: 700,
    padding: "1px 6px",
    borderRadius: 3,
  },
  symFilter: {
    display: "flex",
    gap: 2,
    flex: 1,
    overflowX: "auto",
  },
  symBtn: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "2px 6px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    whiteSpace: "nowrap",
  },
  symBtnActive: {
    background: "#F0F0F0",
    color: "#111111",
    fontWeight: 700,
  },
  filters: {
    display: "flex",
    gap: 2,
    flexShrink: 0,
  },
  tab: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "2px 8px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
  },
  tabActive: {
    background: "#F0F0F0",
    color: "#111111",
    fontWeight: 700,
  },
  stats: {
    display: "flex",
    gap: 16,
    padding: "4px 12px 6px",
    borderBottom: "1px solid #F8F8F8",
    flexShrink: 0,
  },
  stat: {
    display: "flex",
    alignItems: "baseline",
    gap: 3,
  },
  statVal: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    color: "#111111",
  },
  statLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
  },
  tableWrap: {
    flex: 1,
    overflowY: "auto",
    minHeight: 0,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    tableLayout: "fixed",
  },
  thRow: {
    background: "#FAFAFA",
    position: "sticky",
    top: 0,
  },
  th: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "4px 8px",
    textAlign: "left",
    fontWeight: 500,
    borderBottom: "1px solid #F0F0F0",
  },
  row: {
    borderBottom: "1px solid #FAFAFA",
  },
  td: {
    padding: "5px 8px",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#111111",
  },
  sym: {
    fontWeight: 700,
    fontSize: 10,
  },
  dir: {
    fontSize: 9,
    fontWeight: 700,
  },
  empty: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    textAlign: "center",
    padding: "16px 0",
    fontStyle: "italic",
  },
};
