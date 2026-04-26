// ── Table list ──────────────────────────────────────────────────────────────

export async function listTables(): Promise<string[]> {
  const res = await fetch("/api/database/tables");
  const data = await res.json();
  return data.tables ?? [];
}

// ── Schema + rows ────────────────────────────────────────────────────────────

export interface ColumnDef {
  name: string;
  type: string;
  nullable: boolean;
}

export interface TableResult {
  rows: Record<string, unknown>[];
  total: number;
  page: number;
  pageSize: number;
  schema: ColumnDef[];
}

export async function getTableRows(
  table: string,
  page: number,
  pageSize: number,
  search: string,
  sortBy: string,
  sortDir: "asc" | "desc"
): Promise<TableResult> {
  const params = new URLSearchParams({
    table,
    page: String(page),
    pageSize: String(pageSize),
    search,
    sortBy,
    sortDir,
  });
  const res = await fetch(`/api/database/${table}?${params}`);
  return res.json();
}

// ── Status colouring ─────────────────────────────────────────────────────────

export function statusColor(status: string): string {
  switch ((status ?? "").toUpperCase()) {
    case "OPEN":     return "text-green-400";
    case "CLOSED":   return "text-red-400";
    case "PARTIAL":  return "text-yellow-400";
    case "PENDING":  return "text-blue-400";
    case "RUNNING":  return "text-purple-400";
    case "DONE":     return "text-green-500";
    case "FAILED":   return "text-red-500";
    default:         return "text-neutral-400";
  }
}

export function relTime(ts: string): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function formatJSON(val: unknown): string {
  if (typeof val !== "object" || val === null) return String(val ?? "");
  try { return JSON.stringify(val); } catch { return String(val); }
}

// ── Column type → cell renderer hint ────────────────────────────────────────

export type CellHint = "text" | "number" | "boolean" | "json" | "timestamp" | "status";

export function columnHint(type: string, name: string): CellHint {
  const n = name.toLowerCase();
  if (n === "status") return "status";
  if (n.endsWith("_at") || n === "open_time" || n === "close_time" || n === "created_at") return "timestamp";
  if (type === "jsonb" || n === "payload" || n === "data" || n === "confluences" || n === "guard_status") return "json";
  if (type === "boolean") return "boolean";
  if (type === "numeric" || type === "integer" || type === "real" || type === "bigint") return "number";
  return "text";
}