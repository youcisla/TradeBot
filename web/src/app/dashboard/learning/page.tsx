"use client";

import { useEffect, useState, useMemo } from "react";
import SymbolFilter from "@/components/SymbolFilter";
import PaginationControls from "@/components/PaginationControls";

interface StrategyConfidence {
  strategy: string;
  confidence: number;
  total_trades: number;
  total_score: number;
  last_updated: string;
}

interface TradeScore {
  id: number;
  trade_id: string;
  strategy: string;
  symbol: string;
  session: string;
  market_condition: string;
  score: number;
  pnl: number;
  created_at: string;
}

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO =
  `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

function formatStrategy(raw: string): string {
  const model = raw.includes(":") ? raw.split(":").pop()! : raw;
  return model.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function confBarColor(conf: number): string {
  if (conf > 0.7) return "#30D158";
  if (conf > 0.4) return "#FF9F0A";
  return "#FF453A";
}

function scoreColor(score: number): string {
  if (score > 0) return "#30D158";
  if (score < 0) return "#FF453A";
  return "rgba(235,235,245,0.3)";
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export default function LearningPage() {
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [scores, setScores] = useState<TradeScore[]>([]);
  const [symbolFilter, setSymbolFilter] = useState<string | null>(null);
  const [scoreSearch, setScoreSearch] = useState("");
  const [scorePage, setScorePage] = useState(1);
  const [scorePageSize, setScorePageSize] = useState(10);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/learning")
        .then((r) => r.json())
        .then((data) => {
          if (!active) return;
          setConfidences(data.confidences ?? []);
          setScores(data.scores ?? []);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 15_000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const allSymbols = useMemo(
    () => Array.from(new Set(scores.map((s) => s.symbol))).filter(Boolean).sort(),
    [scores]
  );

  const filteredScores = useMemo(
    () => (symbolFilter ? scores.filter((s) => s.symbol === symbolFilter) : scores),
    [scores, symbolFilter]
  );

  const filteredScoresBySearch = useMemo(() => {
    const query = scoreSearch.trim().toLowerCase();
    if (!query) return filteredScores;
    return filteredScores.filter((score) => {
      const haystack = [
        score.symbol,
        score.strategy,
        score.session,
        score.market_condition,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [filteredScores, scoreSearch]);

  const pagedScores = useMemo(() => {
    const start = (scorePage - 1) * scorePageSize;
    return filteredScoresBySearch.slice(start, start + scorePageSize);
  }, [filteredScoresBySearch, scorePage, scorePageSize]);

  useEffect(() => {
    setScorePage(1);
  }, [scoreSearch, scorePageSize, symbolFilter]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredScoresBySearch.length / scorePageSize));
    setScorePage((prev) => Math.min(prev, totalPages));
  }, [filteredScoresBySearch.length, scorePageSize]);

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
          Insights
        </h1>
        <div style={{ fontSize: 15, color: "rgba(235,235,245,0.6)" }}>
          Confidence trends and trade quality signals
        </div>
      </div>

      {/* Strategy Confidence Cards */}
      <div style={{ marginBottom: 28 }}>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 14,
          }}
        >
          Strategy Confidence
        </div>

        {confidences.length === 0 ? (
          <div
            style={{
              background: "#1C1C1E",
              borderRadius: 12,
              padding: "40px 24px",
              textAlign: "center",
              color: "rgba(235,235,245,0.3)",
              fontSize: 15,
            }}
          >
            No strategies tracked yet
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 12,
            }}
          >
            {confidences.map((c) => {
              const pct = Math.max(0, Math.min(100, Number(c.confidence) * 100));
              const color = confBarColor(Number(c.confidence));
              return (
                <div
                  key={c.strategy}
                  style={{
                    background: "#1C1C1E",
                    borderRadius: 12,
                    padding: "16px 20px",
                  }}
                >
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: "#FFFFFF",
                      marginBottom: 4,
                    }}
                  >
                    {formatStrategy(c.strategy)}
                  </div>

                  {/* Bar */}
                  <div
                    style={{
                      height: 4,
                      background: "rgba(120,120,128,0.36)",
                      borderRadius: 2,
                      marginBottom: 10,
                      marginTop: 10,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${pct}%`,
                        background: color,
                        borderRadius: 2,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "rgba(235,235,245,0.3)",
                      }}
                    >
                      {Number(c.total_trades)} trades · score{" "}
                      {Number(c.total_score) >= 0 ? "+" : ""}
                      {Number(c.total_score)}
                    </div>
                    <div
                      style={{
                        fontSize: 17,
                        fontWeight: 700,
                        fontFamily: MONO,
                        color,
                      }}
                    >
                      {pct.toFixed(0)}%
                    </div>
                  </div>

                  {c.last_updated && (
                    <div
                      style={{
                        fontSize: 11,
                        color: "rgba(235,235,245,0.2)",
                        marginTop: 6,
                      }}
                    >
                      Updated {fmtTime(c.last_updated)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Symbol Filter */}
      {allSymbols.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <SymbolFilter
            symbols={allSymbols}
            selected={symbolFilter}
            onSelect={setSymbolFilter}
          />
        </div>
      )}

      {/* Recent Scores Table */}
      <div>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 14,
          }}
        >
          Recent Scores
        </div>

        <div
          style={{
            background: "#1C1C1E",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "12px 12px 0" }}>
            <input
              value={scoreSearch}
              onChange={(e) => setScoreSearch(e.target.value)}
              placeholder="Filter scores..."
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

          {filteredScoresBySearch.length === 0 ? (
            <div
              style={{
                padding: "40px 24px",
                textAlign: "center",
                color: "rgba(235,235,245,0.3)",
                fontSize: 15,
              }}
            >
              {symbolFilter ? `No scores for ${symbolFilter}` : "No scores recorded yet"}
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
                    {["Strategy", "Symbol", "Session", "Score", "PnL", "Date"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "12px 16px",
                          textAlign:
                            h === "Score" || h === "PnL" ? "right" : "left",
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
                  {pagedScores.map((s, idx) => {
                    const isLast = idx === pagedScores.length - 1;
                    const sc = Number(s.score);
                    const pnl = Number(s.pnl);
                    return (
                      <tr key={s.id}>
                        <td
                          style={{
                            padding: "13px 16px",
                            fontSize: 14,
                            color: "rgba(235,235,245,0.6)",
                            borderBottom: isLast
                              ? "none"
                              : "0.5px solid rgba(84,84,88,0.3)",
                          }}
                        >
                          {formatStrategy(s.strategy)}
                        </td>
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
                          {s.symbol}
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
                          {s.session || "—"}
                        </td>
                        <td
                          style={{
                            padding: "13px 16px",
                            fontSize: 14,
                            fontFamily: MONO,
                            fontWeight: 700,
                            color: scoreColor(sc),
                            textAlign: "right",
                            borderBottom: isLast
                              ? "none"
                              : "0.5px solid rgba(84,84,88,0.3)",
                          }}
                        >
                          {sc >= 0 ? "+" : ""}
                          {sc}
                        </td>
                        <td
                          style={{
                            padding: "13px 16px",
                            fontSize: 14,
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
                            color: "rgba(235,235,245,0.3)",
                            whiteSpace: "nowrap",
                            borderBottom: isLast
                              ? "none"
                              : "0.5px solid rgba(84,84,88,0.3)",
                          }}
                        >
                          {fmtTime(s.created_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {filteredScoresBySearch.length > 0 && (
            <div style={{ padding: "0 12px 12px" }}>
              <PaginationControls
                page={scorePage}
                totalItems={filteredScoresBySearch.length}
                pageSize={scorePageSize}
                onPageChange={setScorePage}
                onPageSizeChange={setScorePageSize}
                label="scores"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
