"use client";

import { type ColumnDef } from "@tanstack/react-table";
import { useRisk } from "@/lib/swr";
import { DataTable } from "@/components/ui/data-table";
import { useDataTable } from "@/hooks/use-data-table";

type Guard = {
  name: string;
  status: "pass" | "warn" | "fail";
  threshold: string;
  current: string;
  lastCheck?: string;
};

const STATUS_COLOR: Record<string, string> = {
  pass: "var(--green)",
  warn: "var(--orange)",
  fail: "var(--red)",
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? "var(--text-3)";
  return (
    <span
      className="rounded-full flex-shrink-0"
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        background: color,
        boxShadow: `0 0 6px ${color}`,
      }}
    />
  );
}

export default function GuardTable() {
  const { data: risk } = useRisk();
  const guards: Guard[] = (risk?.guards ?? []) as Guard[];

  const columns: ColumnDef<Guard>[] = [
    {
      id: "status",
      header: "",
      cell: ({ row }) => <StatusDot status={row.original.status} />,
      size: 24,
    },
    {
      id: "name",
      header: "Guard",
      accessorKey: "name",
      cell: ({ row }) => (
        <span className="font-semibold" style={{ color: "var(--text-1)" }}>
          {row.original.name}
        </span>
      ),
    },
    {
      id: "current",
      header: "Current",
      accessorKey: "current",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-2)" }}>{row.original.current}</span>
      ),
    },
    {
      id: "threshold",
      header: "Threshold",
      accessorKey: "threshold",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-3)" }}>/ {row.original.threshold}</span>
      ),
    },
    {
      id: "status_label",
      header: "Status",
      cell: ({ row }) => {
        const s = row.original.status;
        const color = STATUS_COLOR[s] ?? "var(--text-3)";
        return (
          <span
            className="font-bold uppercase"
            style={{
              color,
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              letterSpacing: "0.06em",
            }}
          >
            {s}
          </span>
        );
      },
    },
  ];

  const { table, globalFilter, setGlobalFilter } = useDataTable({
    data: guards,
    columns,
    pageSize: 50,
  });

  return (
    <div className="flex flex-col gap-3">
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
          Guard Pipeline
        </span>
        <span
          className="font-mono"
          style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
        >
          {guards.length} guards
        </span>
      </div>
      <DataTable
        table={table}
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        filterPlaceholder="Filter guards…"
        noResults="No guards"
      />
    </div>
  );
}
