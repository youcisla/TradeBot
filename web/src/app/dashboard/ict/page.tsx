"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import SymbolFilter from "@/components/SymbolFilter";
import PaginationControls from "@/components/PaginationControls";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ICTSetup {
  id: number;
  symbol: string;
  direction: string;
  model: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number;
  confidence: number;
  htf_bias: string;
  htf_regime: string;
  premium_discount: string;
  entry_zone: string;
  reason: string;
  confluences: Record<string, unknown>;
  missing: string[];
  session: string;
  executed: boolean;
  created_at: string;
}

interface ModelStat   { model: string; total: number; executed: number; avg_confidence: number; }
interface SessionStat { session: string; total: number; executed: number; avg_confidence: number; }
interface ConfluenceStats {
  total_setups: number; avg_confidence: number;
  htf_aligned: number; swept: number; mss: number;
  displacement: number; fvg: number; ob: number; session_valid: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FONT = `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`;
const MONO = `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`;

const CONFLUENCE_KEYS: [string, string][] = [
  ["htf_bias_aligned",    "HTF Bias"],
  ["liquidity_swept",     "Liquidity"],
  ["mss_confirmed",       "MSS"],
  ["displacement_present","Displacement"],
  ["fvg_present",         "FVG"],
  ["ob_present",          "OB"],
  ["session_valid",       "Session"],
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function confColor(v: number): string {
  if (v >= 70) return "#30D158";
  if (v >= 55) return "#FF9F0A";
  return "#FF453A";
}

function fmtPrice(n: number): string {
  return Number(n).toFixed(5);
}

function fmtTime(iso: string): string {
  try { return new Date(iso).toLocaleString(); } catch { return "—"; }
}

function fmtShortTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return "—"; }
}

// ── Setup Card ────────────────────────────────────────────────────────────────

