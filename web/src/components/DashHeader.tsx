"use client";

import { useEffect, useState } from "react";

interface StatusData {
  state: string;
  equity: number;
  daily_pnl: number;
  balance: number;
}

export default function DashHeader() {
  const [status, setStatus] = useState<StatusData | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/status")
        .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
        .then((data: StatusData) => { if (active) setStatus(data); })
        .catch(() => {});
    load();
    const id = setInterval(load, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const isRunning = status?.state === "running";
  const equity = status ? Number(status.equity) : null;
  const dailyPnl = status ? Number(status.daily_pnl) : null;
  const pnlPositive = dailyPnl !== null && dailyPnl >= 0;

  return (
    <>
      <header
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 52,
          zIndex: 100,
          background: "rgba(28,28,30,0.9)",
          backdropFilter: "blur(20px) saturate(180%)",
          WebkitBackdropFilter: "blur(20px) saturate(180%)",
          borderBottom: "0.5px solid rgba(84,84,88,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 16px",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        {/* Left: wordmark + status */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontSize: 17,
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "-0.01em",
            }}
          >
            NeuralFX
          </span>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "3px 8px",
              background: isRunning ? "rgba(48,209,88,0.12)" : "rgba(142,142,147,0.15)",
              borderRadius: 6,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: isRunning ? "#30D158" : "#8E8E93",
                display: "inline-block",
                boxShadow: isRunning ? "0 0 6px #30D158" : undefined,
                animation: isRunning ? "headerDotPulse 2s ease-in-out infinite" : undefined,
              }}
            />
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: isRunning ? "#30D158" : "#8E8E93",
                letterSpacing: "0.02em",
              }}
            >
              {status ? (isRunning ? "LIVE" : status.state?.toUpperCase() ?? "—") : "—"}
            </span>
          </div>
        </div>

        {/* Right: equity, PnL, avatar */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {equity !== null && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 1 }}>
              <span
                style={{
                  fontSize: 11,
                  color: "rgba(235,235,245,0.4)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Equity
              </span>
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#FFFFFF",
                  fontFamily: "ui-monospace, 'SF Mono', monospace",
                  letterSpacing: "-0.01em",
                }}
              >
                {equity.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 })}
              </span>
            </div>
          )}

          {dailyPnl !== null && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: 1,
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  color: "rgba(235,235,245,0.4)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Daily P&L
              </span>
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: pnlPositive ? "#30D158" : "#FF453A",
                  fontFamily: "ui-monospace, 'SF Mono', monospace",
                  letterSpacing: "-0.01em",
                }}
              >
                {pnlPositive ? "+" : ""}
                {dailyPnl.toFixed(2)}
              </span>
            </div>
          )}

          {/* Avatar / settings button */}
          <button
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: "rgba(120,120,128,0.36)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(235,235,245,0.6)",
              flexShrink: 0,
            }}
            aria-label="Settings"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
              person
            </span>
          </button>
        </div>
      </header>

      <style>{`
        @keyframes headerDotPulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 6px #30D158; }
          50% { opacity: 0.5; box-shadow: 0 0 12px #30D158; }
        }
      `}</style>
    </>
  );
}
