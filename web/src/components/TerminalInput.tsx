"use client";
import { useState } from "react";

export default function TerminalInput({
  type = "text",
  value,
  onChange,
  placeholder,
  autoFocus,
  autoComplete,
  accent = "#00ff88",
}: {
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  autoComplete?: string;
  accent?: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      autoFocus={autoFocus}
      autoComplete={autoComplete}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{
        display: "block", width: "100%",
        background: "#06060c",
        border: `1px solid ${focused ? accent : "#1c1c28"}`,
        borderRadius: 4, padding: "9px 12px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11, color: "#c0ccd8", outline: "none",
        boxShadow: focused ? `0 0 0 2px ${accent}26` : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
        boxSizing: "border-box" as const,
      }}
    />
  );
}
