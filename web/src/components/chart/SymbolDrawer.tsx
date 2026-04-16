"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface SymbolCategory {
  id: string;
  label: string;
  symbols: string[];
}

const FALLBACK: SymbolCategory[] = [
  { id: "forex-majors",  label: "Forex Majors",  symbols: ["AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDCHF", "USDJPY"] },
  { id: "forex-crosses", label: "Forex Crosses", symbols: ["GBXUSD", "USDAED", "USDCNH", "USDHKD", "USDSGD", "USDZAR"] },
  { id: "forex-s",       label: "Forex (.s)",     symbols: [] },
  { id: "commodities",   label: "Commodities",    symbols: ["XAUUSD", "XAGUSD", "GAUUSD.s", "NG-Cs"] },
  { id: "indices",       label: "Indices",        symbols: ["NAS100.s", "SP500.s", "GER40.s", "US30.s"] },
  { id: "crypto",        label: "Crypto",          symbols: ["BTCUSD", "ETHUSD"] },
];

interface Props {
  selected: string;
  onSelect: (s: string) => void;
}

export default function SymbolDrawer({ selected, onSelect }: Props) {
  const [open, setOpen] = useState(false);
  const [categories, setCategories] = useState<SymbolCategory[]>(FALLBACK);

  useEffect(() => {
    fetch("/api/symbols")
      .then((r) => r.json())
      .then((data: { categories?: SymbolCategory[]; all?: string[] }) => {
        if (data.categories && data.categories.length > 0) {
          setCategories(data.categories);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <>
      <button
        className="flex items-center gap-1 bg-[var(--bg-3)] border border-[var(--border)] rounded px-3 py-1 cursor-pointer"
        onClick={() => setOpen(true)}
      >
        <span className="font-mono text-sm font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
          {selected}
        </span>
        <span className="text-[10px]" style={{ color: "var(--text-3)" }}>▾</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/70 z-[300] flex items-start justify-start"
          style={{ padding: "60px 0 0 200px" }}
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md p-4 w-80 max-h-[calc(100vh-100px)] overflow-y-auto"
            style={{ boxShadow: "0 24px 48px rgba(0,0,0,0.5)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-bold" style={{ fontFamily: "var(--font-ui)", color: "var(--text-1)" }}>
                Select Symbol
              </span>
              <button
                className="bg-none border-none text-[var(--text-3)] cursor-pointer text-sm"
                style={{ background: "none", border: "none", color: "var(--text-3)", cursor: "pointer", padding: "0 4px" }}
                onClick={() => setOpen(false)}
              >
                ✕
              </button>
            </div>

            {categories.map((cat) =>
              cat.symbols.length === 0 ? null : (
                <div key={cat.id} className="flex flex-col gap-1 mb-3">
                  <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
                    {cat.label}
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {cat.symbols.map((s) => (
                      <button
                        key={s}
                        className={cn(
                          "rounded px-2 py-1 font-mono text-xs font-semibold cursor-pointer transition-all border",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                          s === selected
                            ? "bg-[var(--accent)] border-[var(--accent)] text-[#0e0e0e]"
                            : "bg-[var(--bg-3)] border-[var(--border)] text-[var(--text-2)]"
                        )}
                        onClick={() => { onSelect(s); setOpen(false); }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}
    </>
  );
}
