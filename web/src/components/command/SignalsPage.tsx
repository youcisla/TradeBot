"use client";

import { type ColumnDef } from "@tanstack/react-table";
import useSWR from "swr";
import { DirectionBadge } from "@/components/shared/DirectionBadge";
import { StrategyBadge } from "@/components/shared/StrategyBadge";
import { DataTable } from "@/components/ui/data-table";
import { Panel } from "@/components/ui/panel";
import { TableSkeleton } from "@/components/ui/skeleton";
import { useDataTable } from "@/hooks/use-data-table";
import { useState } from "react";

type Signal = {
  id: string;
  symbol: string;
  direction: string;
  strategy: string;
  confidence: number;
  created_at: string;
  entry_price: number;
  tp1: number;
  tp2: number;
  tp3: number;
  tp4: number;
  sl: number;
  bull_case?: string;
  bear_case?: string;
  structural_be?: number;
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const color =
    pct >= 75 ? "var(--positive)" :
    pct >= 50 ? "var(--warning)"  :
    "var(--negative)";

  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1.5 rounded-full overflow-hidden flex-1 min-w-[80px]"
        style={{ background: "var(--bg-3)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span
        className="font-mono font-bold tabular-nums"
        style={{ color, fontFamily: "var(--font-mono)", fontSize: 11, minWidth: 32 }}
      >
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function SignalsPage() {
  const { data: signals = [], isLoading } = useSWR<Signal[]>(
    "/api/signals?limit=100",
    fetcher,
    { refreshInterval: 10_000 }
  );

  const [filter, setFilter] = useState<"all" | "BUY" | "SELL" | "HOLD">("all");
  const [strategyFilter, setStrategyFilter] = useState<string>("all");

  const strategies = Array.from(
    new Set(signals.map((s) => s.strategy).filter(Boolean))
  ).sort();

  const filtered = signals.filter((s) => {
    if (filter !== "all" && s.direction !== filter) return false;
    if (strategyFilter !== "all" && s.strategy !== strategyFilter) return false;
    return true;
  });

  const columns: ColumnDef<Signal>[] = [
    {
      id: "direction",
      header: "",
      cell: ({ row }) => <DirectionBadge direction={row.original.direction as "BUY" | "SELL" | "HOLD"} />,
      size: 48,
    },
    {
      id: "symbol",
      header: "Symbol",
      accessorKey: "symbol",
      cell: ({ row }) => (
        <span
          className="font-bold"
          style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)", fontSize: 12 }}
        >
          {row.original.symbol}
        </span>
      ),
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
      id: "confidence",
      header: "Confidence",
      accessorKey: "confidence",
      cell: ({ row }) => <ConfidenceBar value={row.original.confidence} />,
    },
    {
      id: "entry_price",
      header: "Entry",
      accessorKey: "entry_price",
      cell: ({ row }) => (
        <span
          className="font-mono"
          style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          {row.original.entry_price.toFixed(5)}
        </span>
      ),
    },
    {
      id: "tp1",
      header: "TP1",
      accessorKey: "tp1",
      cell: ({ row }) => (
        <span
          className="font-mono"
          style={{ color: "var(--positive)", fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          {row.original.tp1.toFixed(5)}
        </span>
      ),
    },
    {
      id: "sl",
      header: "SL",
      accessorKey: "sl",
      cell: ({ row }) => (
        <span
          className="font-mono"
          style={{ color: "var(--negative)", fontFamily: "var(--font-mono)", fontSize: 11 }}
        >
          {row.original.sl.toFixed(5)}
        </span>
      ),
    },
    {
      id: "created_at",
      header: "Time",
      accessorKey: "created_at",
      cell: ({ row }) => {
        const ts = row.original.created_at;
        if (!ts) return <span style={{ color: "var(--text-3)" }}>—</span>;
        const d = new Date(ts);
        return (
          <span
            className="font-mono tabular-nums"
            style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
          >
            {d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })}
          </span>
        );
      },
    },
  ];

  const { table, globalFilter, setGlobalFilter } = useDataTable({
    data: filtered,
    columns,
    pageSize: 30,
  });

  return (
    <div className="flex flex-col gap-3">
      {/* Filter row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Direction filter */}
        <div className="flex items-center gap-1.5">
          {(["all", "BUY", "SELL", "HOLD"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="rounded px-2.5 py-1 text-xs font-mono font-bold uppercase tracking-wider cursor-pointer transition-all"
              style={{
                background: filter === f ? "var(--bg-4)" : "transparent",
                border: `1px solid ${filter === f ? "var(--border-active)" : "var(--border)"}`,
                color: filter === f ? "var(--accent)" : "var(--text-3)",
                letterSpacing: "0.05em",
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Strategy filter */}
        <div className="flex items-center gap-1.5">
          <span
            className="font-mono uppercase"
            style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.06em" }}
          >
            Strategy:
          </span>
          <button
            onClick={() => setStrategyFilter("all")}
            className="rounded px-2 py-0.5 text-xs font-mono font-bold transition-all"
            style={{
              background: strategyFilter === "all" ? "var(--bg-4)" : "transparent",
              border: `1px solid ${strategyFilter === "all" ? "var(--border-active)" : "var(--border)"}`,
              color: strategyFilter === "all" ? "var(--accent)" : "var(--text-3)",
            }}
          >
            All
          </button>
          {strategies.map((s) => (
            <button
              key={s}
              onClick={() => setStrategyFilter(s)}
              className="rounded px-2 py-0.5 text-xs font-mono font-bold transition-all"
              style={{
                background: strategyFilter === s ? "var(--bg-4)" : "transparent",
                border: `1px solid ${strategyFilter === s ? "var(--border-active)" : "var(--border)"}`,
                color: strategyFilter === s ? "var(--accent)" : "var(--text-3)",
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Count */}
        <span
          className="ml-auto font-mono"
          style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
        >
          {filtered.length} signal{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Signals table */}
      <Panel className="p-0">
        {isLoading ? (
          <TableSkeleton rows={8} />
        ) : filtered.length === 0 ? (
          <div
            className="flex items-center justify-center py-16"
            style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 11 }}
          >
            No signals found
          </div>
        ) : (
          <DataTable
            table={table}
            globalFilter={globalFilter}
            onGlobalFilterChange={setGlobalFilter}
            filterPlaceholder="Search symbol, strategy…"
            noResults="No signals match your filters"
          />
        )}
      </Panel>
    </div>
  );
}