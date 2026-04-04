"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { formatShort } from "@/lib/time";
import OpenTradesTable from "@/components/OpenTradesTable";
import SymbolFilter from "@/components/SymbolFilter";
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
  open_time: string;
  close_time?: string;
  pnl: number;
  current_price?: number;
  close_reason?: string;
}

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO =
  `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

function fmtPrice(price: number): string {
  if (!price || price === 0) return "—";
  if (price >= 1000) return price.toFixed(2);
  if (price >= 100) return price.toFixed(2);
  if (price >= 1) return price.toFixed(4);
  return price.toFixed(5);
}

interface SummaryCardProps {
  label: string;
  value: string;
  sub?: string;
  color: string;
}

function SummaryCard({ label, value, sub, color }: SummaryCardProps) {
  return (
    <div
      style={{
        flex: 1,
        background: "#1C1C1E",
        borderRadius: 12,
        padding: "16px 20px",
        minWidth: 0,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 12,
          color: "rgba(235,235,245,0.6)",
          marginBottom: 8,
          fontWeight: 500,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 22,
          fontWeight: 700,
          color,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: FONT,
            fontSize: 12,
            color: "rgba(235,235,245,0.3)",
            marginTop: 4,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

export default function TradesPage() {
  const [openTrades, setOpenTrades] = useState<Trade[]>([]);
  const [history, setHistory] = useState<Trade[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [historySearch, setHistorySearch] = useState("");
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize, setHistoryPageSize] = useState(10);
  const [closedExpanded, setClosedExpanded] = useState(false);
  const [todayPnl, setTodayPnl] = useState(0);

  const loadOpen = useCallback(() => {
    fetch("/api/trades")
      .then((r) => r.json())
      .then((data: Trade[]) => {
        if (Array.isArray(data)) setOpenTrades(data.filter((t) => t.status === "OPEN"));
      })
      .catch(() => {});
  }, []);

  const loadHistory = useCallback(() => {
    fetch("/api/trades?all=true&limit=50")
      .then((r) => r.json())
      .then((data: Trade[]) => {
        if (Array.isArray(data)) {
          const closed = data.filter((t) => t.status === "CLOSED");
          setHistory(closed);
          const today = new Date().toISOString().slice(0, 10);
          const tpnl = closed
            .filter((t) => (t.close_time ?? "").startsWith(today))
            .reduce((sum, t) => sum + Number(t.pnl), 0);
          setTodayPnl(tpnl);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadOpen();
    loadHistory();
    const id = setInterval(loadOpen, 5_000);
    return () => clearInterval(id);
  }, [loadOpen, loadHistory]);

  const closeTrade = useCallback(async (id: string) => {
    await fetch("/api/commands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: "close_trade", payload: { trade_id: id } }),
    });
    loadOpen();
  }, [loadOpen]);

  const unrealizedPnl = useMemo(
    () => openTrades.reduce((sum, t) => sum + Number(t.pnl), 0),
    [openTrades]
  );

  const allSymbols = useMemo(() => {
    const set = new Set([
      ...openTrades.map((t) => t.symbol),
      ...history.map((t) => t.symbol),
    ]);
    return Array.from(set).sort();
  }, [openTrades, history]);

  const filteredOpen = useMemo(
    () =>
      selectedSymbol
        ? openTrades.filter((t) => t.symbol === selectedSymbol)
        : openTrades,
    [openTrades, selectedSymbol]
  );

  const filteredHistory = useMemo(
    () =>
      selectedSymbol
        ? history.filter((t) => t.symbol === selectedSymbol)
        : history,
    [history, selectedSymbol]
  );

  const filteredHistoryBySearch = useMemo(() => {
    const query = historySearch.trim().toLowerCase();
    if (!query) return filteredHistory;

    return filteredHistory.filter((trade) => {
      const haystack = [
        trade.symbol,
        trade.direction,
        trade.strategy,
        trade.close_reason ?? "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [filteredHistory, historySearch]);

  const pagedHistory = useMemo(() => {
    const start = (historyPage - 1) * historyPageSize;
    return filteredHistoryBySearch.slice(start, start + historyPageSize);
  }, [filteredHistoryBySearch, historyPage, historyPageSize]);

  useEffect(() => {
    setHistoryPage(1);
  }, [historySearch, historyPageSize, selectedSymbol]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredHistoryBySearch.length / historyPageSize));
    setHistoryPage((prev) => Math.min(prev, totalPages));
  }, [filteredHistoryBySearch.length, historyPageSize]);

  return (
    <div
      style={{
        fontFamily: FONT,
        paddingTop: 20,
        paddingLeft: 20,
        paddingRight: 20,
        paddingBottom: 40,
        maxWidth: 1400,
        margin: "0 auto",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 28,
            fontWeight: 700,
            color: "#FFFFFF",
            margin: 0,
            marginBottom: 4,
          }}
        >
          Trades
        </h1>
        <div
          style={{
            fontSize: 15,
            color: "rgba(235,235,245,0.6)",
          }}
        >
          {openTrades.length === 0
            ? "No open positions"
            : `${openTrades.length} open position${openTrades.length !== 1 ? "s" : ""}`}
        </div>
      </div>

      {/* Summary Row */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 24,
          flexWrap: "wrap",
        }}
      >
        <SummaryCard
          label="Open Positions"
          value={String(openTrades.length)}
          color="#0A84FF"
        />
        <SummaryCard
          label="Unrealized PnL"
          value={`${unrealizedPnl >= 0 ? "+" : ""}$${unrealizedPnl.toFixed(2)}`}
          color={unrealizedPnl >= 0 ? "#30D158" : "#FF453A"}
          sub="across all open trades"
        />
        <SummaryCard
          label="Today's PnL"
          value={`${todayPnl >= 0 ? "+" : ""}$${todayPnl.toFixed(2)}`}
          color={todayPnl >= 0 ? "#30D158" : "#FF453A"}
          sub="from closed trades today"
        />
      </div>

      {/* Symbol Filter */}
      {allSymbols.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <SymbolFilter
            symbols={allSymbols}
            selected={selectedSymbol}
            onSelect={setSelectedSymbol}
          />
        </div>
      )}

      {/* Open Trades */}
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 12,
          }}
        >
          Open Positions
        </div>
        <OpenTradesTable trades={filteredOpen} onClose={closeTrade} />
      </div>

      {/* Recent Closed Trades — collapsible */}
      <div>
        <button
          onClick={() => setClosedExpanded((v) => !v)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
            marginBottom: 12,
            fontFamily: FONT,
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{
              fontSize: 16,
              color: "rgba(235,235,245,0.3)",
              transform: closedExpanded ? "rotate(90deg)" : "rotate(0deg)",
              transition: "transform 0.2s",
            }}
          >
            chevron_right
          </span>
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "rgba(235,235,245,0.6)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Recent Closed ({filteredHistoryBySearch.length})
          </span>
        </button>

        {closedExpanded && (
          <div
            style={{
              background: "#1C1C1E",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: "12px 12px 0" }}>
              <input
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                placeholder="Filter closed trades..."
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

            {filteredHistoryBySearch.length === 0 ? (
              <div
                style={{
                  padding: "40px 24px",
                  textAlign: "center",
                  color: "rgba(235,235,245,0.3)",
                  fontSize: 15,
                }}
              >
                No closed trades
              </div>
            ) : (
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
                      {[
                        "Symbol", "Direction", "Entry", "SL", "PnL", "Lot",
                        "Close Time", "Reason",
                      ].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "12px 16px",
                            textAlign:
                              h === "PnL" || h === "Entry" || h === "SL"
                                ? "right"
                                : "left",
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
                    {pagedHistory.map((t, idx) => {
                      const pnl = Number(t.pnl);
                      const isLast = idx === pagedHistory.length - 1;
                      return (
                        <tr key={t.id}>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 15,
                              fontWeight: 700,
                              color: "#FFFFFF",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {t.symbol}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
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
                                  t.direction === "BUY"
                                    ? "rgba(10,132,255,0.18)"
                                    : "rgba(255,69,58,0.18)",
                                color:
                                  t.direction === "BUY" ? "#0A84FF" : "#FF453A",
                              }}
                            >
                              {t.direction}
                            </span>
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              fontFamily: MONO,
                              color: "rgba(235,235,245,0.6)",
                              textAlign: "right",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {fmtPrice(Number(t.entry_price))}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              fontFamily: MONO,
                              color: "#FF453A",
                              textAlign: "right",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {fmtPrice(Number(t.stop_loss))}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              fontFamily: MONO,
                              fontWeight: 700,
                              color: pnl >= 0 ? "#30D158" : "#FF453A",
                              textAlign: "right",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              color: "rgba(235,235,245,0.6)",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {t.lot_size}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              color: "rgba(235,235,245,0.3)",
                              whiteSpace: "nowrap",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {t.close_time ? formatShort(t.close_time) : "—"}
                          </td>
                          <td
                            style={{
                              padding: "13px 16px",
                              fontSize: 13,
                              color: "rgba(235,235,245,0.3)",
                              borderBottom: isLast
                                ? "none"
                                : "0.5px solid rgba(84,84,88,0.3)",
                            }}
                          >
                            {t.close_reason || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {filteredHistoryBySearch.length > 0 && (
              <div style={{ padding: "0 12px 12px" }}>
                <PaginationControls
                  page={historyPage}
                  totalItems={filteredHistoryBySearch.length}
                  pageSize={historyPageSize}
                  onPageChange={setHistoryPage}
                  onPageSizeChange={setHistoryPageSize}
                  label="closed trades"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
