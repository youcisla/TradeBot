"use client";

import { useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type Variant = "primary" | "secondary" | "danger";
type Size    = "sm" | "md";

interface Props {
  children:  React.ReactNode;
  onClick?:  () => void;
  variant?:  Variant;
  size?:     Size;
  icon?:     string;
  disabled?: boolean;
}

// ── Variant styles ────────────────────────────────────────────────────────────

const VARIANTS: Record<Variant, { bg: string; color: string; border: string }> = {
  primary: {
    bg:     "#0A84FF",
    color:  "#FFFFFF",
    border: "transparent",
  },
  secondary: {
    bg:     "rgba(118,118,128,0.24)",
    color:  "#0A84FF",
    border: "transparent",
  },
  danger: {
    bg:     "rgba(255,69,58,0.15)",
    color:  "#FF453A",
    border: "transparent",
  },
};

// ── Size styles ───────────────────────────────────────────────────────────────

const SIZES: Record<Size, { height: number; fontSize: number; padding: string }> = {
  sm: { height: 34, fontSize: 15, padding: "0 14px" },
  md: { height: 44, fontSize: 17, padding: "0 20px" },
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function TerminalButton({
  children,
  onClick,
  variant  = "primary",
  size     = "md",
  icon,
  disabled = false,
}: Props) {
  const [active, setActive] = useState(false);

  const { bg, color, border } = VARIANTS[variant];
  const { height, fontSize, padding } = SIZES[size];

  const baseStyle: React.CSSProperties = {
    display:        "inline-flex",
    alignItems:     "center",
    justifyContent: "center",
    gap:            6,
    height,
    padding,
    background:     disabled ? "rgba(118,118,128,0.12)" : bg,
    color:          disabled ? "rgba(235,235,245,0.25)" : color,
    border:         `0.5px solid ${border}`,
    borderRadius:   10,
    fontSize,
    fontWeight:     600,
    fontFamily:     '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
    cursor:         disabled ? "not-allowed" : "pointer",
    outline:        "none",
    transform:      active && !disabled ? "scale(0.97)" : "scale(1)",
    opacity:        active && !disabled ? 0.75 : 1,
    transition:     "transform 0.1s, opacity 0.1s",
    userSelect:     "none" as const,
    WebkitUserSelect: "none" as const,
    boxSizing:      "border-box" as const,
  };

  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      onMouseLeave={() => setActive(false)}
      style={baseStyle}
    >
      {icon && (
        <span
          className="material-symbols-outlined"
          style={{ fontSize: size === "sm" ? 16 : 20, lineHeight: 1 }}
        >
          {icon}
        </span>
      )}
      {children}
    </button>
  );
}
