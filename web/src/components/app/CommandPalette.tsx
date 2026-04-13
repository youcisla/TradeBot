"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useKeyboard } from "@/hooks/useKeyboard";
import { COMMAND_ITEMS } from "@/components/app/nav-config";

/**
 * Global command palette — opens with ⌘K / Ctrl+K.
 * Built on a simple div overlay (no Radix Sheet dependency for now).
 * Add new commands in nav-config.ts COMMAND_ITEMS.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const router = useRouter();

  const filtered = COMMAND_ITEMS.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(query.toLowerCase()) ||
      cmd.id.toLowerCase().includes(query.toLowerCase())
  );

  const openPalette = useCallback(() => setOpen(true), []);
  const closePalette = useCallback(() => {
    setOpen(false);
    setQuery("");
    setSelected(0);
  }, []);

  // Register ⌘K / Ctrl+K globally
  useKeyboard([
    { key: "k", meta: true, action: openPalette },
    { key: "k", ctrl: true, action: openPalette },
    { key: "Escape", action: closePalette },
  ]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[selected]) {
        handleSelect(filtered[selected].id);
      }
    }
  }

  function handleSelect(id: string) {
    const cmd = COMMAND_ITEMS.find((c) => c.id === id);
    if (!cmd) return;
    cmd.action();
    closePalette();
  }

  if (!open) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-[200]"
      style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)" }}
      onClick={closePalette}
    >
      {/* Palette panel */}
      <div
        className="absolute left-1/2 top-[20vh] w-full max-w-lg rounded-lg overflow-hidden"
        style={{
          transform: "translateX(-50%)",
          background: "var(--bg-2)",
          border: "1px solid var(--border-active)",
          boxShadow: "var(--shadow-lg)",
        }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div
          className="flex items-center gap-3 px-4 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <span
            className="material-symbols-outlined text-base flex-shrink-0"
            style={{ color: "var(--text-3)" }}
          >
            search
          </span>
          <input
            autoFocus
            className="flex-1 bg-transparent text-sm outline-none"
            placeholder="Type a command…"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
            style={{ color: "var(--text-1)", fontFamily: "var(--font-ui)" }}
          />
          <kbd
            className="rounded px-1.5 py-0.5 text-xs"
            style={{
              background: "var(--bg-3)",
              border: "1px solid var(--border)",
              color: "var(--text-3)",
              fontFamily: "var(--font-mono)",
              fontSize: 10,
            }}
          >
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-64 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <div className="px-4 py-6 text-center" style={{ color: "var(--text-3)" }}>
              <span className="text-sm" style={{ fontFamily: "var(--font-ui)" }}>No commands found</span>
            </div>
          ) : (
            filtered.map((cmd, i) => (
              <button
                key={cmd.id}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors"
                style={{
                  background: i === selected ? "var(--bg-3)" : "transparent",
                  cursor: "pointer",
                }}
                onClick={() => handleSelect(cmd.id)}
                onMouseEnter={() => setSelected(i)}
              >
                <span
                  className="material-symbols-outlined text-base flex-shrink-0"
                  style={{ color: "var(--text-3)" }}
                >
                  {cmd.icon}
                </span>
                <span
                  className="text-sm"
                  style={{ color: "var(--text-1)", fontFamily: "var(--font-ui)" }}
                >
                  {cmd.label}
                </span>
                {cmd.group && (
                  <span
                    className="ml-auto text-xs uppercase tracking-widest"
                    style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 9 }}
                  >
                    {cmd.group}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
