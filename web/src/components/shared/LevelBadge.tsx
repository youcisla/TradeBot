"use client";

type Level = "info" | "warn" | "error" | "debug" | "INFO" | "WARN" | "ERROR" | "DEBUG";

interface LevelBadgeProps {
  level: Level | string;
}

const COLORS: Record<string, { bg: string; text: string }> = {
  info:  { bg: "rgba(0,229,255,0.12)",  text: "#00e5ff" },
  warn:  { bg: "rgba(255,159,10,0.12)", text: "#ff9f0a" },
  error: { bg: "rgba(255,69,58,0.12)",  text: "#ff453a" },
  debug: { bg: "rgba(244,244,245,0.08)", text: "#adaaaa" },
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
        borderRadius:    4,
        fontSize:       10,
        fontFamily:     "var(--font-mono)",
        fontWeight:     700,
        textTransform:  "uppercase",
        letterSpacing: "0.06em",
        backgroundColor: c.bg,
        color:          c.text,
      }}
    >
      {level}
    </span>
  );
}
