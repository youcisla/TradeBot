/**
 * Handoff helpers — mirrors the UI helpers from ui-shell.jsx
 * confTier, dirChip, verdictHue, stateHue
 */

/** Confidence tier for conf-bar class: t-low | t-mid | t-high | t-vh */
export function confTier(c: number): "t-low" | "t-mid" | "t-high" | "t-vh" {
  if (c >= 85) return "t-vh";
  if (c >= 65) return "t-high";
  if (c >= 45) return "t-mid";
  return "t-low";
}

/** Direction to chip tone */
export function dirChip(d: string): "pos" | "neg" {
  return d === "BUY" || d === "LONG" ? "pos" : "neg";
}

/** Verdict to chip tone */
export function verdictHue(v: string): "pos" | "neg" | "warn" | "info" | "" {
  const map: Record<string, "pos" | "neg" | "warn" | "info" | ""> = {
    EXECUTED: "pos",
    APPROVED: "pos",
    PENDING: "warn",
    QUEUED: "info",
    BLOCKED: "neg",
    REJECTED: "neg",
    DROPPED: "",
  };
  return map[v] ?? "";
}

/** Agent state to chip tone */
export function stateHue(s: string): "pos" | "neg" | "warn" | "info" | "" {
  const map: Record<string, "pos" | "neg" | "warn" | "info" | ""> = {
    RUNNING: "pos",
    IDLE: "info",
    STALE: "warn",
    ERROR: "neg",
  };
  return map[s] ?? "";
}
