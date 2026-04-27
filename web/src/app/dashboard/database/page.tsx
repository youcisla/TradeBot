"use client";

import { useState } from "react";
import useSWR from "swr";
import { createColumnHelper } from "@tanstack/react-table";
import { columnHint, relTime, formatJSON, statusColor } from "@/lib/db-admin";
import type { CellContext } from "@tanstack/react-table";

const columnHelper = createColumnHelper<Record<string, unknown>>();

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// ── Main component ───────────────────────────────────────────────────────────

export default function DatabasePage() {
  const [selectedTable, setSelectedTable] = useState<string>("trades");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Load tables list
  const { data: tablesData } = useSWR("/api/database/tables", fetcher, { refreshInterval: 60000 });
  const tables: string[] = tablesData?.tables ?? [];

  // Load table rows + schema
  const { data: tableData, isLoading } = useSWR(
    selectedTable ? [selectedTable, page, pageSize, search, sortBy, sortDir] as const : null,
    ([table, p, ps, s, sb, sd]) => {
      const params = new URLSearchParams({
        table,
        page: String(p),
        pageSize: String(ps),
        search: s,
        sortBy: sb,
        sortDir: sd,
      });
      return fetch(`/api/database/${table}?${params}`).then((r) => r.json());
    },
    { refreshInterval: 15000 }
  );

  const rows = tableData?.rows ?? [];
  const total = tableData?.total ?? 0;
  const schema: { name: string; type: string; nullable: string }[] = tableData?.schema ?? [];
  const totalPages = Math.ceil(total / pageSize);

  // Build columns from schema
  const columns = schema.map((col) =>
    columnHelper.accessor(col.name, {
      id: col.name,
      header: col.name,
      enableSorting: true,
      cell: (info: CellContext<Record<string, unknown>, unknown>) => {
        const val = info.getValue() as unknown;
        const hint = columnHint(col.type, col.name);
        if (hint === "status") {
          return <span className={statusColor(String(val ?? ""))}>{String(val ?? "—")}</span>;
        }
        if (hint === "timestamp") {
          return val ? <span title={String(val)}>{relTime(String(val))}</span> : "—";
        }
        if (hint === "boolean") {
          return val ? "✓" : "✗";
        }
        if (hint === "number") {
          const n = Number(val);
          return isNaN(n) ? String(val ?? "—") : n.toLocaleString(undefined, { maximumFractionDigits: 4 });
        }
        if (hint === "json") {
          if (val == null) return "—";
          const summary = formatJSON(val);
          const truncated = summary.length > 120 ? summary.slice(0, 120) + "…" : summary;
          return (
            <details className="text-xs">
              <summary className="cursor-pointer font-mono text-neutral-400">{truncated}</summary>
              <pre className="mt-1 text-xs text-neutral-500 whitespace-pre-wrap break-all">{formatJSON(val)}</pre>
            </details>
          );
        }
        return val == null ? <span className="text-neutral-500 italic">NULL</span> : String(val);
      },
    })
  );

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Database Viewer</h2>
        <span className="text-xs text-neutral-500">
          {selectedTable} · {total.toLocaleString()} rows
        </span>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ── Left sidebar: table list ────────────────────────────────── */}
        <div className="w-52 shrink-0 flex flex-col gap-1">
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider px-2 pb-2">
            Tables ({tables.length})
          </div>
          {tables.map((t) => (
            <button
              key={t}
              onClick={() => { setSelectedTable(t); setPage(1); setSearch(""); setSortBy(""); }}
              className={`text-left px-3 py-2 rounded text-xs font-mono transition-colors ${
                t === selectedTable
                  ? "bg-[var(--token-sidebar-active-bg,rgba(255,255,255,0.08))] text-white"
                  : "text-neutral-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* ── Main content ───────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          {/* Controls */}
          <div className="flex gap-3 items-center flex-wrap">
            <input
              type="search"
              placeholder="Search across text columns…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              className="px-3 py-1.5 bg-white/5 border border-white/10 rounded text-sm text-white placeholder-neutral-500 w-56 focus:outline-none focus:border-white/20"
            />
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
              className="px-3 py-1.5 bg-white/5 border border-white/10 rounded text-sm text-white focus:outline-none focus:border-white/20"
            >
              {[25, 50, 100].map((s) => (
                <option key={s} value={s}>{s} / page</option>
              ))}
            </select>
            {sortBy && (
              <button
                onClick={() => { setSortBy(""); setPage(1); }}
                className="text-xs text-neutral-500 hover:text-white"
              >
                Clear sort ×
              </button>
            )}
          </div>

          {/* Table */}
          <div className="flex-1 overflow-auto rounded border border-white/5">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-[var(--token-bg-secondary,#0f0f14)]">
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col.id}
                      className="px-3 py-2 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider border-b border-white/5 cursor-pointer hover:text-white select-none"
                      onClick={() => {
                        if (sortBy === col.id) {
                          setSortDir(sortDir === "asc" ? "desc" : "asc");
                        } else {
                          setSortBy(col.id as string);
                          setSortDir("desc");
                        }
                        setPage(1);
                      }}
                    >
                      {String(col.header)}
                      {sortBy === col.id && (sortDir === "asc" ? " ↑" : " ↓")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-12 text-center text-neutral-500">
                      Loading…
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-3 py-12 text-center text-neutral-500">
                      No rows found{search ? ` for "${search}"` : ""}
                    </td>
                  </tr>
                ) : (
                  rows.map((row: Record<string, unknown>, i: number) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/3">
                      {columns.map((col) => {
                        const val = (row as Record<string, unknown>)[col.id as string];
                        return (
                          <td key={col.id} className="px-3 py-2 align-top">
                            {col.cell && (col.cell as (props: { getValue: () => unknown }) => React.ReactNode)({ getValue: () => val })}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex gap-2 items-center justify-center pb-4">
              <button onClick={() => setPage(1)} disabled={page === 1}
                className="px-2 py-1 rounded text-xs bg-white/5 disabled:opacity-30 hover:bg-white/10 disabled:cursor-not-allowed">
                «
              </button>
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                className="px-2 py-1 rounded text-xs bg-white/5 disabled:opacity-30 hover:bg-white/10 disabled:cursor-not-allowed">
                ‹
              </button>
              <span className="text-xs text-neutral-400 px-3">
                {page} / {totalPages}
              </span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                className="px-2 py-1 rounded text-xs bg-white/5 disabled:opacity-30 hover:bg-white/10 disabled:cursor-not-allowed">
                ›
              </button>
              <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                className="px-2 py-1 rounded text-xs bg-white/5 disabled:opacity-30 hover:bg-white/10 disabled:cursor-not-allowed">
                »
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}