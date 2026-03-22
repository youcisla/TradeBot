"use client";

const SYMBOLS = [
  "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF",
  "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURAUD", "EURCAD",
  "GBPCHF", "GBPAUD", "CADJPY", "CHFJPY", "EURCHF", "NZDJPY",
  "XAUUSD", "XAGUSD", "USOUSD", "UKOUSD",
  "BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD",
  "USDZAR", "USDTRY",
];

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "3px 9px",
        background: active ? "rgba(0,212,255,0.12)" : "transparent",
        border: `1px solid ${active ? "rgba(0,212,255,0.4)" : "#1c1c28"}`,
        borderRadius: 4,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9.5, fontWeight: 700, letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: active ? "#00d4ff" : "#2a3a4a",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "border-color 0.15s, color 0.15s, background 0.15s",
        boxShadow: active ? "0 0 8px rgba(0,212,255,0.2)" : "none",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.borderColor = "#2a3a4a";
          btn.style.color = "#4a5a6a";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          const btn = e.currentTarget as HTMLButtonElement;
          btn.style.borderColor = "#1c1c28";
          btn.style.color = "#2a3a4a";
        }
      }}
    >
      {children}
    </button>
  );
}

export default function SymbolFilter({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (symbol: string | null) => void;
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
      <Chip active={value === null} onClick={() => onChange(null)}>
        All
      </Chip>
      {SYMBOLS.map((s) => (
        <Chip
          key={s}
          active={value === s}
          onClick={() => onChange(value === s ? null : s)}
        >
          {s}
        </Chip>
      ))}
    </div>
  );
}
