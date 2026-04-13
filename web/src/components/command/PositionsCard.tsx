"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { DirectionBadge } from "@/components/shared/DirectionBadge";
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
    <div className="flex flex-col">
      {/* Column headers */}
      <div
        className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2 border-b"
        style={{ background: "var(--bg-3)", borderColor: "var(--border)" }}
      >
        {["Symbol", "Dir", "Entry", "PnL", "SL", "Age", ""].map((h) => (
          <span
            key={h}
            className="font-mono text-xs font-bold uppercase tracking-widest"
            style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.06em" }}
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
            className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2.5 border-b transition-colors group"
            style={{ borderColor: "var(--border-subtle)" }}
            onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--bg-3)")}
            onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
          >
            {/* Symbol */}
            <div className="flex flex-col gap-0.5 min-w-0">
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
            <DirectionBadge direction={trade.direction} />

            {/* Entry */}
            <span
              className="font-mono text-right"
              style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {formatPrice(trade.entry_price)}
            </span>

            {/* PnL */}
            <span
              className="font-mono text-right font-bold"
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
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {trade.sl ? formatPrice(trade.sl) : "—"}
            </span>

            {/* Age */}
            <span
              className="font-mono text-right"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {relTime(trade.open_time)}
            </span>

            {/* Close */}
            <div className="flex items-center justify-end">
              <button
                className="rounded transition-colors px-1.5 py-0.5 font-mono text-xs"
                style={{
                  background: "transparent",
                  border: "1px solid var(--border)",
                  color: "var(--text-3)",
                  fontSize: 10,
                }}
                onClick={() => handleClose(trade.id)}
                disabled={closingId === trade.id}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--negative)";
                  (e.currentTarget as HTMLElement).style.color = "var(--negative)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-3)";
                }}
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