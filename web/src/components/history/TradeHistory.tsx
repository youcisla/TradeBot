"use client";

import { useState } from "react";
import { useAllTrades } from "@/lib/swr";
import { DirectionBadge, StrategyBadge } from "@/components/ui/Badges";
import { formatPrice, fmtPnl, fmtDateTime } from "@/lib/format";

const PAGE_SIZE = 30;

export default function TradeHistory() {
  const { data: trades = [] } = useAllTrades(500);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<"all" | "closed" | "open">("closed");

  const filtered = trades.filter((t) => {
    if (filter === "closed") return t.status === "CLOSED";
    if (filter === "open")   return t.status === "OPEN" || t.status === "PARTIAL";
    return true;
  });

  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  return (
    <div style={styles.wrapper}>
      {/* Header + filter */}
      <div style={styles.header}>
        <span style={styles.title}>Trade History</span>
        <div style={styles.filters}>
          {(["all", "closed", "open"] as const).map((f) => (
            <button
              key={f}
              style={{
                ...styles.filterBtn,
                ...(filter === f ? styles.filterBtnActive : {}),
              }}
              onClick={() => { setFilter(f); setPage(0); }}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={styles.tableWrap}>
        <div style={styles.tableHeader}>
          {["Date", "Symbol", "Dir", "Strategy", "Entry", "Exit", "P&L"].map((h) => (
            <span key={h} style={styles.th}>{h}</span>
          ))}
        </div>

        {paginated.length === 0 ? (
          <p style={styles.empty}>No trades</p>
        ) : (
          paginated.map((trade) => (
            <div key={trade.id} style={styles.row}>
              <span style={styles.td}>
                {trade.close_time ? fmtDateTime(trade.close_time) : "—"}
              </span>
              <span style={styles.td}>
                <strong style={styles.symbol}>{trade.symbol}</strong>
              </span>
              <span style={styles.td}>
                <DirectionBadge direction={trade.direction} />
              </span>
              <span style={styles.td}>
                {trade.strategy && <StrategyBadge strategy={trade.strategy} />}
              </span>
              <span style={styles.td}>{formatPrice(trade.entry_price)}</span>
              <span style={styles.td}>
                {trade.pnl != null ? formatPrice(trade.pnl) : "—"}
              </span>
              <span
                style={{
                  ...styles.td,
                  ...styles.pnlCell,
                  ...(typeof trade.pnl === "number" && trade.pnl < 0
                    ? styles.pnlNeg
                    : styles.pnlPos),
                }}
              >
                {fmtPnl(trade.pnl)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={styles.pagination}>
          <button
            style={styles.pageBtn}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            ←
          </button>
          <span style={styles.pageInfo}>
            {page + 1} / {totalPages}
          </span>
          <button
            style={styles.pageBtn}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            →
          </button>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-3) var(--space-4)",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  title: {
    fontFamily: "var(--font-ui)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-2)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  filters: {
    display: "flex",
    gap: "var(--space-1)",
  },
  filterBtn: {
    background: "none",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-3)",
    cursor: "pointer",
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    padding: "2px 6px",
    letterSpacing: "0.05em",
  },
  filterBtnActive: {
    background: "var(--bg-3)",
    border:     "1px solid var(--border-active)",
    color:      "var(--text-1)",
  },
  tableWrap: {
    overflowY: "auto",
    flex: 1,
  },
  tableHeader: {
    display: "grid",
    gridTemplateColumns: "120px 80px 64px 80px 80px 80px 80px",
    padding: "4px var(--space-4)",
    background: "var(--bg-3)",
    borderBottom: "1px solid var(--border)",
    gap: "var(--space-2)",
  },
  th: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  row: {
    display: "grid",
    gridTemplateColumns: "120px 80px 64px 80px 80px 80px 80px",
    padding: "6px var(--space-4)",
    borderBottom: "1px solid var(--border)",
    gap: "var(--space-2)",
    alignItems: "center",
  },
  td: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-2)",
  },
  symbol: {
    fontWeight: 700,
    color: "var(--text-1)",
  },
  pnlCell: {
    textAlign: "right",
    fontWeight: 700,
  },
  pnlPos: { color: "var(--green)" },
  pnlNeg: { color: "var(--red)" },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    textAlign: "center",
    padding: "var(--space-5)",
    margin: 0,
  },
  pagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "var(--space-3)",
    padding: "var(--space-3)",
    borderTop: "1px solid var(--border)",
    flexShrink: 0,
  },
  pageBtn: {
    background: "var(--bg-3)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-1)",
    cursor: "pointer",
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    padding: "4px 10px",
  },
  pageInfo: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
  },
};
