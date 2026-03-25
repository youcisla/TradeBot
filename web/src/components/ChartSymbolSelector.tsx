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

interface Props {
  value: string;
  onChange: (symbol: string) => void;
}

function SymBtn({ sym, active, onClick }: { sym: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 6px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, fontWeight: 700, letterSpacing: "0.02em",
        background: active ? "rgba(0,255,136,0.15)" : "transparent",
        border: `1px solid ${active ? "rgba(0,255,136,0.4)" : "#1c1c28"}`,
        borderRadius: 3,
        color: active ? "#00ff88" : "#607888",
        cursor: "pointer",
        width: "100%",
        textAlign: "center",
        transition: "background 0.1s, color 0.1s, border-color 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.color = "#c0ccd8";
          btn.style.borderColor = "#607888";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.color = "#607888";
          btn.style.borderColor = "#1c1c28";
        }
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
          display: "flex", alignItems: "center", gap: 8,
          padding: "6px 14px",
          background: "#0a0a12",
          border: "1px solid #1c1c28",
          borderRadius: 5,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, fontWeight: 700,
          color: "#00d4ff",
          cursor: "pointer",
          transition: "border-color 0.12s",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(0,212,255,0.4)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#1c1c28"; }}
      >
        {value}
        <svg
          width="10" height="10" viewBox="0 0 24 24"
          fill="none" stroke="#607888" strokeWidth={2.5}
          strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 4px)",
          left: 0,
          zIndex: 50,
          width: 300,
          maxHeight: 380,
          overflowY: "auto",
          background: "#0a0a12",
          border: "1px solid #1c1c28",
          borderRadius: 6,
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}>
          {/* Search */}
          <div style={{ padding: "8px 10px", borderBottom: "1px solid #1c1c28" }}>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search symbol…"
              autoFocus
              style={{
                width: "100%",
                background: "#06060c",
                border: "1px solid #1c1c28",
                borderRadius: 4,
                padding: "5px 10px",
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10.5, color: "#c0ccd8",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Results */}
          {filtered ? (
            <div style={{ padding: "8px 10px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 4 }}>
              {filtered.map((sym) => (
                <SymBtn key={sym} sym={sym} active={sym === value} onClick={() => { onChange(sym); close(); }} />
              ))}
              {filtered.length === 0 && (
                <div style={{
                  gridColumn: "1 / -1", textAlign: "center",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9.5, color: "#607888", padding: "12px 0",
                }}>
                  No symbols found
                </div>
              )}
            </div>
          ) : (
            Object.entries(SYMBOL_GROUPS).map(([group, symbols], gi, arr) => (
              <div key={group} style={{ borderBottom: gi < arr.length - 1 ? "1px solid #1c1c28" : "none" }}>
                <div style={{
                  padding: "6px 12px 2px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 8, fontWeight: 700, letterSpacing: "0.18em",
                  textTransform: "uppercase", color: "#607888",
                }}>
                  {group}
                </div>
                <div style={{
                  padding: "4px 10px 8px",
                  display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 4,
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
