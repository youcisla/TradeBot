"use client";

import { useState, useEffect } from "react";

interface Command {
  id: string;
  label: string;
  hint: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNav: (page: string) => void;
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.5-4.5" />
    </svg>
  );
}

export function CommandPalette({ open, onClose, onNav }: CommandPaletteProps) {
  const [q, setQ] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  const cmds: Command[] = [
    { id: "g:mission",  label: "Go to Mission Control",        hint: "Page" },
    { id: "g:signals",  label: "Go to Signal Intelligence",      hint: "Page" },
    { id: "g:trades",   label: "Go to Trade Operations",          hint: "Page" },
    { id: "g:risk",     label: "Go to Risk & Exposure",           hint: "Page" },
    { id: "g:agents",   label: "Go to Agent Observability",       hint: "Page" },
    { id: "g:macro",    label: "Go to Macro Intelligence",         hint: "Page" },
    { id: "g:perf",     label: "Go to Performance",               hint: "Page" },
    { id: "g:learn",    label: "Go to Learning",                  hint: "Page" },
    { id: "g:health",   label: "Go to System Health",             hint: "Page" },
    { id: "g:settings", label: "Go to Controls & Settings",       hint: "Page" },
    { id: "act:pause",    label: "Pause bot",                      hint: "Action" },
    { id: "act:resume",    label: "Resume bot",                     hint: "Action" },
    { id: "act:closeall", label: "Close all positions",            hint: "Danger" },
    { id: "act:retrain",   label: "Trigger LGBM retrain",          hint: "Action" },
    { id: "ask:why",       label: "Ask: why was GBPUSD blocked?",  hint: "DeepSeek" },
    { id: "ask:brief",     label: "Ask: brief me on next 2h",     hint: "DeepSeek" },
  ];

  const filtered = cmds.filter((c) =>
    c.label.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="palette-back" onClick={onClose}>
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <div className="palette-input">
          <span style={{ color: "var(--fg-3)" }}>
            <SearchIcon />
          </span>
          <input
            autoFocus
            placeholder="Type a command, page, or ask DeepSeek…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <span className="kbd">ESC</span>
        </div>
        <div className="palette-list">
          {filtered.map((c) => (
            <button
              key={c.id}
              className="palette-item"
              onClick={() => {
                if (c.id.startsWith("g:")) onNav(c.id.slice(2));
                onClose();
              }}
            >
              <span>{c.label}</span>
              <span className="dim mono" style={{ fontSize: 10.5 }}>
                {c.hint}
              </span>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="empty">No results.</div>
          )}
        </div>
        <div className="palette-foot">
          <span className="hint">
            DeepSeek NL · powered by the bot&apos;s natural-language layer
          </span>
          <span>
            <span className="kbd">↑↓</span>{" "}
            <span className="kbd">↵</span>
          </span>
        </div>
      </div>
    </div>
  );
}
