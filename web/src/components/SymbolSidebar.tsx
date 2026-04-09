"use client";

import { useCallback, useEffect, useState } from "react";

interface SidebarProps {
  selected: string;
  onSelect: (s: string) => void;
}

// ── Symbol classification ────────────────────────────────────────────────────────

const SECTIONS = [
  { label: "Crypto",          key: "CRYPTO",       color: "#F7931A" },
  { label: "Forex Major",     key: "FOREX_MAJORS",  color: "#16A34A" },
  { label: "Forex Crosses",   key: "FOREX_CROSSES", color: "#16A34A" },
  { label: "Commodities",     key: "COMMODITIES",   color: "#D97706" },
  { label: "Indices",         key: "INDICES",       color: "#2563EB" },
  { label: "ETFs",            key: "ETFS",          color: "#9333EA" },
  { label: "Bonds",           key: "BONDS",         color: "#6B7280" },
  { label: "Stock CFDs",      key: "STOCK_CFDS",    color: "#374151" },
  { label: "Forex (.s)",      key: "FOREX_S",       color: "#16A34A" },
] as const;

export default function SymbolSidebar({ selected, onSelect }: SidebarProps) {
  const [expanded, setExpanded] = useState(true);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    CRYPTO: true,
    FOREX_MAJORS: true,
  });

  const toggleSection = (key: string) =>
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <aside style={styles.sidebar}>
      <AccountSummary />
      <div style={styles.divider} />

      <div style={styles.sectionHeader}>
        <span style={styles.sectionLabel}>Symbols</span>
        <button onClick={() => setExpanded((v) => !v)} style={styles.toggleBtn}>
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && (
        <div style={styles.scrollArea}>
          {SECTIONS.map(({ label, key, color }) => (
            <SymbolSection
              key={key}
              label={label}
              categoryKey={key}
              color={color}
              isOpen={!!openSections[key]}
              onToggle={() => toggleSection(key)}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </aside>
  );
}

// ── Account summary ────────────────────────────────────────────────────────────

function AccountSummary() {
  const [status, setStatus] = useState<Record<string, string | number> | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const r = await fetch("/api/status");
      if (r.ok) setStatus(await r.json());
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, 8_000);
    return () => clearInterval(id);
  }, [fetch_]);

  if (!status) return <div style={styles.accountSkeleton} />;

  const equity = typeof status.equity === "string"
    ? parseFloat(status.equity) : (status.equity as number) ?? 0;
  const balance = typeof status.balance === "string"
    ? parseFloat(status.balance) : (status.balance as number) ?? 0;
  const dailyPnl = typeof status.daily_pnl === "string"
    ? parseFloat(status.daily_pnl) : (status.daily_pnl as number) ?? 0;

  const fmt = (v: number) =>
    v >= 0
      ? `$${v.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
      : `-$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  return (
    <div style={styles.account}>
      <div style={styles.accountRow}>
        <span style={styles.accountLabel}>Equity</span>
        <span style={styles.accountValue}>{fmt(equity)}</span>
      </div>
      <div style={styles.accountRow}>
        <span style={styles.accountLabel}>Balance</span>
        <span style={styles.accountValue}>{fmt(balance)}</span>
      </div>
      <div style={styles.accountRow}>
        <span style={styles.accountLabel}>Today</span>
        <span style={{ ...styles.accountValue, color: dailyPnl >= 0 ? "#16A34A" : "#DC2626" }}>
          {dailyPnl >= 0 ? "+" : ""}
          {fmt(dailyPnl)}
        </span>
      </div>
    </div>
  );
}

// ── Symbol section ────────────────────────────────────────────────────────────

interface SymbolSectionProps {
  label: string;
  categoryKey: string;
  color: string;
  isOpen: boolean;
  onToggle: () => void;
  selected: string;
  onSelect: (s: string) => void;
}

