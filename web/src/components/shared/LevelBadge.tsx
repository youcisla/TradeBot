"use client";

type Level = "info" | "warn" | "error" | "debug" | "INFO" | "WARN" | "ERROR" | "DEBUG";

interface LevelBadgeProps {
  level: Level | string;
}

const COLORS: Record<string, { bg: string; text: string }> = {
  info:  { bg: "var(--cyan-dim)",    text: "var(--cyan)"    },
  warn:  { bg: "var(--warning-dim)", text: "var(--warning)" },
  error: { bg: "var(--negative-dim)", text: "var(--negative)" },
  debug: { bg: "rgba(244,244,245,0.08)", text: "var(--text-3)" },
};

export function LevelBadge({ level }: LevelBadgeProps) {
  const key = level.toLowerCase();
  const c = COLORS[key] ?? COLORS.info;

  return (
    <span
      style={{
        display:        "inline-flex",
        alignItems:     "center",
        padding:        "2px 7px",
        borderRadius:    "var(--radius-md)",
        fontSize:       10,
        fontFamily:     "var(--font-mono)",
        fontWeight:     700,
        textTransform:  "uppercase",
        letterSpacing: "0.08em",
        backgroundColor: c.bg,
        color:          c.text,
      }}
    >
      {level}
    </span>
  );
}
