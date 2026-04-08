"use client";

import { useState, useEffect } from "react";
import TradingChart from "@/components/TradingChart";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ArcGauge } from "@/components/ui/ArcGauge";
import { EventFeed, FeedEvent } from "@/components/ui/EventFeed";

export default function MarketIntel() {
  const [symbol, setSymbol] = useState("BTC/USD");
  const [timeframe, setTimeframe] = useState("15m");

  // Overlays state (not yet fully connected to Chart, but UI ready)
  const [showFVG, setShowFVG] = useState(true);
  const [showOB, setShowOB] = useState(true);
  const [showFIB, setShowFIB] = useState(false);

  // Symbol Events
  const [events, setEvents] = useState<FeedEvent[]>([]);

  useEffect(() => {
    let active = true;
    const fetchEm = async () => {
      try {
        const res = await fetch("/api/events?limit=50");
        const data = await res.json();
        if (active && Array.isArray(data)) {
          const mapped: FeedEvent[] = [];
          for (let i = 0; i < data.length; i++) {
            const e = data[i];
            const m = (e.message || e.msg || "").toLowerCase();
            const s = symbol.split("/")[0].toLowerCase();
            if (m.includes(s) || m.includes("all markets")) {
              mapped.push({
                id: String(e.id || Math.random()),
                timestamp: String(e.ts || e.created_at || new Date().toISOString()),
                agent: String(e.agent || "SYSTEM"),
                level: String(e.level || "info").toLowerCase(),
                message: String(e.message || e.msg || ""),
              });
            }
          }
          setEvents(mapped.slice(0, 50));
        }
      } catch (_err) {}
    };
    fetchEm();
    const inv = setInterval(fetchEm, 5000);
    return () => { active = false; clearInterval(inv); };
  }, [symbol]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "calc(100vh - 64px)",
        padding: "24px",
        gap: 20,
        maxWidth: 1800,
        margin: "0 auto",
      }}
    >
      {/* ── Top Toolbar ─────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "14px 20px",
          background: "var(--bg-2)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)",
          flexShrink: 0,
        }}
      >
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          style={{
            background: "var(--bg-3)",
            border: "1px solid var(--border)",
            color: "var(--text-1)",
            fontFamily: "var(--font-mono)",
            fontWeight: 700,
            fontSize: 15,
            padding: "8px 14px",
            borderRadius: "var(--radius-sm)",
            outline: "none",
            cursor: "pointer",
          }}
        >
          <option value="BTC/USD">BTC/USD</option>
          <option value="ETH/USD">ETH/USD</option>
          <option value="SOL/USD">SOL/USD</option>
        </select>

        <div
          style={{
            display: "flex",
            gap: 4,
            padding: 4,
            background: "var(--bg-3)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {["1m", "5m", "15m", "1h", "4h", "1d", "1w"].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              style={{
                padding: "6px 12px",
                fontFamily: "var(--font-ui)",
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                borderRadius: "var(--radius-sm)",
                border: "none",
                cursor: "pointer",
                background: timeframe === tf ? "var(--bg-4)" : "transparent",
                color: timeframe === tf ? "var(--text-1)" : "var(--text-3)",
                transition: "all 0.15s ease",
              }}
            >
              {tf}
            </button>
          ))}
        </div>

        <div style={{ width: 1, height: 28, background: "var(--border)", flexShrink: 0 }} />

        <div style={{ display: "flex", gap: 10 }}>
          {[
            { id: "fvg", label: "FVG", val: showFVG, set: setShowFVG },
            { id: "ob", label: "Order Blocks", val: showOB, set: setShowOB },
            { id: "fib", label: "Fibonacci", val: showFIB, set: setShowFIB },
          ].map((o) => (
            <button
              key={o.id}
              onClick={() => o.set(!o.val)}
              style={{
                padding: "6px 14px",
                fontFamily: "var(--font-ui)",
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                borderRadius: "var(--radius-sm)",
                border: `1px solid ${o.val ? "var(--gold)" : "var(--border)"}`,
                cursor: "pointer",
                background: o.val ? "var(--gold-dim)" : "var(--bg-3)",
                color: o.val ? "var(--gold)" : "var(--text-3)",
                transition: "all 0.15s ease",
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Content ─────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          flex: 1,
          gap: 20,
          minHeight: 0, // critical: allows flex children to shrink below content size
        }}
      >
        {/* Left: Chart + Activity Stream */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            gap: 16,
            minWidth: 0,
          }}
        >
          {/* Chart */}
          <div
            style={{
              flex: 1,
              background: "var(--bg-1)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              overflow: "hidden",
              position: "relative",
              minHeight: 380,
            }}
          >
            <div style={{ position: "absolute", inset: 0 }}>
              <TradingChart symbol={symbol} timeframe={timeframe} />
            </div>
          </div>

          {/* Activity Stream */}
          <Card style={{ flexShrink: 0 }}>
            <CardHeader>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>Activity Stream: {symbol}</span>
                <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
                  {events.length} events
                </span>
              </div>
            </CardHeader>
            <CardBody style={{ padding: 0 }}>
              <div style={{ height: 220, overflow: "hidden" }}>
                <EventFeed events={events} />
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Right: Stats Panel */}
        <div
          style={{
            width: 360,
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            gap: 16,
            overflowY: "auto",
          }}
        >
          {/* Live Market Stats */}
          <Card>
            <CardHeader>Live Market Stats</CardHeader>
            <CardBody style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Bid/Ask Row */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  paddingBottom: 16,
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 10,
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      color: "var(--text-3)",
                      fontWeight: 700,
                      marginBottom: 4,
                    }}
                  >
                    Bid
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 18,
                      fontWeight: 600,
                      color: "var(--text-1)",
                    }}
                  >
                    98,241.50
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontSize: 10,
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      color: "var(--text-3)",
                      fontWeight: 700,
                      marginBottom: 4,
                    }}
                  >
                    Ask
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 18,
                      fontWeight: 600,
                      color: "var(--text-1)",
                    }}
                  >
                    98,242.00
                  </div>
                </div>
              </div>

              {/* Spread */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  paddingBottom: 16,
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "var(--text-3)",
                    fontWeight: 700,
                  }}
                >
                  Spread
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--cyan)",
                  }}
                >
                  0.50 pips
                </span>
              </div>

              {/* Session */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  paddingBottom: 16,
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "var(--text-3)",
                    fontWeight: 700,
                  }}
                >
                  Session
                </span>
                <span
                  style={{
                    padding: "4px 10px",
                    background: "var(--blue-dim)",
                    color: "var(--blue)",
                    fontFamily: "var(--font-ui)",
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  New York
                </span>
              </div>

              {/* Daily Range */}
              <div style={{ paddingBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      color: "var(--text-3)",
                      fontWeight: 700,
                    }}
                  >
                    Daily Range
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--text-2)",
                    }}
                  >
                    2.4%
                  </span>
                </div>
                <div
                  style={{
                    height: 6,
                    width: "100%",
                    background: "var(--bg-4)",
                    borderRadius: 3,
                    overflow: "hidden",
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: "20%",
                      right: "30%",
                      height: "100%",
                      background: "var(--text-3)",
                      opacity: 0.4,
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      left: "65%",
                      width: 2,
                      height: "100%",
                      background: "var(--gold)",
                    }}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginTop: 6,
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    color: "var(--text-3)",
                  }}
                >
                  <span>$96,000</span>
                  <span>$99,200</span>
                </div>
              </div>

              {/* RSI */}
              <div style={{ paddingBottom: 16, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "var(--text-3)",
                    fontWeight: 700,
                    marginBottom: 12,
                  }}
                >
                  RSI (14)
                </div>
                <div style={{ display: "flex", justifyContent: "center" }}>
                  <ArcGauge value={62} max={100} label="" size={100} />
                </div>
              </div>

              {/* ICT Signal */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "var(--text-3)",
                    fontWeight: 700,
                  }}
                >
                  ICT Signal
                </span>
                <span
                  style={{
                    padding: "6px 12px",
                    background: "var(--gold-dim)",
                    color: "var(--gold)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    fontWeight: 700,
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid rgba(240,180,41,0.3)",
                  }}
                >
                  LONG (92%)
                </span>
              </div>
            </CardBody>
          </Card>

          {/* Symbol Info */}
          <Card>
            <CardHeader>Symbol Info</CardHeader>
            <CardBody style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[
                { label: "Symbol", value: "BTC/USD" },
                { label: "Contract Size", value: "1 BTC" },
                { label: "Tick Size", value: "0.01" },
                { label: "Margin Req.", value: "1.0%" },
                { label: "Swap Long", value: "-0.05%" },
                { label: "Swap Short", value: "0.02%" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 12, color: "var(--text-3)" }}>{label}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--text-1)",
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </CardBody>
          </Card>

          {/* Quick Overlays Legend */}
          <Card>
            <CardHeader>Active Overlays</CardHeader>
            <CardBody style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "Fair Value Gap", active: showFVG, color: "var(--cyan)" },
                { label: "Order Blocks", active: showOB, color: "var(--gold)" },
                { label: "Fibonacci", active: showFIB, color: "var(--purple)" },
              ].map(({ label, active, color }) => (
                <div
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    opacity: active ? 1 : 0.35,
                  }}
                >
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      background: color,
                      flexShrink: 0,
                    }}
                  />
                  <span
                    style={{
                      fontSize: 12,
                      color: "var(--text-2)",
                      fontFamily: "var(--font-ui)",
                    }}
                  >
                    {label}
                  </span>
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: active ? "var(--green)" : "var(--text-3)",
                      textTransform: "uppercase",
                      fontWeight: 700,
                    }}
                  >
                    {active ? "ON" : "OFF"}
                  </span>
                </div>
              ))}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
