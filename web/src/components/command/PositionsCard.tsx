"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { DirectionBadge } from "@/components/shared/DirectionBadge";
import { formatPrice, fmtPnl, relTime } from "@/lib/format";
import { sendCommand } from "@/lib/ws";
import { cn } from "@/lib/utils";

export default function PositionsCard() {
  const { openTrades } = useAppShell();
  const [closingId, setClosingId] = useState<number | null>(null);

  async function handleClose(id: number) {
    setClosingId(id);
    await sendCommand("close_trade", { trade_id: id });
    setClosingId(null);
  }

  return (
    <div className="flex flex-col" role="table" aria-label="Open positions">
      {/* Column headers */}
      <div
        className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2 border-b bg-[var(--bg-3)] border-[var(--border)]"
        role="row"
      >
        {["Symbol", "Dir", "Entry", "PnL", "SL", "Age", ""].map((h, i) => (
          <span
            key={h}
            role="columnheader"
            className="font-mono text-xs font-bold uppercase tracking-widest"
            style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.06em" }}
            aria-colindex={i + 1}
          >
            {h}
          </span>
        ))}
      </div>

      {/* Rows */}
      {openTrades.length === 0 ? (
        <div
          className="flex items-center justify-center py-10 font-mono text-sm"
          style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          No open positions
        </div>
      ) : (
        openTrades.map((trade) => (
          <div
            key={trade.id}
            className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2.5 border-b border-[var(--border-subtle)] transition-colors group"
            role="row"
          >
            {/* Symbol */}
            <div className="flex flex-col gap-0.5 min-w-0" role="cell">
              <span
                className="font-mono font-bold"
                style={{ color: "var(--text-1)", fontSize: 12 }}
              >
                {trade.symbol}
              </span>
              {trade.strategy && (
                <span
                  className="font-mono uppercase"
                  style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.04em" }}
                >
                  {trade.strategy}
                </span>
              )}
            </div>

            {/* Direction */}
            <div role="cell">
              <DirectionBadge direction={trade.direction} />
            </div>

            {/* Entry */}
            <span
              className="font-mono text-right"
              role="cell"
              style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {formatPrice(trade.entry_price)}
            </span>

            {/* PnL */}
            <span
              className="font-mono text-right font-bold"
              role="cell"
              style={{
                color: typeof trade.pnl === "number" && trade.pnl < 0
                  ? "var(--negative)"
                  : "var(--positive)",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
              }}
            >
              {fmtPnl(trade.pnl)}
            </span>

            {/* SL */}
            <span
              className="font-mono text-right"
              role="cell"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {trade.sl ? formatPrice(trade.sl) : "—"}
            </span>

            {/* Age */}
            <span
              className="font-mono text-right"
              role="cell"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {relTime(trade.open_time)}
            </span>

            {/* Close */}
            <div className="flex items-center justify-end" role="cell">
              <button
                className={cn(
                  "rounded transition-colors px-1.5 py-0.5 font-mono text-xs",
                  "border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                  closingId === trade.id
                    ? "border-[var(--border)] text-[var(--text-3)] cursor-not-allowed"
                    : "border-[var(--border)] text-[var(--text-3)] hover:border-[var(--negative)] hover:text-[var(--negative)]"
                )}
                onClick={() => handleClose(trade.id)}
                disabled={closingId === trade.id}
                aria-label={`Close ${trade.symbol} position`}
              >
                {closingId === trade.id ? "…" : "✕"}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
