"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import EquityCurve from "@/components/EquityCurve";
import SymbolFilter from "@/components/SymbolFilter";
import PaginationControls from "@/components/PaginationControls";

interface SymbolStat {
  symbol: string;
  total: number;
  wins: number;
  losses: number;
  total_pnl: number;
  avg_pnl: number;
}

interface DayPnl {
  day: string;
  pnl: number;
  trades: number;
}

interface Kpis {
  total_trades: number;
  wins: number;
  losses: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade: number;
  worst_trade: number;
  avg_duration_min: number;
}

type Period = "1D" | "1W" | "1M" | "3M" | "All";

const FONT =
  `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO =
  `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

function sinceDate(p: Period): string | undefined {
  if (p === "All") return undefined;
  const d = new Date();
  if (p === "1D") d.setDate(d.getDate() - 1);
  else if (p === "1W") d.setDate(d.getDate() - 7);
  else if (p === "1M") d.setMonth(d.getMonth() - 1);
  else d.setMonth(d.getMonth() - 3);
  return d.toISOString();
}

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}

function KpiCard({ label, value, sub, color = "#FFFFFF" }: KpiCardProps) {
  return (
    <div
      style={{
        background: "#1C1C1E",
        borderRadius: 12,
        padding: 16,
        minWidth: 130,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: "rgba(235,235,245,0.6)",
          marginBottom: 8,
          fontWeight: 500,
          fontFamily: FONT,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 20,
          fontWeight: 700,
          color,
          fontFamily: MONO,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: 12,
            color: "rgba(235,235,245,0.3)",
            marginTop: 4,
            fontFamily: FONT,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

interface BarTooltipProps {
  active?: boolean;
  payload?: { value?: number }[];
  label?: string;
}

function DailyTooltip({ active, payload, label }: BarTooltipProps) {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value ?? 0;
  return (
    <div
      style={{
        background: "#2C2C2E",
        borderRadius: 8,
        padding: "8px 12px",
        fontFamily: FONT,
        fontSize: 12,
        color: "#FFFFFF",
        boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
      }}
    >
      <div style={{ color: "rgba(235,235,245,0.6)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontWeight: 700, color: Number(val) >= 0 ? "#30D158" : "#FF453A" }}>
        {Number(val) >= 0 ? "+" : ""}${Number(val).toFixed(2)}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>("All");
  const [symbolFilter, setSymbolFilter] = useState<string | null>(null);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [dailyPnl, setDailyPnl] = useState<DayPnl[]>([]);
  const [symbolStats, setSymbolStats] = useState<SymbolStat[]>([]);
  const [tableSearch, setTableSearch] = useState("");
  const [tablePage, setTablePage] = useState(1);
  const [tablePageSize, setTablePageSize] = useState(10);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const since = sinceDate(period);
    const params = new URLSearchParams();
    if (since) params.set("since", since);
    if (symbolFilter) params.set("symbol", symbolFilter);
    const qs = params.toString() ? `?${params.toString()}` : "";
    fetch(`/api/analytics${qs}`)
      .then((r) => r.json())
      .then((d) => {
        setKpis(d.kpis ?? null);
        setDailyPnl(d.dailyPnl ?? []);
        setSymbolStats(d.symbolStats ?? []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period, symbolFilter]);

  useEffect(() => { load(); }, [load]);

  const winRate = kpis && kpis.total_trades > 0
    ? (kpis.wins / kpis.total_trades) * 100
    : 0;
  const winRateColor =
    winRate >= 55 ? "#30D158" : winRate >= 45 ? "#FF9F0A" : "#FF453A";

  const equityCurveData = useMemo(() => dailyPnl.map((d) => ({ day: d.day, pnl: d.pnl })), [dailyPnl]);

  const allSymbols = useMemo(
    () => symbolStats.map((s) => s.symbol).sort(),
    [symbolStats]
  );

  const filteredSymbolStats = useMemo(() => {
    const query = tableSearch.trim().toLowerCase();
    if (!query) return symbolStats;
    return symbolStats.filter((stat) => stat.symbol.toLowerCase().includes(query));
  }, [symbolStats, tableSearch]);

  const pagedSymbolStats = useMemo(() => {
    const start = (tablePage - 1) * tablePageSize;
    return filteredSymbolStats.slice(start, start + tablePageSize);
  }, [filteredSymbolStats, tablePage, tablePageSize]);

  useEffect(() => {
    setTablePage(1);
  }, [tableSearch, tablePageSize, symbolFilter]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredSymbolStats.length / tablePageSize));
    setTablePage((prev) => Math.min(prev, totalPages));
  }, [filteredSymbolStats.length, tablePageSize]);

  const PERIODS: Period[] = ["1D", "1W", "1M", "3M", "All"];

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
      <div style={{ marginBottom: 24, display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
          Performance
        </h1>
        {loading && (
          <span style={{ fontSize: 13, color: "rgba(235,235,245,0.3)" }}>
            Loading...
          </span>
        )}
      </div>

      {/* Period Selector */}
      <div
        style={{
          display: "inline-flex",
          background: "rgba(118,118,128,0.24)",
          borderRadius: 10,
          padding: 2,
          marginBottom: 24,
          gap: 2,
        }}
      >
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            style={{
              padding: "6px 16px",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: FONT,
              background: period === p ? "#2C2C2E" : "transparent",
              color: period === p ? "#FFFFFF" : "rgba(235,235,245,0.6)",
              transition: "background 0.15s, color 0.15s",
            }}
          >
            {p}
          </button>
        ))}
      </div>

      {/* KPI Cards Row */}
      {kpis && (
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 24,
            overflowX: "auto",
            paddingBottom: 4,
            scrollbarWidth: "none",
          }}
        >
          <KpiCard
            label="Win Rate"
            value={`${winRate.toFixed(1)}%`}
            sub={`${kpis.wins}W / ${kpis.losses}L`}
            color={winRateColor}
          />
          <KpiCard
            label="Total PnL"
            value={`${Number(kpis.total_pnl) >= 0 ? "+" : ""}$${Number(kpis.total_pnl).toFixed(2)}`}
            color={Number(kpis.total_pnl) >= 0 ? "#30D158" : "#FF453A"}
          />
          <KpiCard
            label="Best Trade"
            value={`+$${Number(kpis.best_trade).toFixed(2)}`}
            color="#30D158"
          />
          <KpiCard
            label="Worst Trade"
            value={`$${Number(kpis.worst_trade).toFixed(2)}`}
            color="#FF453A"
          />
          <KpiCard
            label="Avg Duration"
            value={`${Math.floor(Number(kpis.avg_duration_min))}m`}
            sub="per trade"
            color="rgba(235,235,245,0.6)"
          />
          <KpiCard
            label="Total Trades"
            value={String(kpis.total_trades)}
            color="rgba(235,235,245,0.6)"
          />
        </div>
      )}

      {/* Symbol Filter */}
      {allSymbols.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <SymbolFilter
            symbols={allSymbols}
            selected={symbolFilter}
            onSelect={setSymbolFilter}
          />
        </div>
      )}

      {/* Equity Curve */}
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "16px 20px",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 12,
          }}
        >
          Equity Curve
        </div>
        <EquityCurve data={equityCurveData} />
      </div>

      {/* Daily PnL Bar Chart */}
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "16px 20px",
          marginBottom: 20,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            marginBottom: 12,
          }}
        >
          Daily PnL
        </div>
        {dailyPnl.length === 0 ? (
          <div
            style={{
              height: 160,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(235,235,245,0.3)",
              fontSize: 14,
            }}
          >
            No data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={dailyPnl.map((d) => ({ ...d, pnl: Number(d.pnl) }))}>
              <XAxis
                dataKey="day"
                tick={{ fill: "rgba(235,235,245,0.3)", fontSize: 11, fontFamily: FONT }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "rgba(235,235,245,0.3)", fontSize: 11, fontFamily: FONT }}
                axisLine={false}
                tickLine={false}
                width={50}
                tickFormatter={(v: number) => `$${v}`}
              />
              <Tooltip content={<DailyTooltip />} />
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {dailyPnl.map((d, i) => (
                  <Cell
                    key={i}
                    fill={Number(d.pnl) >= 0 ? "#30D158" : "#FF453A"}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Symbol Performance Table */}
      {symbolStats.length > 0 && (
        <div
          style={{
            background: "#1C1C1E",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "16px 20px 12px",
              fontSize: 12,
              fontWeight: 600,
              color: "rgba(235,235,245,0.6)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Symbol Performance
          </div>
          <div style={{ padding: "0 12px 12px" }}>
            <input
              value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)}
              placeholder="Filter symbols..."
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
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontFamily: FONT }}
          >
            <thead>
              <tr style={{ borderTop: "0.5px solid rgba(84,84,88,0.65)" }}>
                {["Symbol", "Win Rate", "Trades", "Total PnL"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 20px",
                      textAlign: h === "Total PnL" ? "right" : "left",
                      fontSize: 11,
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: "rgba(235,235,245,0.3)",
                      borderBottom: "0.5px solid rgba(84,84,88,0.65)",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pagedSymbolStats.map((s, idx) => {
                const wr = s.total > 0 ? (Number(s.wins) / Number(s.total)) * 100 : 0;
                const pnl = Number(s.total_pnl);
                const isLast = idx === pagedSymbolStats.length - 1;
                return (
                  <tr key={s.symbol}>
                    <td
                      style={{
                        padding: "13px 20px",
                        fontSize: 15,
                        fontWeight: 700,
                        color: "#FFFFFF",
                        borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                      }}
                    >
                      {s.symbol}
                    </td>
                    <td
                      style={{
                        padding: "13px 20px",
                        fontSize: 14,
                        fontWeight: 600,
                        color: wr >= 50 ? "#30D158" : "#FF453A",
                        borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                      }}
                    >
                      {wr.toFixed(0)}%
                    </td>
                    <td
                      style={{
                        padding: "13px 20px",
                        fontSize: 14,
                        color: "rgba(235,235,245,0.6)",
                        borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                      }}
                    >
                      {s.total}
                    </td>
                    <td
                      style={{
                        padding: "13px 20px",
                        fontSize: 14,
                        fontFamily: MONO,
                        fontWeight: 700,
                        color: pnl >= 0 ? "#30D158" : "#FF453A",
                        textAlign: "right",
                        borderBottom: isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                      }}
                    >
                      {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filteredSymbolStats.length > 0 && (
            <div style={{ padding: "0 12px 12px" }}>
              <PaginationControls
                page={tablePage}
                totalItems={filteredSymbolStats.length}
                pageSize={tablePageSize}
                onPageChange={setTablePage}
                onPageSizeChange={setTablePageSize}
                label="symbols"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
