"use client";

import { useCallback, useEffect, useState } from "react";

interface Trade {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  close_price?: number;
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
  const n = typeof v === "string" ? parseFloat(v) : v as number;
  if (isNaN(n)) return "—";
  const abs = Math.abs(n);
  const f = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return (n < 0 ? "-$" : "$") + f;
}

function relAge(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000) return Math.floor(ms / 60_000) + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return Math.floor(ms / 86_400_000) + "d";
}

export default function TradesWidget() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [tab, setTab] = useState<"OPEN" | "CLOSED">("CLOSED");
  const [showAll, setShowAll] = useState(false);
  const [page, setPage] = useState(0);

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

  const closed = trades.filter((t) => t.status === "CLOSED");
  const open = trades.filter((t) => t.status === "OPEN" || t.status === "PARTIAL");
  const visible = tab === "OPEN" ? open : closed;

  // Today's closed trades
  const today = new Date().toDateString();
  const todayClosed = closed.filter(
    (t) => t.close_time && new Date(t.close_time).toDateString() === today
  );
  const todayPnl = todayClosed.reduce((s, t) => s + (parseFloat(String(t.pnl ?? 0))), 0);
  const wins = todayClosed.filter((t) => parseFloat(String(t.pnl ?? 0)) > 0);
  const losses = todayClosed.filter((t) => parseFloat(String(t.pnl ?? 0)) < 0);
  const winRate = todayClosed.length > 0
    ? (wins.length / todayClosed.length) * 100 : 0;

  const pnlColor = todayPnl >= 0 ? "#16A34A" : "#DC2626";

  return (
    <div style={styles.widget}>
      {/* Widget header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.title}>Trades</span>
          {todayClosed.length > 0 && (
            <span
              style={{
                ...styles.pnlChip,
                color: pnlColor,
                background: todayPnl >= 0 ? "rgba(22,163,74,0.08)" : "rgba(220,38,38,0.08)",
              }}
            >
              {todayPnl >= 0 ? "+" : ""}
              {fmtUsd(todayPnl)}
            </span>
          )}
        </div>
        <div style={styles.headerRight}>
          <div style={styles.tabs}>
            {(["OPEN", "CLOSED"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                style={{
                  ...styles.tab,
                  ...(tab === t ? styles.tabActive : {}),
                }}
              >
                {t}
                {t === "OPEN" ? ` (${open.length})` : ` (${closed.length})`}
              </button>
            ))}
          </div>
          <button onClick={() => setCollapsed((v) => !v)} style={styles.collapseBtn}>
            {collapsed ? "▸" : "▾"}
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          {/* Summary strip */}
          <div style={styles.summary}>
            <span style={styles.summaryItem}>
              <span style={styles.summaryValue}>{winRate.toFixed(0)}%</span>
              <span style={styles.summaryLabel}>win rate</span>
            </span>
            <span style={styles.summaryDivider} />
            <span style={styles.summaryItem}>
              <span style={styles.summaryValue}>{wins.length}W</span>
              <span style={styles.summaryLabel}>{losses.length}L</span>
            </span>
            <span style={styles.summaryDivider} />
            <span style={styles.summaryItem}>
              <span style={{ ...styles.summaryValue, color: pnlColor }}>
                {todayPnl >= 0 ? "+" : ""}
                {fmtUsd(todayPnl)}
              </span>
              <span style={styles.summaryLabel}>today</span>
            </span>
          </div>

          {/* Table */}
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeadRow}>
                  <th style={styles.th}>Symbol</th>
                  <th style={styles.th}>Dir</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Lot</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Entry</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>P&L</th>
                  <th style={{ ...styles.th, textAlign: "right" }}>Age</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={styles.empty}>
                      No {tab.toLowerCase()} trades
                    </td>
                  </tr>
                ) : (
                  (showAll ? visible : visible.slice(page * 20, (page + 1) * 20)).map((t) => {
                    const pnl = parseFloat(String(t.pnl ?? 0));
                    const pnlCellColor =
                      t.status === "OPEN"
                        ? "#111111"
                        : pnl > 0
                        ? "#16A34A"
                        : pnl < 0
                        ? "#DC2626"
                        : "#9CA3AF";
                    return (
                      <tr key={t.id} style={styles.row}>
                        <td style={styles.td}>
                          <span style={styles.sym}>{t.symbol}</span>
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.dir,
                              color: t.direction === "BUY" ? "#16A34A" : "#DC2626",
                            }}
                          >
                            {t.direction === "BUY" ? "▲" : "▼"}
                          </span>
                        </td>
                        <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>
                          {String(t.lot_size ?? "—")}
                        </td>
                        <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>
                          {fmtPrice(t.entry_price)}
                        </td>
                        <td
                          style={{
                            ...styles.td,
                            textAlign: "right",
                            fontFamily: "'IBM Plex Mono', monospace",
                            fontSize: 12,
                            fontWeight: 700,
                            color: pnlCellColor,
                          }}
                        >
                          {t.status === "OPEN" ? "—" : (pnl >= 0 ? "+" : "") + fmtUsd(pnl)}
                        </td>
                        <td style={{ ...styles.td, textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#9CA3AF" }}>
                          {relAge(t.close_time ?? t.open_time)}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination or show all */}
          {visible.length > 20 && (
            <div style={styles.pagination}>
              {!showAll ? (
                <>
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    style={styles.pageBtn}
                  >
                    ←
                  </button>
                  <span style={styles.pageInfo}>
                    {page * 20 + 1}–{Math.min((page + 1) * 20, visible.length)} of {visible.length}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={(page + 1) * 20 >= visible.length}
                    style={styles.pageBtn}
                  >
                    →
                  </button>
                  <button onClick={() => { setShowAll(true); setPage(0); }} style={styles.pageBtn}>
                    Show all
                  </button>
                </>
              ) : (
                <button onClick={() => setShowAll(false)} style={styles.pageBtn}>
                  Paginate
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  widget: {
    background: "#FFFFFF",
    borderTop: "1px solid #F5F5F7",
    display: "flex",
    flexDirection: "column",
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "10px 14px 8px",
    gap: 12,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  title: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    color: "#111111",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  pnlChip: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    padding: "2px 7px",
    borderRadius: 4,
  },
  tabs: {
    display: "flex",
    gap: 2,
  },
  tab: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "3px 8px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
  },
  tabActive: {
    background: "#F5F5F7",
    color: "#111111",
    fontWeight: 700,
  },
  collapseBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: 11,
    color: "#9CA3AF",
    padding: "2px 4px",
  },
  summary: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "4px 14px 8px",
    borderBottom: "1px solid #F5F5F7",
  },
  summaryItem: {
    display: "flex",
    alignItems: "baseline",
    gap: 4,
  },
  summaryValue: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    fontWeight: 700,
    color: "#111111",
  },
  summaryLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
  },
  summaryDivider: {
    width: 1,
    height: 12,
    background: "#E5E7EB",
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
  tableHeadRow: {
    background: "#FAFAFA",
  },
  th: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "5px 10px",
    textAlign: "left",
    fontWeight: 500,
    borderBottom: "1px solid #F5F5F7",
  },
  row: {
    borderBottom: "1px solid #FAFAFA",
  },
  td: {
    padding: "7px 10px",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#111111",
  },
  sym: {
    fontWeight: 700,
    fontSize: 11,
  },
  dir: {
    fontSize: 10,
    fontWeight: 700,
  },
  empty: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    textAlign: "center",
    padding: "20px 0",
    fontStyle: "italic",
  },
  pagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    padding: "8px 14px",
    borderTop: "1px solid #F5F5F7",
    flexShrink: 0,
  },
  pageBtn: {
    background: "none",
    border: "1px solid #E5E7EB",
    borderRadius: 3,
    padding: "3px 10px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#6B7280",
  },
  pageInfo: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
  },
};
