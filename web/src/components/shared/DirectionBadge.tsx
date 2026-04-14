"use client";

interface DirectionBadgeProps {
  direction: string;
  /** Show as compact pill (default: rounded square) */
  pill?: boolean;
}

/**
 * BUY (green) / SELL (red) / HOLD (amber) direction badge.
 * Always uses CSS token colors — never raw hex.
 */
export function DirectionBadge({ direction, pill = false }: DirectionBadgeProps) {
  const d = direction.toUpperCase();
  const isBuy  = d === "BUY"  || d === "LONG";
  const isSell = d === "SELL" || d === "SHORT";
  const isHold = d === "HOLD";

  const bg  = isBuy ? "var(--positive-dim)"  : isSell ? "var(--negative-dim)" : "var(--warning-dim)";
  const text = isBuy ? "var(--positive)"      : isSell ? "var(--negative)"      : "var(--warning)";

  return (
    <span
      style={{
        display:        "inline-flex",
        alignItems:     "center",
        padding:        "2px 8px",
        borderRadius:    pill ? "var(--radius-pill)" : "var(--radius-md)",
        fontSize:       10,
        fontFamily:     "var(--font-mono)",
        fontWeight:     700,
        textTransform:  "uppercase",
        letterSpacing: "0.06em",
        backgroundColor: bg,
        color:          text,
        border:         `1px solid ${text}30`,
      }}
    >
      {direction}
    </span>
  );
}
