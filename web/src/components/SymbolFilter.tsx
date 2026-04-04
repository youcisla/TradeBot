"use client";

import { useMemo, useState } from "react";

interface SymbolFilterProps {
  symbols: string[];
  selected: string | null;
  onSelect: (s: string | null) => void;
}

export default function SymbolFilter({ symbols, selected, onSelect }: SymbolFilterProps) {
  const [search, setSearch] = useState("");

  const visibleSymbols = useMemo(() => {
    const q = search.trim().toUpperCase();
    if (!q) return symbols;
    return symbols.filter((symbol) => symbol.toUpperCase().includes(q));
  }, [symbols, search]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter symbols..."
        style={{
          height: 34,
          borderRadius: 10,
          border: "1px solid rgba(84,84,88,0.65)",
          background: "rgba(118,118,128,0.2)",
          color: "#FFFFFF",
          padding: "0 12px",
          fontSize: 13,
          fontWeight: 500,
          fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
          outline: "none",
        }}
      />

      <div
        style={{
          display: "flex",
          flexDirection: "row",
          gap: 8,
          overflowX: "auto",
          paddingBottom: 4,
          scrollbarWidth: "none",
        }}
      >
        {/* All pill */}
        <button
          onClick={() => onSelect(null)}
          style={{
            height: 32,
            padding: "0 14px",
            borderRadius: 10,
            border: "none",
            fontSize: 13,
            fontWeight: 600,
            fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
            cursor: "pointer",
            whiteSpace: "nowrap",
            flexShrink: 0,
            background: selected === null ? "#0A84FF" : "rgba(118,118,128,0.24)",
            color: selected === null ? "#FFFFFF" : "rgba(235,235,245,0.6)",
            transition: "background 0.15s, color 0.15s",
          }}
        >
          All
        </button>

        {visibleSymbols.map((s) => {
          const active = selected === s;
          return (
            <button
              key={s}
              onClick={() => onSelect(active ? null : s)}
              style={{
                height: 32,
                padding: "0 14px",
                borderRadius: 10,
                border: "none",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
                cursor: "pointer",
                whiteSpace: "nowrap",
                flexShrink: 0,
                background: active ? "#0A84FF" : "rgba(118,118,128,0.24)",
                color: active ? "#FFFFFF" : "rgba(235,235,245,0.6)",
                transition: "background 0.15s, color 0.15s",
              }}
            >
              {s}
            </button>
          );
        })}
      </div>
    </div>
  );
}
