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

export default function ChartSymbolSelector({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const allSymbols = Object.values(SYMBOL_GROUPS).flat();
  const filtered = search
    ? allSymbols.filter((s) => s.includes(search.toUpperCase()))
    : null;

  return (
    <div className="relative">
      {/* Current symbol button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-4 py-2 bg-terminal-surface border border-terminal-border rounded hover:border-matrix/50 transition-colors"
      >
        <span className="text-matrix font-bold text-sm">{value}</span>
        <svg
          className={`w-3 h-3 text-matrix-dim transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 w-80 max-h-96 overflow-y-auto bg-terminal-surface border border-terminal-border rounded shadow-lg shadow-black/50">
          {/* Search */}
          <div className="p-2 border-b border-terminal-border">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search symbol..."
              className="w-full px-3 py-1.5 text-xs bg-terminal border border-terminal-border rounded text-matrix placeholder:text-matrix-dim/50 focus:outline-none focus:border-matrix/50"
              autoFocus
            />
          </div>

          {/* Filtered results */}
          {filtered ? (
            <div className="p-2 grid grid-cols-4 gap-1">
              {filtered.map((sym) => (
                <button
                  key={sym}
                  onClick={() => { onChange(sym); setOpen(false); setSearch(""); }}
                  className={`px-2 py-1.5 text-[10px] font-bold rounded border transition-all ${
                    sym === value
                      ? "bg-matrix/20 text-matrix border-matrix"
                      : "bg-terminal text-matrix-dim border-terminal-border hover:text-matrix hover:border-matrix/50"
                  }`}
                >
                  {sym}
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="col-span-4 text-matrix-dim text-xs text-center py-2">
                  No symbols found
                </div>
              )}
            </div>
          ) : (
            /* Grouped view */
            Object.entries(SYMBOL_GROUPS).map(([group, symbols]) => (
              <div key={group} className="border-b border-terminal-border last:border-0">
                <div className="px-3 py-1.5 text-[10px] text-matrix-dim/60 uppercase tracking-widest">
                  {group}
                </div>
                <div className="px-2 pb-2 grid grid-cols-4 gap-1">
                  {symbols.map((sym) => (
                    <button
                      key={sym}
                      onClick={() => { onChange(sym); setOpen(false); }}
                      className={`px-2 py-1.5 text-[10px] font-bold rounded border transition-all ${
                        sym === value
                          ? "bg-matrix/20 text-matrix border-matrix"
                          : "bg-terminal text-matrix-dim border-terminal-border hover:text-matrix hover:border-matrix/50"
                      }`}
                    >
                      {sym}
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Click outside to close */}
      {open && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => { setOpen(false); setSearch(""); }}
        />
      )}
    </div>
  );
}
