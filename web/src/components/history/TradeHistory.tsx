"use client";

import { useState } from "react";
import { useAllTrades } from "@/lib/swr";
import { DirectionBadge, StrategyBadge } from "@/components/ui/Badges";
import { formatPrice, fmtPnl, fmtDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

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
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden flex flex-col">
      {/* Header + filter */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] flex-shrink-0">
        <span
          className="text-[11px] font-bold uppercase"
          style={{ fontFamily: "var(--font-ui)", color: "var(--text-2)", letterSpacing: "0.08em" }}
        >
          Trade History
        </span>
        <div className="flex gap-1">
          {(["all", "closed", "open"] as const).map((f) => (
            <button
              key={f}
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider cursor-pointer transition-all border",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                filter === f
                  ? "bg-[var(--bg-3)] border-[var(--border-active)] text-[var(--text-1)]"
                  : "border-[var(--border)] text-[var(--text-3)]"
              )}
              onClick={() => { setFilter(f); setPage(0); }}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-y-auto flex-1">
        <div
          className="grid gap-2 px-4 py-1"
          style={{ gridTemplateColumns: "120px 80px 64px 80px 80px 80px 80px", background: "var(--bg-3)", borderBottom: "1px solid var(--border)" }}
        >
          {["Date", "Symbol", "Dir", "Strategy", "Entry", "Exit", "P&L"].map((h) => (
            <span key={h} className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
              {h}
            </span>
          ))}
        </div>

        {paginated.length === 0 ? (
          <p className="font-mono text-sm text-center py-5 m-0" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
            No trades
          </p>
        ) : (
          paginated.map((trade) => (
            <div
              key={trade.id}
              className="grid gap-2 px-4 py-1.5 border-b border-[var(--border)] items-center"
              style={{ gridTemplateColumns: "120px 80px 64px 80px 80px 80px 80px" }}
            >
              <span className="font-mono text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
                {trade.close_time ? fmtDateTime(trade.close_time) : "—"}
              </span>
              <span className="font-mono text-xs font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
                {trade.symbol}
              </span>
              <span className="font-mono text-xs">
                <DirectionBadge direction={trade.direction} />
              </span>
              <span className="font-mono text-xs">
                {trade.strategy && <StrategyBadge strategy={trade.strategy} />}
              </span>
              <span className="font-mono text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
                {formatPrice(trade.entry_price)}
              </span>
              <span className="font-mono text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
                {trade.close_time ? fmtDateTime(trade.close_time) : "—"}
              </span>
              <span
                className="font-mono text-xs font-bold text-right"
                style={{ fontFamily: "var(--font-mono)", color: typeof trade.pnl === "number" && trade.pnl < 0 ? "var(--red)" : "var(--green)" }}
              >
                {fmtPnl(trade.pnl)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 px-4 py-3 border-t border-[var(--border)] flex-shrink-0">
          <button
            className="rounded px-2 py-1 font-mono text-sm cursor-pointer transition-all bg-[var(--bg-3)] border border-[var(--border)] text-[var(--text-1)] hover:border-[var(--text-3)] disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ fontFamily: "var(--font-mono)" }}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            ←
          </button>
          <span className="font-mono text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
            {page + 1} / {totalPages}
          </span>
          <button
            className="rounded px-2 py-1 font-mono text-sm cursor-pointer transition-all bg-[var(--bg-3)] border border-[var(--border)] text-[var(--text-1)] hover:border-[var(--text-3)] disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ fontFamily: "var(--font-mono)" }}
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
