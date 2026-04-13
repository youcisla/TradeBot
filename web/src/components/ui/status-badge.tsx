"use client";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "muted";

interface StatusBadgeProps {
  label: string;
  variant?: BadgeVariant;
  pulse?: boolean;
  size?: "sm" | "md";
}

const VARIANT_STYLES: Record<BadgeVariant, { bg: string; text: string; border: string; dot: string }> = {
  default:  { bg: "var(--bg-3)",       text: "var(--text-2)",  border: "var(--border)",        dot: "var(--text-3)"  },
  success:  { bg: "var(--green-dim)", text: "var(--green)",   border: "rgba(48,209,88,0.25)",  dot: "var(--green)"   },
  warning:  { bg: "var(--orange)",     text: "#000",           border: "rgba(255,159,10,0.35)", dot: "#000"            },
  danger:   { bg: "var(--red-dim)",    text: "var(--red)",     border: "rgba(255,69,58,0.25)",   dot: "var(--red)"     },
  info:     { bg: "var(--cyan-dim)",   text: "var(--cyan)",    border: "rgba(100,210,255,0.25)",dot: "var(--cyan)"    },
  muted:    { bg: "transparent",       text: "var(--text-3)",  border: "transparent",             dot: "var(--text-3)"  },
};

export function StatusBadge({ label, variant = "default", pulse = false, size = "sm" }: StatusBadgeProps) {
  const s = VARIANT_STYLES[variant];
  const isSmall = size === "sm";

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full font-mono font-semibold uppercase tracking-widest"
      style={{
        background: s.bg,
        color: s.text,
        border: `1px solid ${s.border}`,
        padding: isSmall ? "2px 8px" : "4px 12px",
        fontSize: isSmall ? 8 : 10,
        letterSpacing: "0.08em",
      }}
    >
      {pulse ? (
        <span
          className="rounded-full flex-shrink-0"
          style={{
            width: isSmall ? 5 : 7,
            height: isSmall ? 5 : 7,
            background: s.dot,
            boxShadow: `0 0 4px ${s.dot}`,
            animation: "pulse-dot 1.8s ease-in-out infinite",
          }}
        />
      ) : (
        <span
          className="rounded-full flex-shrink-0"
          style={{
            width: isSmall ? 5 : 7,
            height: isSmall ? 5 : 7,
            background: s.dot,
          }}
        />
      )}
      {label}
    </span>
  );
}
