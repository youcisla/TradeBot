"use client";

import { cn } from "@/lib/utils";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"] as const;
type TF = typeof TIMEFRAMES[number];

interface Props {
  selected: TF;
  onChange: (tf: TF) => void;
}

export default function TimeframeBar({ selected, onChange }: Props) {
  return (
    <div className="flex items-center gap-0.5">
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf}
          className={cn(
            "rounded px-2 py-1 font-mono text-xs font-semibold cursor-pointer transition-all border",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
            tf === selected
              ? "bg-[var(--bg-3)] border-[var(--border-active)] text-[var(--text-1)]"
              : "bg-transparent border-transparent text-[var(--text-3)] hover:text-[var(--text-2)]"
          )}
          onClick={() => onChange(tf)}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
