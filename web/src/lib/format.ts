// Centralised formatters — replaces scattered fmtPrice.ts, time.ts helpers

// ── Price ─────────────────────────────────────────────────────────────────────

export function formatPrice(
  value: string | number | null | undefined,
  digits = 5,
  hideZero = true,
): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return "—";
  if (hideZero && Math.abs(num) < 1e-10) return "—";
  return num.toFixed(digits);
}

// ── USD ──────────────────────────────────────────────────────────────────────

export function fmtUsd(value: number | string | null | undefined, showSign = true): string {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (isNaN(num)) return "—";
  const abs = Math.abs(num);
  const formatted = "$" + abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  if (!showSign) return formatted;
  return num >= 0 ? "+" + formatted : "-" + formatted.replace("$", "$");
}

export function fmtPnl(value: number | string | null | undefined): string {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (isNaN(num)) return "—";
  return fmtUsd(num, true);
}

// ── Percent ───────────────────────────────────────────────────────────────────

export function fmtPct(value: number | string | null | undefined, decimals = 1): string {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (isNaN(num)) return "—";
  return num.toFixed(decimals) + "%";
}

// ── Time ──────────────────────────────────────────────────────────────────────

export function relTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return Math.floor(ms / 1_000)     + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)  + "m ago";
  return                       Math.floor(ms / 3_600_000) + "h ago";
}

export function fmtDateTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Europe/Paris",
  });
}

export function fmtDuration(ms: number): string {
  const s = Math.floor(ms / 1_000);
  if (s < 60)    return s + "s";
  const m = Math.floor(s / 60);
  if (m < 60)    return m + "m " + (s % 60) + "s";
  const h = Math.floor(m / 60);
  return h + "h " + (m % 60) + "m";
}

// ── Numbers ───────────────────────────────────────────────────────────────────

export function fmtNumber(value: number | string | null | undefined, decimals = 2): string {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (isNaN(num)) return "—";
  return num.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