function SetupCard({ s }: { s: ICTSetup }) {
  const isBuy    = s.direction === "BUY";
  const dirColor = isBuy ? "#0A84FF" : "#FF453A";

  return (
    <div
      style={{
        background:   "#1C1C1E",
        borderRadius: 12,
        padding:      16,
        display:      "flex",
        flexDirection:"column",
        gap:          12,
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", fontFamily: FONT }}>
          {s.symbol}
        </span>

        {/* Direction */}
        <span
          style={{
            background:    `${dirColor}20`,
            border:        `1px solid ${dirColor}`,
            color:         dirColor,
            fontSize:      11,
            fontWeight:    700,
            padding:       "2px 9px",
            borderRadius:  6,
            letterSpacing: "0.06em",
            fontFamily:    FONT,
          }}
        >
          {s.direction}
        </span>

        {/* Session */}
        {s.session && (
          <span
            style={{
              background: "rgba(118,118,128,0.24)",
              color:      "rgba(235,235,245,0.6)",
              fontSize:   11,
              fontWeight: 500,
              padding:    "2px 9px",
              borderRadius: 6,
              fontFamily: FONT,
              textTransform: "capitalize",
            }}
          >
            {s.session}
          </span>
        )}

        {/* Executed */}
        {s.executed && (
          <span
            style={{
              marginLeft:   "auto",
              background:   "rgba(48,209,88,0.15)",
              border:       "1px solid rgba(48,209,88,0.4)",
              color:        "#30D158",
              fontSize:     10,
              fontWeight:   700,
              padding:      "2px 9px",
              borderRadius: 6,
              letterSpacing: "0.08em",
              fontFamily:   FONT,
            }}
          >
            EXECUTED
          </span>
        )}

        {/* Confidence */}
        <span
          style={{
            marginLeft:  s.executed ? 0 : "auto",
            fontSize:    15,
            fontWeight:  700,
            color:       confColor(s.confidence),
            fontFamily:  FONT,
          }}
        >
          {Number(s.confidence).toFixed(0)}%
        </span>
      </div>

      {/* Model footnote */}
      <span
        style={{
          fontSize:   12,
          color:      "#8E8E93",
          fontFamily: FONT,
          marginTop:  -8,
        }}
      >
        {s.model}
      </span>

      {/* Price levels grid */}
      <div
        style={{
          display:             "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap:                 6,
          background:          "#2C2C2E",
          borderRadius:        8,
          padding:             "10px 12px",
        }}
      >
        {[
          { label: "Entry",  value: fmtPrice(s.entry_price),   color: "#FFFFFF" },
          { label: "SL",     value: fmtPrice(s.stop_loss),     color: "#FF453A" },
          { label: "TP1",    value: fmtPrice(s.take_profit_1), color: "#30D158" },
          { label: "TP2",    value: fmtPrice(s.take_profit_2), color: "#30D158" },
          { label: "TP3",    value: fmtPrice(s.take_profit_3), color: "#30D158" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontSize: 10, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>{label}</span>
            <span style={{ fontSize: 11, fontWeight: 600, color, fontFamily: MONO }}>{value}</span>
          </div>
        ))}
      </div>

      {/* Confluences */}
      <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
        {CONFLUENCE_KEYS.map(([key, label]) => {
          const active = Boolean(s.confluences?.[key]);
          return (
            <span
              key={key}
              style={{
                fontSize:     11,
                fontWeight:   500,
                padding:      "3px 8px",
                borderRadius: 6,
                background:   active ? "rgba(48,209,88,0.15)" : "rgba(118,118,128,0.18)",
                color:        active ? "#30D158" : "rgba(235,235,245,0.3)",
                border:       active ? "1px solid rgba(48,209,88,0.35)" : "1px solid rgba(84,84,88,0.3)",
                fontFamily:   FONT,
              }}
            >
              {label}
            </span>
          );
        })}
      </div>

      {/* Missing */}
      {s.missing && s.missing.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: "rgba(235,235,245,0.3)", fontFamily: FONT }}>missing:</span>
          {s.missing.map((m) => (
            <span
              key={m}
              style={{
                fontSize:     11,
                padding:      "2px 7px",
                borderRadius: 5,
                background:   "rgba(118,118,128,0.15)",
                color:        "rgba(235,235,245,0.3)",
                fontFamily:   FONT,
              }}
            >
              {m}
            </span>
          ))}
        </div>
      )}

      {/* Reason */}
      {s.reason && (
        <p
          style={{
            fontSize:   13,
            fontStyle:  "italic",
            color:      "rgba(235,235,245,0.5)",
            margin:     0,
            lineHeight: 1.5,
            fontFamily: FONT,
          }}
        >
          {s.reason}
        </p>
      )}

      {/* Footer: HTF info + timestamp */}
      <div
        style={{
          display:        "flex",
          justifyContent: "space-between",
          alignItems:     "center",
          borderTop:      "0.5px solid rgba(84,84,88,0.3)",
          paddingTop:     8,
          marginTop:      -4,
        }}
      >
        <span style={{ fontSize: 11, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>
          {s.htf_bias && `HTF: ${s.htf_bias}`}
          {s.htf_bias && s.premium_discount && " · "}
          {s.premium_discount && s.premium_discount}
        </span>
        <span style={{ fontSize: 11, color: "rgba(235,235,245,0.3)", fontFamily: MONO }}>
          {fmtShortTime(s.created_at)}
        </span>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ICTPage() {
  const [symbol,    setSymbol]    = useState<string | null>(null);
  const [setups,    setSetups]    = useState<ICTSetup[]>([]);
  const [search,    setSearch]    = useState("");
  const [direction, setDirection] = useState<"ALL" | "BUY" | "SELL">("ALL");
  const [page,      setPage]      = useState(1);
  const [pageSize,  setPageSize]  = useState(12);
  const [loading,   setLoading]   = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
      const res  = await fetch(`/api/ict${params}`);
      if (!res.ok) return;
      const data = await res.json();
      setSetups(data.setups ?? []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [symbol]);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const iv = setInterval(fetchData, 30_000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const allSymbols = Array.from(new Set(setups.map((s) => s.symbol))).filter(Boolean);

  const filteredSetups = useMemo(() => {
    const query = search.trim().toLowerCase();

    return setups.filter((setup) => {
      const passDirection = direction === "ALL" || setup.direction === direction;
      if (!passDirection) return false;

      if (!query) return true;

      const haystack = [
        setup.symbol,
        setup.direction,
        setup.model,
        setup.session,
        setup.reason,
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [setups, search, direction]);

  const pagedSetups = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredSetups.slice(start, start + pageSize);
  }, [filteredSetups, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [search, direction, pageSize, symbol]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(filteredSetups.length / pageSize));
    setPage((prev) => Math.min(prev, totalPages));
  }, [filteredSetups.length, pageSize]);

  return (
    <div
      style={{
        paddingTop:    20,
        paddingBottom: 40,
        fontFamily:    FONT,
        minHeight:     "100vh",
        background:    "#000000",
      }}
    >
      {/* Title */}
      <h1
        style={{
          fontSize:     28,
          fontWeight:   700,
          color:        "#FFFFFF",
          margin:       "0 0 20px",
          letterSpacing:"-0.5px",
          fontFamily:   FONT,
        }}
      >
        ICT Setups
      </h1>

      {/* Symbol filter */}
      <div style={{ marginBottom: 20 }}>
        <SymbolFilter
          symbols={allSymbols}
          selected={symbol}
          onSelect={setSymbol}
        />
      </div>

      {/* Search + direction filters */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 20 }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter setups..."
          style={{
            flex: 1,
            minWidth: 220,
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

        <select
          value={direction}
          onChange={(e) => setDirection(e.target.value as "ALL" | "BUY" | "SELL")}
          style={{
            width: 140,
            height: 34,
            borderRadius: 10,
            border: "1px solid rgba(84,84,88,0.65)",
            background: "rgba(118,118,128,0.2)",
            color: "#FFFFFF",
            padding: "0 10px",
            fontSize: 13,
            fontWeight: 500,
            fontFamily: FONT,
            outline: "none",
          }}
        >
          <option value="ALL">All directions</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div
          style={{
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            padding:        "60px 0",
            color:          "rgba(235,235,245,0.4)",
            fontSize:       14,
            fontFamily:     FONT,
          }}
        >
          Loading ICT setups…
        </div>
      )}

      {/* Empty state */}
      {!loading && filteredSetups.length === 0 && (
        <div
          style={{
            display:        "flex",
            flexDirection:  "column",
            alignItems:     "center",
            justifyContent: "center",
            padding:        "60px 20px",
            gap:            14,
            background:     "#1C1C1E",
            borderRadius:   12,
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: 48, color: "rgba(235,235,245,0.2)" }}
          >
            analytics
          </span>
          <span style={{ fontSize: 15, color: "rgba(235,235,245,0.4)", fontFamily: FONT }}>
            No ICT setups found
          </span>
        </div>
      )}

      {/* Setup grid */}
      {!loading && filteredSetups.length > 0 && (
        <>
          <div
            style={{
              display:             "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
              gap:                 14,
            }}
          >
            {pagedSetups.map((s) => (
              <SetupCard key={s.id} s={s} />
            ))}
          </div>

          <PaginationControls
            page={page}
            totalItems={filteredSetups.length}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            label="setups"
          />
        </>
      )}
    </div>
  );
}
