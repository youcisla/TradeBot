"use client";

import { Panel } from "@/components/ui/panel";

export default function SignalsPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-64 rounded gap-3"
      style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
    >
      <span
        className="material-symbols-outlined text-5xl opacity-30"
        style={{ color: "var(--text-3)", fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 48" }}
      >
        sync
      </span>
      <p className="font-bold text-base" style={{ color: "var(--text-1)", margin: 0 }}>
        Signals Intelligence
      </p>
      <p className="font-mono text-xs" style={{ color: "var(--text-3)", margin: 0, maxWidth: 320, textAlign: "center" }}>
        ICT signal detection and HKU marketplace signal feed coming in a future update.
      </p>
    </div>
  );
}
