"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { DirectionBadge } from "@/components/ui/Badges";
import { formatPrice, fmtPnl, relTime } from "@/lib/format";
import { sendCommand } from "@/lib/ws";

export default function PositionsCard() {
  const { openTrades } = useAppShell();
  const [closingId, setClosingId] = useState<number | null>(null);

  async function handleClose(id: number) {
    setClosingId(id);
    await sendCommand("close_trade", { trade_id: id });
    setClosingId(null);
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.title}>Open Positions</span>
        <span style={styles.count}>{openTrades.length}</span>
      </div>

      <div style={styles.table}>
        {/* Column headers */}
        <div style={styles.rowHeader}>
          <span style={styles.colSymbol}>Symbol</span>
          <span style={styles.colDir}>Dir</span>
          <span style={styles.colEntry}>Entry</span>
          <span style={styles.colPnL}>PnL</span>
          <span style={styles.colSL}>SL</span>
          <span style={styles.colAge}>Age</span>
          <span style={styles.colAction}></span>
        </div>

        {openTrades.length === 0 ? (
          <p style={styles.empty}>No open positions</p>
        ) : (
          openTrades.map((trade) => (
            <div key={trade.id} style={styles.row}>
              <span style={styles.colSymbol}>
                <strong style={styles.symbol}>{trade.symbol}</strong>
                {trade.strategy && (
                  <span style={styles.strategy}>{trade.strategy}</span>
                )}
              </span>
              <span style={styles.colDir}>
                <DirectionBadge direction={trade.direction} />
              </span>
              <span style={styles.colEntry}>
                {formatPrice(trade.entry_price)}
              </span>
              <span
                style={{
                  ...styles.colPnL,
                  ...(typeof trade.pnl === "number" && trade.pnl < 0
                    ? styles.pnlNeg
                    : styles.pnlPos),
                }}
              >
                {fmtPnl(trade.pnl)}
              </span>
              <span style={styles.colSL}>
                {trade.sl ? formatPrice(trade.sl) : "—"}
              </span>
              <span style={styles.colAge}>
                {relTime(trade.open_time)}
              </span>
              <span style={styles.colAction}>
                <button
                  style={styles.closeBtn}
                  onClick={() => handleClose(trade.id)}
                  disabled={closingId === trade.id}
                >
                  {closingId === trade.id ? "…" : "✕"}
                </button>
              </span>
            </div>
          ))
        )}
      </div>
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
  count: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--accent)",
    background: "rgba(0,220,130,0.1)",
    border: "1px solid rgba(0,220,130,0.25)",
    borderRadius: 9999,
    padding: "1px 8px",
  },
  table: {
    overflowY: "auto",
    flex: 1,
  },
  rowHeader: {
    display: "flex",
    alignItems: "center",
    padding: "4px var(--space-4)",
    borderBottom: "1px solid var(--border)",
    background: "var(--bg-3)",
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  row: {
    display: "flex",
    alignItems: "center",
    padding: "6px var(--space-4)",
    borderBottom: "1px solid var(--border)",
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    gap: "var(--space-2)",
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    textAlign: "center",
    padding: "var(--space-5)",
    margin: 0,
  },
  colSymbol: {
    flex: 2,
    display: "flex",
    flexDirection: "column",
    gap: 1,
    minWidth: 0,
  },
  symbol: {
    fontWeight: 700,
    color: "var(--text-1)",
    fontSize: 12,
  },
  strategy: {
    fontSize: 9,
    color: "var(--text-3)",
    fontWeight: 400,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  colDir: {
    flex: 0,
    minWidth: 52,
  },
  colEntry: {
    flex: 1,
    color: "var(--text-2)",
    textAlign: "right",
  },
  colPnL: {
    flex: 1,
    textAlign: "right",
    fontWeight: 700,
  },
  pnlPos: { color: "var(--green)" },
  pnlNeg: { color: "var(--red)" },
  colSL: {
    flex: 1,
    color: "var(--text-3)",
    textAlign: "right",
  },
  colAge: {
    flex: 0,
    minWidth: 60,
    color: "var(--text-3)",
    textAlign: "right",
  },
  colAction: {
    flex: 0,
    minWidth: 28,
    textAlign: "right",
  },
  closeBtn: {
    background: "none",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-3)",
    cursor: "pointer",
    fontSize: 10,
    padding: "2px 5px",
    lineHeight: 1,
  },
};
