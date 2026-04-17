"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[dashboard error]", error);
  }, [error]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 320,
        gap: 20,
        padding: "40px 24px",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: "var(--red)",
            marginBottom: 8,
          }}
        >
          Something went wrong
        </div>
        <div
          style={{
            fontSize: 14,
            color: "var(--text-3)",
            maxWidth: 400,
            lineHeight: 1.6,
          }}
        >
          {error.digest ? (
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
              [{error.digest}]
            </span>
          ) : null}
          {" "}The dashboard failed to load. Check the bot status and try refreshing.
        </div>
      </div>
      <button
        onClick={reset}
        style={{
          padding: "9px 22px",
          background: "var(--red)",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Try again
      </button>
    </div>
  );
}
