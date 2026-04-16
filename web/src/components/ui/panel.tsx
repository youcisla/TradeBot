"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PanelProps {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  action?: ReactNode;
  noPadding?: boolean;
}

export function Panel({ children, className = "", title, action, noPadding = false }: PanelProps) {
  return (
    <div
      className={cn("rounded flex flex-col bg-[var(--bg-2)] border border-[var(--border)]", className)}
    >
      {title && (
        <div
          className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] flex-shrink-0"
        >
          <span
            className="text-xs font-bold uppercase tracking-widest"
            style={{
              color: "var(--text-3)",
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              letterSpacing: "0.08em",
            }}
          >
            {title}
          </span>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={`flex-1 ${noPadding ? "" : "p-4"}`}>
        {children}
      </div>
    </div>
  );
}
