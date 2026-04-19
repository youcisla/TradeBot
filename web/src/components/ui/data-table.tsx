"use client";

import {
  type ColumnDef,
  flexRender,
} from "@tanstack/react-table";
import type { Table } from "@tanstack/react-table";

interface DataTableProps<T> {
  table: Table<T>;
  globalFilter?: string;
  onGlobalFilterChange?: (value: string) => void;
  filterPlaceholder?: string;
  noResults?: string;
}

export function DataTable<T>({
  table,
  globalFilter,
  onGlobalFilterChange,
  filterPlaceholder = "Filter…",
  noResults = "No results",
}: DataTableProps<T>) {
  const page = table.getState().pagination;
  const pageCount = table.getPageCount();
  const rowCount = table.getFilteredRowModel().rows.length;

  return (
    <div className="flex flex-col gap-0 rounded overflow-hidden" style={{ border: "1px solid var(--border)" }}>

      {/* ── Search bar ── */}
      {onGlobalFilterChange && (
        <div
          className="flex items-center gap-2 px-4 py-2 border-b"
          style={{ background: "var(--bg-3)", borderColor: "var(--border)" }}
        >
          <span
            className="material-symbols-outlined text-base flex-shrink-0"
            style={{ color: "var(--text-3)", fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 16" }}
          >
            search
          </span>
          <input
            className="flex-1 bg-transparent text-sm outline-none"
            style={{
              color: "var(--text-1)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
            }}
            placeholder={filterPlaceholder}
            value={globalFilter ?? ""}
            onChange={(e) => onGlobalFilterChange(e.target.value)}
          />
          {globalFilter && (
            <button
              className="text-xs rounded px-1.5 py-0.5 cursor-pointer"
              style={{
                background: "var(--bg-4)",
                color: "var(--text-3)",
                fontFamily: "var(--font-mono)",
                border: "1px solid var(--border)",
              }}
              onClick={() => onGlobalFilterChange("")}
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* ── Table ── */}
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} style={{ background: "var(--bg-3)", borderBottom: "1px solid var(--border)" }}>
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      className="px-4 py-2.5"
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 9,
                        fontWeight: 700,
                        color: "var(--text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                        cursor: canSort ? "pointer" : "default",
                        userSelect: "none",
                      }}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && (
                          <span
                            className="material-symbols-outlined text-xs flex-shrink-0"
                            style={{
                              fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 12",
                              color: sorted ? "var(--accent)" : "var(--text-3)",
                            }}
                          >
                            {sorted === "asc"
                              ? "arrow_upward"
                              : sorted === "desc"
                              ? "arrow_downward"
                              : "unfold_more"}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={table.getHeaderGroups()[0]?.headers.length ?? 1}
                  className="px-4 py-12 text-center"
                >
                  <span
                    className="font-mono text-sm"
                    style={{ color: "var(--text-3)" }}
                  >
                    {noResults}
                  </span>
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b transition-colors hover:bg-[var(--bg-3)]"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--bg-2)",
                  }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-4 py-2.5"
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        color: "var(--text-1)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ── */}
      {pageCount > 1 && (
        <div
          className="flex items-center justify-between px-4 py-2.5 border-t"
          style={{
            background: "var(--bg-3)",
            borderColor: "var(--border)",
          }}
        >
          <span
            className="font-mono text-xs"
            style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
          >
            {page.pageIndex * page.pageSize + 1}–
            {Math.min((page.pageIndex + 1) * page.pageSize, rowCount)}{" "}
            of {rowCount}
          </span>

          <div className="flex items-center gap-1">
            <PageBtn
              onClick={() => table.firstPage()}
              disabled={!table.getCanPreviousPage()}
              icon="first_page"
            />
            <PageBtn
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              icon="chevron_left"
            />
            <span
              className="font-mono px-2"
              style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            >
              {page.pageIndex + 1} / {pageCount}
            </span>
            <PageBtn
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              icon="chevron_right"
            />
            <PageBtn
              onClick={() => table.lastPage()}
              disabled={!table.getCanNextPage()}
              icon="last_page"
            />
          </div>
        </div>
      )}
    </div>
  );
}

function PageBtn({
  onClick,
  disabled,
  icon,
}: {
  onClick: () => void;
  disabled: boolean;
  icon: string;
}) {
  return (
    <button
      className="flex items-center justify-center rounded cursor-pointer p-1"
      style={{
        background: disabled ? "transparent" : "var(--bg-4)",
        border: "1px solid var(--border)",
        color: disabled ? "var(--text-3)" : "var(--text-1)",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.4 : 1,
      }}
      onClick={onClick}
      disabled={disabled}
    >
      <span
        className="material-symbols-outlined text-sm"
        style={{
          fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16",
          opacity: disabled ? 0.4 : 1,
        }}
      >
        {icon}
      </span>
    </button>
  );
}
