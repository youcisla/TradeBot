"use client";

import { ReactNode } from "react";

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
      className={`rounded flex flex-col ${className}`}
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border)",
      }}
    >
      {title && (
        <div
          className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
          style={{ borderColor: "var(--border)" }}
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
