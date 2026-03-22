"use client";

import { useEffect, useState } from "react";
import { formatShort } from "@/lib/time";

interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  status: string;
  pnl: number;
  open_time: string;
}

export default function OpenTradesTable({ symbol }: { symbol?: string | null }) {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/trades")
        .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
        .then((data) => { if (active) setTrades(data); })
        .catch(() => {});
    load();
    const id = setInterval(load, 15_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  async function closeTrade(tradeId: string) {
    await fetch("/api/commands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: "close_trade", payload: { trade_id: tradeId } }),
    });
  }

  const filtered = symbol ? trades.filter((t) => t.symbol === symbol) : trades;

  if (filtered.length === 0) {
    return (
      <div style={{
        background: "#0a0a12", border: "1px solid #1c1c28",
        borderRadius: 8, padding: "20px 24px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11, color: "#1e2e1e",
        textAlign: "center",
      }}>
        {symbol ? `No open trades for ${symbol}.` : "No open positions."}
      </div>
    );
  }

  return (
    <div style={{
      background: "#0e0e10", border: "1px solid #1c1c28",
      borderRadius: 8, overflow: "auto",
    }}>
      <table style={{
        width: "100%", borderCollapse: "collapse",
        fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
      }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #1c1c28" }}>
            {["Symbol","Dir","Strategy","Entry","Lots","SL","TP1","PnL","Status","Opened",""].map((h) => (
              <th key={h} style={{
                padding: "9px 10px",
                textAlign: h === "Entry" || h === "Lots" || h === "SL" || h === "TP1" || h === "PnL" ? "right" : "left",
                fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                color: "#2a3a4a", fontWeight: 600, whiteSpace: "nowrap",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((t) => {
            const pnl = Number(t.pnl);
            return (
              <tr
                key={t.id}
                style={{ borderBottom: "1px solid rgba(28,28,40,0.5)", transition: "background 0.1s" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,255,65,0.02)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
              >
                <td style={{ padding: "7px 10px", color: "#00d4ff", fontWeight: 700 }}>{t.symbol}</td>
                <td style={{ padding: "7px 10px" }}>
                  <span style={{
                    display: "inline-block", padding: "1px 7px", borderRadius: 3,
                    fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                    background: t.direction === "BUY" ? "rgba(0,255,136,0.12)" : "rgba(255,68,85,0.12)",
                    color: t.direction === "BUY" ? "#00ff88" : "#ff4455",
                    border: `1px solid ${t.direction === "BUY" ? "rgba(0,255,136,0.3)" : "rgba(255,68,85,0.3)"}`,
                  }}>
                    {t.direction}
                  </span>
                </td>
                <td style={{ padding: "7px 10px", color: "#4a5568", fontSize: 9.5 }}>{t.strategy}</td>
                <td style={{ padding: "7px 10px", textAlign: "right", color: "#9aa8b8", fontFamily: "monospace" }}>
                  {Number(t.entry_price).toFixed(5)}
                </td>
                <td style={{ padding: "7px 10px", textAlign: "right", color: "#7a8a9a" }}>{t.lot_size}</td>
                <td style={{ padding: "7px 10px", textAlign: "right", color: "#ff4455", fontFamily: "monospace" }}>
                  {Number(t.stop_loss).toFixed(5)}
                </td>
                <td style={{ padding: "7px 10px", textAlign: "right", color: "#2a3a4a", fontFamily: "monospace" }}>
                  {Number(t.take_profit_1).toFixed(5)}
                </td>
                <td style={{
                  padding: "7px 10px", textAlign: "right",
                  fontWeight: 700, color: pnl >= 0 ? "#00ff88" : "#ff4455",
                  textShadow: pnl > 0 ? "0 0 8px rgba(0,255,136,0.4)" : pnl < 0 ? "0 0 8px rgba(255,68,85,0.4)" : "none",
                }}>
                  {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                </td>
                <td style={{ padding: "7px 10px" }}>
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: 4,
                    fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                    color: t.status === "OPEN" ? "#00ff41" : "#f5c518",
                  }}>
                    <span style={{
                      width: 5, height: 5, borderRadius: "50%",
                      background: t.status === "OPEN" ? "#00ff41" : "#f5c518",
                      boxShadow: `0 0 4px ${t.status === "OPEN" ? "#00ff41" : "#f5c518"}`,
                    }} />
                    {t.status}
                  </span>
                </td>
                <td style={{ padding: "7px 10px", color: "#2a3a4a", fontSize: 9.5, whiteSpace: "nowrap" }}>
                  {formatShort(t.open_time)}
                </td>
                <td style={{ padding: "7px 10px", textAlign: "right" }}>
                  <button
                    onClick={() => closeTrade(t.id)}
                    style={{
                      padding: "3px 10px",
                      background: "rgba(255,68,85,0.08)",
                      border: "1px solid rgba(255,68,85,0.3)",
                      borderRadius: 3,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
                      color: "#ff4455",
                      cursor: "pointer",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,68,85,0.2)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,68,85,0.08)"; }}
                  >
                    CLOSE
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
