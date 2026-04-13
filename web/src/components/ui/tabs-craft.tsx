"use client";

import { ReactNode, useState } from "react";

interface Tab {
  id: string;
  label: string;
  icon?: string;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (id: string) => void;
  children: (id: string) => ReactNode;
}

export function Tabs({ tabs, active, onChange, children }: TabsProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* Tab bar */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((tab) => {
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className="flex items-center gap-2 rounded px-4 py-2 text-sm font-semibold transition-all cursor-pointer"
              style={{
                background: isActive ? "var(--bg-3)" : "var(--bg-2)",
                border: `1px solid ${isActive ? "var(--border-active)" : "var(--border)"}`,
                color: isActive ? "var(--accent)" : "var(--text-2)",
                fontFamily: "var(--font-ui)",
                fontSize: 12,
                letterSpacing: "0.02em",
              }}
            >
              {tab.icon && (
                <span
                  className="material-symbols-outlined text-base"
                  style={{
                    fontVariationSettings: isActive
                      ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 16"
                      : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 16",
                  }}
                >
                  {tab.icon}
                </span>
              )}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div>{children(active)}</div>
    </div>
  );
}
