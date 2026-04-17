"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { DirectionBadge } from "@/components/shared/DirectionBadge";
import { formatPrice, fmtPnl, relTime } from "@/lib/format";
import { sendCommand } from "@/lib/ws";

export default function PositionsCard() {
  const { openTrades } = useAppShell();
  const [closingId, setClosingId] = useState<number | null>(null);

  // Guard: SWR returns undefined before first fetch resolves
  const trades = Array.isArray(openTrades) ? openTrades : [];

  async function handleClose(id: number) {
    setClosingId(id);
    await sendCommand("close_trade", { trade_id: id });
    setClosingId(null);
  }

  return (
    <div className="flex flex-col" role="table" aria-label="Open positions">
      {/* Column headers */}
      <div
        className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2 border-b"
        style={{ background: "var(--bg-3)", borderColor: "var(--border)" }}
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
      {trades.length === 0 ? (
        <div
          className="flex items-center justify-center py-10 font-mono text-sm"
          style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          No open positions
        </div>
      ) : (
        trades.map((trade) => {
          const t = trade as { id: number; symbol: string; direction: string; entry_price: number; pnl?: number; sl?: number; strategy?: string; open_time: string };
          const isClosing = closingId === t.id;
          return (
            <div
              key={t.id}
              className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2.5 border-b transition-colors group"
              style={{ borderColor: "var(--border-subtle)" }}
              role="row"
            >
              {/* Symbol */}
              <div className="flex flex-col gap-0.5 min-w-0" role="cell">
                <span
                  className="font-mono font-bold"
                  style={{ color: "var(--text-1)", fontSize: 12 }}
                >
                  {t.symbol}
                </span>
                {t.strategy && (
                  <span
                    className="font-mono uppercase"
                    style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.04em" }}
                  >
                    {t.strategy}
                  </span>
                )}
              </div>

              {/* Direction */}
              <div role="cell">
                <DirectionBadge direction={t.direction} />
              </div>

              {/* Entry */}
              <span
                className="font-mono text-right"
                role="cell"
                style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 11 }}
              >
                {formatPrice(t.entry_price)}
              </span>

              {/* PnL */}
              <span
                className="font-mono text-right font-bold"
                role="cell"
                style={{
                  color: typeof t.pnl === "number" && t.pnl < 0
                    ? "var(--negative)"
                    : "var(--positive)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                }}
              >
                {fmtPnl(t.pnl)}
              </span>

              {/* SL */}
              <span
                className="font-mono text-right"
                role="cell"
                style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
              >
                {t.sl ? formatPrice(t.sl) : "—"}
              </span>

              {/* Age */}
              <span
                className="font-mono text-right"
                role="cell"
                style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
              >
                {relTime(t.open_time)}
              </span>

              {/* Close */}
              <div className="flex items-center justify-end" role="cell">
                <button
                  className="rounded transition-colors px-1.5 py-0.5 font-mono text-xs border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-3)",
                    cursor: isClosing ? "not-allowed" : "pointer",
                  }}
                  onClick={() => handleClose(t.id)}
                  disabled={isClosing}
                  aria-label={`Close ${t.symbol} position`}
                >
                  {isClosing ? "…" : "✕"}
                </button>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
