"use client";

import { type ColumnDef } from "@tanstack/react-table";
import { useAllTrades } from "@/lib/swr";
import { DirectionBadge, StrategyBadge } from "@/components/ui/Badges";
import { DataTable } from "@/components/ui/data-table";
import { useDataTable } from "@/hooks/use-data-table";
import { formatPrice, fmtPnl, fmtDateTime } from "@/lib/format";
import { useState } from "react";
import { cn } from "@/lib/utils";

type Trade = {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  close_time?: string;
  pnl?: number;
  status: string;
  strategy?: string;
  lots?: number;
};

function PnlCell({ value }: { value?: number }) {
  if (value == null) return <span style={{ color: "var(--text-3)" }}>—</span>;
  return (
    <span
      className="font-bold"
      style={{ color: value >= 0 ? "var(--positive)" : "var(--negative)" }}
    >
      {fmtPnl(value)}
    </span>
  );
}

export default function TradeHistory() {
  const { data: trades = [] } = useAllTrades(500);
  const [filter, setFilter] = useState<"all" | "closed" | "open">("all");

  const filtered = trades.filter((t) => {
    if (filter === "closed") return t.status === "CLOSED";
    if (filter === "open") return t.status === "OPEN" || t.status === "PARTIAL";
    return true;
  });

  const columns: ColumnDef<Trade>[] = [
    {
      id: "close_time",
      header: "Date",
      accessorKey: "close_time",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-2)" }}>
          {row.original.close_time ? fmtDateTime(row.original.close_time) : "—"}
        </span>
      ),
    },
    {
      id: "symbol",
      header: "Symbol",
      accessorKey: "symbol",
      cell: ({ row }) => (
        <span className="font-bold" style={{ color: "var(--text-1)" }}>
          {row.original.symbol}
        </span>
      ),
    },
    {
      id: "direction",
      header: "Dir",
      accessorKey: "direction",
      cell: ({ row }) => <DirectionBadge direction={row.original.direction} />,
    },
    {
      id: "strategy",
      header: "Strategy",
      accessorKey: "strategy",
      cell: ({ row }) =>
        row.original.strategy ? (
          <StrategyBadge strategy={row.original.strategy} />
        ) : (
          <span style={{ color: "var(--text-3)" }}>—</span>
        ),
    },
    {
      id: "entry_price",
      header: "Entry",
      accessorKey: "entry_price",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-2)" }}>
          {formatPrice(row.original.entry_price)}
        </span>
      ),
    },
    {
      id: "close_time",
      header: "Exit",
      accessorKey: "close_time",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-2)" }}>
          {row.original.close_time ? fmtDateTime(row.original.close_time) : "—"}
        </span>
      ),
    },
    {
      id: "pnl",
      header: "P&L",
      accessorKey: "pnl",
      cell: ({ row }) => <PnlCell value={row.original.pnl} />,
    },
  ];

  const { table, globalFilter, setGlobalFilter } = useDataTable({
    data: filtered,
    columns,
    pageSize: 30,
  });

  return (
    <div className="flex flex-col gap-3">
      {/* Header + filter row */}
      <div className="flex items-center justify-between">
        <span
          className="font-bold text-xs uppercase tracking-widest"
          style={{
            color: "var(--text-3)",
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            letterSpacing: "0.06em",
          }}
        >
          Trade History
        </span>
        <div className="flex items-center gap-2">
          {(["all", "closed", "open"] as const).map((f) => (
            <button
              key={f}
              className={cn(
                "rounded px-2 py-1 text-xs font-mono font-bold uppercase tracking-wider cursor-pointer transition-all",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                filter === f
                  ? "bg-[var(--bg-3)] border border-[var(--border-active)] text-[var(--accent)]"
                  : "bg-transparent border border-[var(--border)] text-[var(--text-3)]"
              )}
              style={{ letterSpacing: "0.05em" }}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <DataTable
        table={table}
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        filterPlaceholder="Search symbol, strategy…"
        noResults="No trades found"
      />
    </div>
  );
}
