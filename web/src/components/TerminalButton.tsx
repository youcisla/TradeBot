"use client";
import { useState } from "react";

type ButtonVariant = "primary" | "danger" | "warning" | "ghost";

const VARIANT_COLORS: Record<ButtonVariant, { base: string; r: number; g: number; b: number }> = {
  primary: { base: "#00ff88", r: 0,   g: 255, b: 136 },
  danger:  { base: "#ff4455", r: 255, g: 68,  b: 85  },
  warning: { base: "#f5c518", r: 245, g: 197, b: 24  },
  ghost:   { base: "#607888", r: 96,  g: 120, b: 136 },
};

export default function TerminalButton({
  children,
  onClick,
  variant = "primary",
  disabled = false,
  size = "md",
  fullWidth = false,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const { base, r, g, b } = VARIANT_COLORS[variant];
  const alpha = disabled ? 0.04 : hovered ? 0.15 : 0.08;
  const borderAlpha = disabled ? 0.15 : hovered ? 0.5 : 0.3;
  const textColor = disabled ? `rgba(${r},${g},${b},0.35)` : base;
  const padding = size === "sm" ? "5px 12px" : size === "lg" ? "12px 28px" : "9px 20px";
  const fontSize = size === "sm" ? 9 : size === "lg" ? 11 : 11;

  return (
    <button
      onClick={disabled ? undefined : onClick}
      onMouseEnter={() => !disabled && setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding,
        background: `rgba(${r},${g},${b},${alpha})`,
        border: `1px solid rgba(${r},${g},${b},${borderAlpha})`,
        borderRadius: 5,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize, fontWeight: 700, letterSpacing: "0.08em",
        textTransform: "uppercase" as const,
        color: textColor,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.15s, border-color 0.15s",
        width: fullWidth ? "100%" : undefined,
      }}
    >
      {children}
    </button>
  );
}
