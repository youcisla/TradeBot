"use client";

import { useEffect, useMemo, useState } from "react";
import { formatShort } from "@/lib/time";
import PaginationControls from "@/components/PaginationControls";

interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2?: number;
  take_profit_3?: number;
  tp1_hit?: boolean;
  tp2_hit?: boolean;
  tp3_hit?: boolean;
  status: string;
  pnl: number;
  open_time: string;
  current_price?: number;
}

interface OpenTradesTableProps {
  trades: Trade[];
  onClose?: (id: string) => void;
}

function fmtPrice(price: number): string {
  if (!price || price === 0) return "—";
  if (price >= 1000) return price.toFixed(2);
  if (price >= 100) return price.toFixed(2);
  if (price >= 1) return price.toFixed(4);
  return price.toFixed(5);
}

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO =
  `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

export default function OpenTradesTable({ trades, onClose }: OpenTradesTableProps) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const filteredTrades = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return trades;

    return trades.filter((trade) => {
      const haystack = [
        trade.symbol,
        trade.direction,
        trade.strategy,
        trade.status,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [trades, search]);

  const totalPages = Math.max(1, Math.ceil(filteredTrades.length / pageSize));

  useEffect(() => {
    setPage((prev) => Math.min(prev, totalPages));
  }, [totalPages]);

  useEffect(() => {
    setPage(1);
  }, [search, pageSize]);

  const pagedTrades = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredTrades.slice(start, start + pageSize);
  }, [filteredTrades, page, pageSize]);

  if (trades.length === 0) {
    return (
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "48px 24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
        }}
      >
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 40, color: "rgba(235,235,245,0.3)" }}
        >
          shield
        </span>
        <span
          style={{
            fontFamily: FONT,
            fontSize: 15,
            color: "rgba(235,235,245,0.3)",
          }}
        >
          No open positions
        </span>
      </div>
    );
  }

  const HEADERS = [
    "Symbol", "Direction", "Entry", "Current", "SL", "TP", "PnL", "Lot", "Time", "",
  ];

  return (
    <div
      style={{
        background: "#1C1C1E",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "12px 12px 0" }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter open trades..."
          style={{
            width: "100%",
            height: 34,
            borderRadius: 10,
            border: "1px solid rgba(84,84,88,0.65)",
            background: "rgba(118,118,128,0.2)",
            color: "#FFFFFF",
            padding: "0 12px",
            fontSize: 13,
            fontWeight: 500,
            fontFamily: FONT,
            outline: "none",
          }}
        />
      </div>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontFamily: FONT,
          }}
        >
          <thead>
            <tr>
              {HEADERS.map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "12px 16px",
                    textAlign: h === "PnL" || h === "Entry" || h === "Current" || h === "SL" ? "right" : "left",
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "rgba(235,235,245,0.3)",
                    borderBottom: "0.5px solid rgba(84,84,88,0.65)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagedTrades.map((trade, idx) => {
              const pnl = Number(trade.pnl);
              const pnlPositive = pnl >= 0;
              const isLast = idx === pagedTrades.length - 1;

              return (
                <tr key={trade.id}>
                  {/* Symbol */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 15,
                      fontWeight: 700,
                      color: "#FFFFFF",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                      whiteSpace: "nowrap",
                      minHeight: 52,
                    }}
                  >
                    {trade.symbol}
                  </td>

                  {/* Direction */}
                  <td
                    style={{
                      padding: "14px 16px",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    <span
                      style={{
                        display: "inline-block",
                        padding: "3px 10px",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        background:
                          trade.direction === "BUY"
                            ? "rgba(10,132,255,0.18)"
                            : "rgba(255,69,58,0.18)",
                        color:
                          trade.direction === "BUY" ? "#0A84FF" : "#FF453A",
                      }}
                    >
                      {trade.direction}
                    </span>
                  </td>

                  {/* Entry */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      fontFamily: MONO,
                      color: "rgba(235,235,245,0.6)",
                      textAlign: "right",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {fmtPrice(Number(trade.entry_price))}
                  </td>

                  {/* Current */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      fontFamily: MONO,
                      color: "#FFFFFF",
                      textAlign: "right",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {trade.current_price ? fmtPrice(Number(trade.current_price)) : "—"}
                  </td>

                  {/* SL */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      fontFamily: MONO,
                      color: "#FF453A",
                      textAlign: "right",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {fmtPrice(Number(trade.stop_loss))}
                  </td>

                  {/* TP dots */}
                  <td
                    style={{
                      padding: "14px 16px",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                      {[trade.tp1_hit, trade.tp2_hit, trade.tp3_hit].map((hit, i) => (
                        <div
                          key={i}
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background: hit ? "#30D158" : "#3A3A3C",
                          }}
                        />
                      ))}
                    </div>
                  </td>

                  {/* PnL */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      fontFamily: MONO,
                      fontWeight: 700,
                      color: pnlPositive ? "#30D158" : "#FF453A",
                      textAlign: "right",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {pnlPositive ? "+" : ""}${pnl.toFixed(2)}
                  </td>

                  {/* Lot */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      color: "rgba(235,235,245,0.6)",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {trade.lot_size}
                  </td>

                  {/* Time */}
                  <td
                    style={{
                      padding: "14px 16px",
                      fontSize: 13,
                      color: "rgba(235,235,245,0.3)",
                      whiteSpace: "nowrap",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {formatShort(trade.open_time)}
                  </td>

                  {/* Close button */}
                  <td
                    style={{
                      padding: "14px 16px",
                      textAlign: "right",
                      borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                    }}
                  >
                    {onClose && (
                      <button
                        onClick={() => onClose(trade.id)}
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: "50%",
                          background: "rgba(255,69,58,0.15)",
                          border: "none",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#FF453A",
                          transition: "background 0.15s",
                        }}
                        onMouseEnter={(e) => {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            "rgba(255,69,58,0.3)";
                        }}
                        onMouseLeave={(e) => {
                          (e.currentTarget as HTMLButtonElement).style.background =
                            "rgba(255,69,58,0.15)";
                        }}
                        title="Close trade"
                      >
                        <span
                          className="material-symbols-outlined"
                          style={{ fontSize: 16 }}
                        >
                          close
                        </span>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {filteredTrades.length > 0 && (
        <div style={{ padding: "0 12px 12px" }}>
          <PaginationControls
            page={page}
            totalItems={filteredTrades.length}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            label="open trades"
          />
        </div>
      )}
    </div>
  );
}
