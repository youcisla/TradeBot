"use client";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];

interface Props {
  value: string;
  onChange: (tf: string) => void;
}

export default function TimeframeSelector({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-1">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf}
          onClick={() => onChange(tf)}
          className={`px-3 py-1.5 text-xs font-bold rounded border transition-all ${
            tf === value
              ? "bg-matrix/20 text-matrix border-matrix shadow-[0_0_8px_rgba(0,255,65,0.3)]"
              : "bg-terminal-surface text-matrix-dim border-terminal-border hover:text-matrix hover:border-matrix/50"
          }`}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
