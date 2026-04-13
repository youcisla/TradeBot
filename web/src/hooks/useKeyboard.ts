"use client";

import { useEffect } from "react";

interface Shortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  action: () => void;
}

/**
 * Register keyboard shortcuts.
 * Pass an array of Shortcut objects.
 * Auto-cleanup on unmount.
 *
 * @example
 * useKeyboard([
 *   { key: "k", meta: true, action: () => setOpen(true) },
 *   { key: "Escape", action: () => setOpen(false) },
 * ]);
 */
export function useKeyboard(shortcuts: Shortcut[]) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      for (const shortcut of shortcuts) {
        const metaMatch = shortcut.meta
          ? e.metaKey || e.ctrlKey   // meta = ⌘ on Mac, Ctrl on Windows
          : !e.metaKey && !e.ctrlKey;

        if (
          e.key === shortcut.key &&
          metaMatch &&
          (shortcut.shift ? e.shiftKey : !e.shiftKey)
        ) {
          e.preventDefault();
          shortcut.action();
          return;
        }
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [shortcuts]);
}
