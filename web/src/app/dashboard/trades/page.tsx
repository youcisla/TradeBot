"use client";

import { useEffect, useState } from "react";
import { formatShort } from "@/lib/time";
import { formatPrice } from "@/lib/formatPrice";
import SymbolFilter from "@/components/SymbolFilter";
import PageHeader from "@/components/PageHeader";

interface Trade {
  id: string; symbol: string; strategy: string; direction: string;
  entry_price: number; lot_size: number; stop_loss: number;
  take_profit_1: number; take_profit_2: number; take_profit_3: number;
  tp1_hit: boolean; tp2_hit: boolean; tp3_hit: boolean;
  status: string; open_time: string; close_time: string | null;
  pnl: number; close_reason: string;
}

function TpDot({ hit, label }: { hit: boolean; label: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 3,
      fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
      color: hit ? "#00ff88" : "#607888",
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: "50%",
        background: hit ? "#00ff88" : "#1c1c28",
        boxShadow: hit ? "0 0 4px #00ff88" : undefined,
      }} />
      {label}
    </span>
  );
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [symbol, setSymbol] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/trades?all=true")
      .then((r) => r.json())
      .then(setTrades)
      .catch(() => {});
  }, []);

  const filtered = symbol ? trades.filter((t) => t.symbol === symbol) : trades;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

      <PageHeader subsystem="History" title="All Trades" accent="#00ff88" />

      <SymbolFilter value={symbol} onChange={setSymbol} />

      {/* Summary strip */}
      {filtered.length > 0 && (() => {
        const closed   = filtered.filter((t) => t.status === "CLOSED");
        const wins     = closed.filter((t) => Number(t.pnl) > 0).length;
        const totalPnl = closed.reduce((s, t) => s + Number(t.pnl), 0);
        return (
          <div style={{
            display: "flex", gap: 20, padding: "10px 16px",
            background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 6,
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            <span style={{ fontSize: 10, color: "#607888" }}>
              {filtered.length} trades
            </span>
            <span style={{ fontSize: 10, color: "#607888" }}>
              {closed.length} closed · {wins} wins
            </span>
            <span style={{
              fontSize: 10, fontWeight: 700,
              color: totalPnl >= 0 ? "#00ff88" : "#ff4455",
            }}>
              Net: {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
            </span>
          </div>
        );
      })()}

      {/* Table */}
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
              {["ID","Symbol","Dir","Strategy","Entry","Lots","P&L","Status","SL","TPs","Opened","Closed","Reason"].map((h) => (
                <th key={h} style={{
                  padding: "9px 10px",
                  textAlign: h === "Entry" || h === "Lots" || h === "P&L" ? "right" : "left",
                  fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                  color: "#607888", fontWeight: 600, whiteSpace: "nowrap",
                }}>
                  {h}
                </th>
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
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,212,255,0.03)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                >
                  <td style={{ padding: "7px 10px", color: "#607888", fontSize: 9.5 }}>
                    {t.id.slice(0, 8)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#00d4ff", fontWeight: 700 }}>
                    {t.symbol}
                  </td>
                  <td style={{ padding: "7px 10px" }}>
                    <span style={{
                      display: "inline-block",
                      padding: "1px 7px", borderRadius: 3,
                      fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                      background: t.direction === "BUY" ? "rgba(0,255,136,0.12)" : "rgba(255,68,85,0.12)",
                      color: t.direction === "BUY" ? "#00ff88" : "#ff4455",
                      border: `1px solid ${t.direction === "BUY" ? "rgba(0,255,136,0.3)" : "rgba(255,68,85,0.3)"}`,
                    }}>
                      {t.direction}
                    </span>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#7a8a9a", fontSize: 9.5 }}>
                    {t.strategy}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: "#9aa8b8" }}>
                    {Number(t.entry_price).toFixed(5)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: "#7a8a9a" }}>
                    {t.lot_size}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", fontWeight: 700, color: pnl >= 0 ? "#00ff88" : "#ff4455" }}>
                    {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                  </td>
                  <td style={{ padding: "7px 10px" }}>
                    <span style={{
                      fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                      color: t.status === "CLOSED" ? "#607888" : t.status === "OPEN" ? "#00ff88" : "#f5c518",
                    }}>
                      {t.status}
                    </span>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#ff4455", fontSize: 9.5 }}>
                    {formatPrice(t.stop_loss)}
                  </td>
                  <td style={{ padding: "7px 10px" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <TpDot hit={t.tp1_hit} label="TP1" />
                      <TpDot hit={t.tp2_hit} label="TP2" />
                      <TpDot hit={t.tp3_hit} label="TP3" />
                    </div>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#607888", fontSize: 9.5, whiteSpace: "nowrap" }}>
                    {formatShort(t.open_time)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#607888", fontSize: 9.5, whiteSpace: "nowrap" }}>
                    {t.close_time ? formatShort(t.close_time) : "—"}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#7a8a9a", fontSize: 9.5 }}>
                    {t.close_reason || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div style={{
            padding: "40px 20px", textAlign: "center",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            color: "#3a5248",
          }}>
            {symbol ? `no trades for ${symbol}` : "no trades recorded yet"}
          </div>
        )}
      </div>
    </div>
  );
}
