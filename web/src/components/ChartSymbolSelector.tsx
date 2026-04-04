"use client";

import { useState } from "react";

const SYMBOL_GROUPS: Record<string, string[]> = {
  "Forex Majors": ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"],
  "Crosses": [
    "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURAUD", "EURCAD",
    "GBPCHF", "GBPAUD", "CADJPY", "CHFJPY", "EURCHF", "NZDJPY",
  ],
  "Metals": ["XAUUSD", "XAGUSD"],
  "Energy": ["USOUSD", "UKOUSD"],
  "Crypto": ["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD"],
  "Exotics": ["USDZAR", "USDTRY"],
};

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

interface Props {
  value: string;
  onChange: (symbol: string) => void;
}

function SymBtn({ sym, active, onClick }: { sym: string; active: boolean; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        ...SF,
        padding: "6px 4px",
        fontSize: 11,
        fontWeight: active ? 600 : 400,
        background: active
          ? "rgba(10,132,255,0.2)"
          : hovered
          ? "rgba(120,120,128,0.18)"
          : "transparent",
        border: `1px solid ${active ? "rgba(10,132,255,0.5)" : "rgba(84,84,88,0.3)"}`,
        borderRadius: 6,
        color: active ? "#0A84FF" : hovered ? "#FFFFFF" : "rgba(235,235,245,0.6)",
        cursor: "pointer",
        width: "100%",
        textAlign: "center",
        transition: "background 0.12s, color 0.12s, border-color 0.12s",
      }}
    >
      {sym}
    </button>
  );
}

export default function ChartSymbolSelector({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const allSymbols = Object.values(SYMBOL_GROUPS).flat();
  const filtered = search ? allSymbols.filter((s) => s.includes(search.toUpperCase())) : null;

  const close = () => { setOpen(false); setSearch(""); };

  return (
    <div style={{ position: "relative" }}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          ...SF,
          display: "flex",
          alignItems: "center",
          gap: 8,
          height: 44,
          padding: "0 14px",
          background: "#1C1C1E",
          border: "1px solid rgba(84,84,88,0.65)",
          borderRadius: 10,
          fontSize: 15,
          fontWeight: 600,
          color: "#FFFFFF",
          cursor: "pointer",
          transition: "border-color 0.12s",
          minWidth: 120,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(10,132,255,0.6)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(84,84,88,0.65)";
        }}
      >
        <span style={{ color: "#64D2FF", fontSize: 13, fontWeight: 400 }}>Pair</span>
        <span>{value}</span>
        <svg
          width="10" height="10" viewBox="0 0 24 24"
          fill="none" stroke="rgba(235,235,245,0.4)" strokeWidth={2.5}
          strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s", marginLeft: 2 }}
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 6px)",
          left: 0,
          zIndex: 50,
          width: 320,
          maxHeight: 420,
          overflowY: "auto",
          background: "#2C2C2E",
          border: "1px solid rgba(84,84,88,0.65)",
          borderRadius: 12,
          boxShadow: "0 12px 40px rgba(0,0,0,0.7)",
        }}>
          {/* Search */}
          <div style={{ padding: "10px 12px", borderBottom: "1px solid rgba(84,84,88,0.4)" }}>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search symbol…"
              autoFocus
              style={{
                ...SF,
                width: "100%",
                height: 36,
                background: "rgba(120,120,128,0.24)",
                border: "1px solid transparent",
                borderRadius: 8,
                padding: "0 12px",
                fontSize: 15,
                color: "#FFFFFF",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Results */}
          {filtered ? (
            <div style={{ padding: "10px 12px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 5 }}>
              {filtered.map((sym) => (
                <SymBtn key={sym} sym={sym} active={sym === value} onClick={() => { onChange(sym); close(); }} />
              ))}
              {filtered.length === 0 && (
                <div style={{
                  ...SF,
                  gridColumn: "1 / -1",
                  textAlign: "center",
                  fontSize: 13,
                  color: "rgba(235,235,245,0.3)",
                  padding: "16px 0",
                }}>
                  No symbols found
                </div>
              )}
            </div>
          ) : (
            Object.entries(SYMBOL_GROUPS).map(([group, symbols], gi, arr) => (
              <div key={group} style={{ borderBottom: gi < arr.length - 1 ? "1px solid rgba(84,84,88,0.3)" : "none" }}>
                <div style={{
                  ...SF,
                  padding: "8px 14px 4px",
                  fontSize: 12,
                  fontWeight: 600,
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                  color: "rgba(235,235,245,0.3)",
                }}>
                  {group}
                </div>
                <div style={{
                  padding: "4px 12px 10px",
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: 5,
                }}>
                  {symbols.map((sym) => (
                    <SymBtn key={sym} sym={sym} active={sym === value} onClick={() => { onChange(sym); close(); }} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Click-outside backdrop */}
      {open && (
        <div
          style={{ position: "fixed", inset: 0, zIndex: 40 }}
          onClick={close}
        />
      )}
    </div>
  );
}
