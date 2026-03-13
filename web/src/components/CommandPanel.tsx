"use client";

import { useState } from "react";

export default function CommandPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string | null>(null);

  async function send(command: string) {
    setLoading(command);
    setLastResult(null);
    try {
      const res = await fetch("/api/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      const data = await res.json();
      setLastResult(data.ok ? `${command} sent` : data.error);
    } catch {
      setLastResult("Network error");
    } finally {
      setLoading(null);
    }
  }

  const buttons = [
    { cmd: "pause", label: "⏸ PAUSE", cls: "border-yellow-400 text-yellow-400 hover:bg-yellow-400 hover:text-black" },
    { cmd: "resume", label: "▶ RESUME", cls: "border-matrix text-matrix hover:bg-matrix hover:text-black" },
    { cmd: "kill", label: "☠ KILL ALL", cls: "border-red-500 text-red-500 hover:bg-red-500 hover:text-black" },
  ];

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-4">
      <div className="text-matrix-dim text-xs uppercase tracking-widest mb-3">
        Command Panel
      </div>
      <div className="flex gap-3 flex-wrap">
        {buttons.map((b) => (
          <button
            key={b.cmd}
            disabled={loading !== null}
            onClick={() => send(b.cmd)}
            className={`px-4 py-1.5 border rounded text-xs font-bold uppercase transition-colors ${b.cls} disabled:opacity-40`}
          >
            {loading === b.cmd ? "…" : b.label}
          </button>
        ))}
      </div>
      {lastResult && (
        <div className="mt-2 text-matrix-dim text-xs">→ {lastResult}</div>
      )}
    </div>
  );
}
