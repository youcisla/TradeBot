"use client";

import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export default function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div
      style={{
        paddingBottom: 20,
        borderBottom: "0.5px solid rgba(84,84,88,0.35)",
        marginBottom: 20,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1
            style={{
              margin: 0,
              fontSize: 28,
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "-0.015em",
              lineHeight: 1.15,
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p
              style={{
                margin: "6px 0 0",
                fontSize: 15,
                color: "rgba(235,235,245,0.6)",
                lineHeight: 1.4,
              }}
            >
              {subtitle}
            </p>
          )}
        </div>

        {action && (
          <div style={{ flexShrink: 0, alignSelf: "center" }}>
            {action}
          </div>
        )}
      </div>
    </div>
  );
}
