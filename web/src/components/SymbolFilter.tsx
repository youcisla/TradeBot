"use client";

const SYMBOLS = [
  "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF",
  "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURAUD", "EURCAD",
  "GBPCHF", "GBPAUD", "CADJPY", "CHFJPY", "EURCHF", "NZDJPY",
  "XAUUSD", "XAGUSD", "USOUSD", "UKOUSD",
  "BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD",
  "USDZAR", "USDTRY",
];

const chip = (active: boolean) =>
  `px-2 py-0.5 rounded text-[10px] font-bold uppercase border transition-colors cursor-pointer whitespace-nowrap ${
    active
      ? "border-matrix bg-matrix/20 text-matrix"
      : "border-terminal-border text-matrix-dim hover:text-matrix"
  }`;

export default function SymbolFilter({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (symbol: string | null) => void;
}) {
  // Derive which symbols to show: only those the user has data for
  // For now, show all known symbols with an "All" reset button
  return (
    <div className="flex flex-wrap gap-1.5 items-center">
      <button className={chip(value === null)} onClick={() => onChange(null)}>
        All
      </button>
      {SYMBOLS.map((s) => (
        <button
          key={s}
          className={chip(value === s)}
          onClick={() => onChange(value === s ? null : s)}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
