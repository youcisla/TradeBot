"use client";

import { useAppShell } from "@/components/AppShell";

export default function DashHeader() {
  const { status, isRunning } = useAppShell();

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
          height: 64,
          zIndex: 100,
          background:
            "linear-gradient(180deg, rgba(13,17,25,0.86) 0%, rgba(10,13,18,0.78) 100%)",
          backdropFilter: "blur(18px) saturate(145%)",
          WebkitBackdropFilter: "blur(18px) saturate(145%)",
          borderBottom: "1px solid rgba(95,122,158,0.35)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 18px",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
          boxShadow: "0 14px 30px rgba(0,0,0,0.35)",
        }}
      >
        {/* Left: wordmark + status */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span
            style={{
              width: 14,
              height: 14,
              borderRadius: 4,
              background: "linear-gradient(140deg, #30d6ff 0%, #8bf7b4 100%)",
              boxShadow: "0 0 16px rgba(48,214,255,0.7)",
              transform: "rotate(45deg)",
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "#eaf2ff",
              letterSpacing: "0.03em",
              textTransform: "uppercase",
            }}
          >
            PulseTrade
          </span>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              background: isRunning ? "rgba(102,246,165,0.16)" : "rgba(142,142,147,0.18)",
              borderRadius: 999,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: isRunning ? "#66f6a5" : "#8E8E93",
                display: "inline-block",
                boxShadow: isRunning ? "0 0 6px #66f6a5" : undefined,
                animation: isRunning ? "headerDotPulse 2s ease-in-out infinite" : undefined,
              }}
            />
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: isRunning ? "#66f6a5" : "#8E8E93",
                letterSpacing: "0.07em",
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
                  color: "rgba(184,203,232,0.5)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Equity
              </span>
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#f0f5ff",
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
                  color: "rgba(184,203,232,0.5)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
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
              width: 34,
              height: 34,
              borderRadius: "50%",
              background: "rgba(108,146,185,0.24)",
              border: "1px solid rgba(126,171,214,0.42)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(223,235,253,0.78)",
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
          0%, 100% { opacity: 1; box-shadow: 0 0 6px #66f6a5; }
          50% { opacity: 0.5; box-shadow: 0 0 12px #66f6a5; }
        }
      `}</style>
    </>
  );
}
