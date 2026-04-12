"use client";

import { useState, useEffect } from "react";
import { useAppShell } from "@/components/AppShell";

interface SymbolCategory {
  id: string;
  label: string;
  symbols: string[];
}

// Fallback hardcoded list — used until Python bot writes data/symbols.json
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
  const { intelligence } = useAppShell();
  const sweepAge = intelligence?.sweepAgeMin;

  useEffect(() => {
    fetch("/api/symbols")
      .then((r) => r.json())
      .then((data: { categories?: SymbolCategory[]; all?: string[] }) => {
        if (data.categories && data.categories.length > 0) {
          setCategories(data.categories);
        }
      })
      .catch(() => {
        // Keep fallback on error
      });
  }, []);

  return (
    <>
      <button style={styles.trigger} onClick={() => setOpen(true)}>
        <span style={styles.sym}>{selected}</span>
        <span style={styles.chevron}>▾</span>
      </button>

      {open && (
        <div style={styles.backdrop} onClick={() => setOpen(false)}>
          <div style={styles.drawer} onClick={(e) => e.stopPropagation()}>
            <div style={styles.drawerHeader}>
              <span style={styles.drawerTitle}>Select Symbol</span>
              <button style={styles.closeBtn} onClick={() => setOpen(false)}>✕</button>
            </div>

            {categories.map((cat) =>
              cat.symbols.length === 0 ? null : (
                <div key={cat.id} style={styles.group}>
                  <span style={styles.groupLabel}>{cat.label}</span>
                  <div style={styles.groupSymbols}>
                    {cat.symbols.map((s) => (
                      <button
                        key={s}
                        style={{
                          ...styles.symbolBtn,
                          ...(s === selected ? styles.symbolBtnActive : {}),
                        }}
                        onClick={() => { onSelect(s); setOpen(false); }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )
            )}

            {sweepAge !== undefined && (
              <div style={styles.sweepInfo}>
                <span style={styles.sweepLabel}>Last sweep:</span>
                <span style={styles.sweepValue}>{sweepAge}m ago</span>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const styles: Record<string, React.CSSProperties> = {
  trigger: {
    display:       "flex",
    alignItems:     "center",
    gap:            4,
    background:     "var(--bg-3)",
    border:        "1px solid var(--border)",
    borderRadius:  "var(--radius-sm)",
    cursor:        "pointer",
    padding:       "4px 10px",
  },
  sym: {
    fontFamily: "var(--font-mono)",
    fontSize:   12,
    fontWeight:  700,
    color:      "var(--text-1)",
  },
  chevron: {
    fontSize: 10,
    color:   "var(--text-3)",
  },
  backdrop: {
    position:    "fixed",
    inset:       0,
    background:  "rgba(0,0,0,0.7)",
    zIndex:     300,
    display:    "flex",
    alignItems: "flex-start",
    justifyContent: "flex-start",
    padding:    "60px 0 0 200px",
  },
  drawer: {
    background:  "var(--bg-2)",
    border:      "1px solid var(--border)",
    borderRadius:"var(--radius-md)",
    padding:     "var(--space-3)",
    width:       320,
    maxHeight:   "calc(100vh - 100px)",
    overflowY:   "auto",
    boxShadow:   "0 24px 48px rgba(0,0,0,0.5)",
    display:    "flex",
    flexDirection: "column",
    gap:        "var(--space-3)",
  },
  drawerHeader: {
    display:        "flex",
    alignItems:     "center",
    justifyContent: "space-between",
  },
  drawerTitle: {
    fontFamily: "var(--font-ui)",
    fontSize:   13,
    fontWeight:  700,
    color:      "var(--text-1)",
  },
  closeBtn: {
    background: "none",
    border:     "none",
    color:      "var(--text-3)",
    cursor:     "pointer",
    fontSize:   12,
    padding:    "0 4px",
  },
  group: {
    display:       "flex",
    flexDirection: "column",
    gap:           "var(--space-1)",
  },
  groupLabel: {
    fontFamily:    "var(--font-mono)",
    fontSize:      9,
    fontWeight:    700,
    color:         "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  groupSymbols: {
    display:   "flex",
    flexWrap:  "wrap",
    gap:       4,
  },
  symbolBtn: {
    background:  "var(--bg-3)",
    border:     "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color:      "var(--text-2)",
    cursor:     "pointer",
    fontFamily: "var(--font-mono)",
    fontSize:   11,
    fontWeight: 600,
    padding:    "3px 8px",
  },
  symbolBtnActive: {
    background: "var(--accent)",
    border:    "1px solid var(--accent)",
    color:     "#0e0e0e",
  },
  sweepInfo: {
    display:       "flex",
    alignItems:    "center",
    gap:           "var(--space-2)",
    paddingTop:    "var(--space-2)",
    borderTop:     "1px solid var(--border)",
  },
  sweepLabel: {
    fontFamily: "var(--font-mono)",
    fontSize:   10,
    color:      "var(--text-3)",
  },
  sweepValue: {
    fontFamily: "var(--font-mono)",
    fontSize:   10,
    fontWeight: 700,
    color:      "var(--text-2)",
  },
};
