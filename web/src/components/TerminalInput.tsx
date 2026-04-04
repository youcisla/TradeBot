"use client";

import { useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Props {
  value:        string;
  onChange:     (v: string) => void;
  placeholder?: string;
  onSubmit?:    () => void;
  type?:        string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TerminalInput({
  value,
  onChange,
  placeholder,
  onSubmit,
  type = "text",
}: Props) {
  const [focused, setFocused] = useState(false);

  return (
    <input
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && onSubmit) onSubmit();
      }}
      style={{
        display:          "block",
        width:            "100%",
        height:           44,
        padding:          "0 14px",
        background:       focused
          ? "rgba(118,118,128,0.24)"
          : "rgba(116,116,128,0.18)",
        border:           "none",
        borderRadius:     10,
        outline:          "none",
        boxShadow:        focused
          ? "0 0 0 3px rgba(10,132,255,0.3)"
          : "none",
        fontSize:         17,
        color:            "#FFFFFF",
        fontFamily:       '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
        caretColor:       "#0A84FF",
        transition:       "box-shadow 0.2s, background 0.15s",
        boxSizing:        "border-box" as const,
        WebkitAppearance: "none" as const,
      }}
    />
  );
}
