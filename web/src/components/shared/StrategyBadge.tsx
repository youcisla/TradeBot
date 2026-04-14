"use client";

interface StrategyBadgeProps {
  strategy: string;
}

/**
 * Coloured badge per strategy type.
 * Auto-detects ICT, DeepSeek, Ensemble, SMA from the strategy name.
 */
export function StrategyBadge({ strategy }: StrategyBadgeProps) {
  const s = strategy.toLowerCase();

  let bg   = "var(--bg-5)";
  let text = "var(--text-3)";

  if (s.includes("ict"))          { bg = "var(--cyan-dim)";  text = "var(--cyan)"; }
  else if (s.includes("deepseek")) { bg = "rgba(191,90,242,0.15)"; text = "var(--purple)"; }
  else if (s.includes("ensemble")) { bg = "var(--warning-dim)"; text = "var(--warning)"; }
  else if (s.includes("sma"))      { bg = "var(--bg-5)"; text = "var(--text-3)"; }
  else if (s.includes("lstm") || s.includes("neural")) { bg = "rgba(191,90,242,0.15)"; text = "var(--purple)"; }

  return (
    <span
      style={{
        display:        "inline-flex",
        alignItems:     "center",
        padding:        "2px 8px",
        borderRadius:   "var(--radius-pill)",
        fontSize:       10,
        fontFamily:     "var(--font-mono)",
        fontWeight:     700,
        textTransform:  "uppercase",
        letterSpacing: "0.08em",
        backgroundColor: bg,
        color:          text,
        border:         "1px solid var(--border-subtle)",
      }}
    >
      {strategy}
    </span>
  );
}