function SymbolSection({ label, categoryKey, color, isOpen, onToggle, selected, onSelect }: SymbolSectionProps) {
  const symbols = SYMBOL_MAP[categoryKey] ?? [];
  if (symbols.length === 0) return null;

  return (
    <div style={styles.section}>
      <button onClick={onToggle} style={styles.catBtn}>
        <span style={{ ...styles.catDot, background: color }} />
        <span style={styles.catLabel}>{label}</span>
        <span style={styles.catCount}>{symbols.length}</span>
        <span style={styles.catChevron}>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div style={styles.symGrid}>
          {symbols.map((sym) => (
            <button
              key={sym}
              onClick={() => onSelect(sym)}
              style={{
                ...styles.symBtn,
                ...(selected === sym ? styles.symBtnActive : {}),
              }}
            >
              {sym.replace(".s", "")}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Static symbol map (populated from config/symbols.py at build time) ────────
// Categories with fewer than 10 items are shown fully; larger ones show top流动性

const SYMBOL_MAP: Record<string, string[]> = {
  // CRYPTO — 65 symbols, show all
  CRYPTO: [
    "ADAJPY","ADAUSD","ALGUSD","ALICEUSD","ALPACAUSD","ALPHAUSD","AMDUSD","ARPAUSD","ATAUSD","ATMUSD",
    "AVAUSD","AXSUSD","BATUSD","BCHUSD","BICOUSD","BLZUSD","BNBUSD","BTCUSD","BTMUSD","C98USD",
    "CAKEUSD","CELOUSD","CELRUSDD","CHZUSD","COTIUSD","CRVUSD","DASHUSD","DENTUSD","DGBUSD","DOGUSD",
    "DOTUSD","EGLDUSD","ENJUSD","EOSUSD","ETCUSD","ETHUSD","FETUSD","FILUSD","FTMUSDD",
    "FTTUSD","GALAUSD","GODSUSD","GRTUSD","GTCUSD","HBARUSD","ICPUSD","ICXUSD","JASMYUSD","KAVAUSD",
    "KCSUSD","KDAUSD","KSMUSD","LINKUSD","LPTUSD","LRCUSD","LSKUSD","LTCUSD","LUNAUSD","MANAUSD",
    "MKRUSD","NEARUSD","NEOUSD","OMGUSD","ONGUSD","ONTUSD","PAXUSD","QTUMUSD","RAREUSD","RAYUSD",
    "RENUSD","RNDRUSD","ROSEUSD","RSRUSDD","RUNEUSD","RVNUSD","SANDUSD","SFPUSD","SHIBUSD","SLPUSD",
    "SOLUSD","STARUSD","STCUSD","SUSHIUSD","SXPUSD","THETAUSD","TKNGUSD","TLMUSD","TOMOUSDD","TRXUSD",
    "TUSDUSD","UMAUSD","UNFIUSD","VETUSD","VTHOUSD","WAVESUSD","XLMUSD","XMRUSD","XRPUSD","XTZUSD",
    "YFIUSD","YGGUSD","ZBCUSD","ZECUSD","ZENUSD","ZILUSD","ZRXUSD",
  ],
  FOREX_MAJORS: ["AUDUSD","EURUSD","GBPUSD","USDCAD","USDCHF","USDJPY"],
  FOREX_CROSSES: ["GBXUSD","USDAED","USDCNH","USDHKD","USDSGD","USDZAR"],
  COMMODITIES: [
    "COPPER-Cs","Cocoa-Cs","Coffee-Cs","Cotton-Cs","GAS-Cs","GASOIL-Cs","GAUUSD.s","NG-Cs",
    "OJ-Cs","ROBUSTAft.s","Soybean-Cs","Sugar-Cs","Wheat-Cs","XAGUSD.s","XAUEUR.s","XAUJPY.s",
    "XAUUSD.s","XPDUSD.s","XPTUSD.s",
  ],
  INDICES: [
    "BVSPX.s","CHINA50.s","CHINA50ft.s","CHINAH.s","DJ30.s","DJ30ft.s","ES35.s","EU50.s",
    "FRA40.s","FRA40ft.s","GER40.s","GER40ft.s","HK50.s","HK50ft.s","HKTECH.s","JPN225ft.s",
    "NAS100.s","NAS100ft.s","NETH25.s","Nikkei225.s","SA40.s","SGP20.s","SP500.s","SP500ft.s",
    "SPI200.s","SWI20.s","TWINDEX.s","UK100.s","UK100ft.s","US2000.s","USDX.s","VIX.s",
  ],
  ETFS: [
    "AGG","ARKB","ARKG","ARKK","ARKQ","ARKW","BITB","BITO","BITQ","BKCH",
    "BLCN","BLOK","BND","BNDX","BNO","BTCO","DBA","DBC","EEM","EFA",
    "ESGV","FAS","FAZ","FDN","FXI","GBTC","GDX","GDXJ","GLD","GOAU",
    "GOEX","GRID","GSG","IBIT","ICLN","IWM","IYW","JNUG","NUGT","OIH",
    "QCLN","QQQ","RING","SDS","SGDJ","SMH","SOXL","SPGP","SQQQ","TAN",
    "TECL","TNA","TYD","UDOW","UMDD","UPRO","URTY","WANT","WUGI","XLK",
    "XLV","XLY","YINN","YLD",
  ],
  BONDS: ["BIL","GOVT","HYG","IEF","IEM","LQD","SHY","TIP","TLH","TLT","VGLT"],
  // STOCK_CFDS — show top 60 most liquid
  STOCK_CFDS: [
    "AAPL","ABNB","ADBE","ADMA","ADSK","ALGN","ALNY","AMD","AMGN","AMZN",
    "ANSS","APP","ASML","ATVI","AVGO","AVLR","AZO","BABA","BIDU","BKNG",
    "CDAY","CDNS","CDW","CERN","CHKP","COIN","COST","CRM","CSCO","CSGP",
    "CTAS","CTSH","CVET","CZR","DDOG","DECK","DGX","DIDI","DLTR","DOCU",
    "DOCUS","DT","EA","EBAY","EXAS","EXC","EXPE","FANG","FAST","FISV",
    "FTNT","FVRR","GILD","GLNG","GLOB","GOOGL","GOOG","HAR","HON","HOOD",
  ],
  FOREX_S: [
    "AUDCAD.s","AUDCHF.s","AUDJPY.s","AUDNZD.s","AUDSGD.s","AUDUSD.s","CADCHF.s","CADJPY.s",
    "CHFJPY.s","EURAUD.s","EURCAD.s","EURCHF.s","EURCZK.s","EURDKK.s","EURGBP.s","EURHUF.s",
    "EURJPY.s","EURNZD.s","EURSGD.s","EURUSD.s","GBPAUD.s","GBPCAD.s","GBPCHF.s","GBPJPY.s",
    "GBPNZD.s","GBPSGD.s","GBPUSD.s","NZDCAD.s","NZDCHF.s","NZDJPY.s","NZDSGD.s","NZDUSD.s",
    "SGDJPY.s","USDAED.s","USDBRL.s","USDCAD.s","USDCHF.s","USDCLP.s","USDCOP.s","USDCZK.s",
    "USDDKK.s","USDHKD.s","USDHUF.s","USDIDR.s","USDILS.s","USDINR.s","USDJPY.s","USDKRW.s",
    "USDMXN.s","USDNOK.s","USDSEK.s","USDSGD.s","USDTHB.s","USDTWD.s","USDZAR.s",
  ],
};

// ── Styles ──────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    position: "fixed",
    top: 48,
    left: 0,
    bottom: 0,
    width: 180,
    background: "#F5F5F7",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    zIndex: 90,
  },
  account: {
    padding: "14px 14px 10px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  accountRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  accountLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  accountValue: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    fontWeight: 600,
    color: "#111111",
  },
  accountSkeleton: {
    height: 72,
    margin: "14px 14px 10px",
    background: "#E5E7EB",
    borderRadius: 4,
  },
  divider: {
    height: 1,
    background: "#E5E7EB",
    margin: "0 14px",
  },
  sectionHeader: {
    padding: "10px 14px 6px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sectionLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  toggleBtn: {
    background: "none",
    border: "none",
    padding: 0,
    cursor: "pointer",
    fontSize: 9,
    color: "#9CA3AF",
  },
  scrollArea: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    padding: "0 8px 14px",
  },
  section: {
    display: "flex",
    flexDirection: "column",
  },
  catBtn: {
    background: "none",
    border: "none",
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 6px",
    cursor: "pointer",
    width: "100%",
    borderRadius: 4,
  },
  catDot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    flexShrink: 0,
  },
  catLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#6B7280",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  catCount: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    marginLeft: "auto",
  },
  catChevron: {
    fontSize: 9,
    color: "#9CA3AF",
  },
  symGrid: {
    display: "flex",
    flexWrap: "wrap",
    gap: 2,
    padding: "3px 4px 6px",
  },
  symBtn: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "3px 6px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#6B7280",
    transition: "background 0.1s, color 0.1s",
  },
  symBtnActive: {
    background: "#FFFFFF",
    color: "#111111",
    fontWeight: 700,
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  },
};
