// Helper to format price fields (SL/TP) robustly for display
// Accepts string | number | null | undefined
// Returns "—" for null/undefined/zero (if hideZero is true)
// Otherwise returns value as fixed decimal string

export function formatPrice(
  value: string | number | null | undefined,
  digits: number = 5,
  hideZero: boolean = true
): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (isNaN(num)) return "—";
  if (hideZero && Math.abs(num) < 1e-10) return "—";
  return num.toFixed(digits);
}
