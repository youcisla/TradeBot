# TradeBot Dashboard — Complete UI/UX Redesign Blueprint

**Date:** April 2026
**Scope:** Ground-up redesign of the entire web dashboard — every page, component, interaction, and data flow
**Backend:** All API routes and data functions already exist. This document specifies WHAT to build on top of them.

---

## 1. What Exists Today (And Why It Fails)

### Current State

The dashboard is 38 components (~11,600 LOC), 26 API routes, and 10 page routes. It has:

- A trading-terminal-style main view (`NewDashboard.tsx`) with symbol sidebar, chart, trade table, intelligence panel, and world strip
- Separate full-page views for: Trades, Analytics, Risk, Learning, Signals, Health, Macro, Brain, Markets, Settings
- Two navigation systems that conflict: `DashNav` (horizontal top bar with 12 items) and `DashBottomNav` (mobile tab bar with 5 items) — neither matches the actual route structure
- A command panel with two-step approval flow
- Real-time agent event feed via WebSocket
- SWR polling on 8-second intervals for status, trades, and events

### Core Problems

| # | Problem | Impact |
|---|---------|--------|
| 1 | **12 navigation items** — 7 of them have no corresponding route (chart, strategy, world, ict, agent_theater, tools, skills) | Users click dead links. The nav structure is a wishlist, not a UI. |
| 2 | **3 different "trades" views** — `TradeTable.tsx`, `OpenTradesTable.tsx`, `TradesPage.tsx` — each with its own data fetching, formatting, and styling | Inconsistent data display. Triple maintenance burden. |
| 3 | **2 different "analytics" views** — `AnalyticsPage.tsx` and `AnalyticsPanel.tsx` — one is a full page, one is an embedded panel. Neither shares code. | Same problem. Double maintenance. |
| 4 | **Hardcoded inline styles everywhere** — `NewDashboard.tsx` has a `styles` object with 40+ entries. `TopBar.tsx`, `SymbolSidebar.tsx`, `IntelligencePanel.tsx` all use inline `style={{}}` | Impossible to theme, no dark/light toggle, no responsive design system |
| 5 | **No shared design tokens** — colors like `#16A34A`, `#DC2626`, `#D97706` are copy-pasted across 20+ files | Change one shade of green → touch 20 files |
| 6 | **Every component fetches its own data** — `TopBar` fetches `/api/status`, `IntelligencePanel` fetches `/api/intelligence`, `TradeTable` fetches `/api/trades`, all independently | N+1 polling problem. 6-8 parallel fetch calls every 8 seconds per page. |
| 7 | **Mobile bottom nav has 5 items; desktop nav has 12** — completely different navigation mental model per device | Users can't transfer muscle memory between devices |
| 8 | **No loading states beyond a single `loading.tsx`** — most components show nothing until data arrives | White flash on every page transition |
| 9 | **`MissionControl.tsx` (515 lines) and `NewDashboard.tsx` are two competing home pages** — MissionControl uses the component library (`Card`, `StatChip`, `Badge`), NewDashboard uses raw inline styles | Unclear which is the real home page |
| 10 | **The WebSocket in `SmartAlertFeed.tsx` is component-local** — only works when that component is mounted. Navigate away → lose the connection. | Missed real-time events on most pages |

---

## 2. Design Direction

### Aesthetic: **Instrument Panel**

Think Bloomberg Terminal meets Porsche dashboard. Dense information, zero decoration. Every pixel earns its space. Dark theme only — traders work in the dark.

**Typography:**
- Headlines: `JetBrains Mono` — monospaced, technical, authoritative
- Body/data: `IBM Plex Mono` — slightly softer monospace for tables and numbers
- Labels: `IBM Plex Sans` — clean sans-serif for navigation and UI chrome

**Color Palette (CSS custom properties in `:root`):**

```css
:root {
  /* Backgrounds */
  --bg-0: #06060A;          /* deepest — page bg */
  --bg-1: #0C0C14;          /* cards, panels */
  --bg-2: #12121C;          /* elevated — modals, dropdowns */
  --bg-3: #1A1A28;          /* hover states */

  /* Borders */
  --border: #1E1E2E;
  --border-focus: #2E2E44;

  /* Text */
  --text-1: #E8E8F0;        /* primary */
  --text-2: #9898B0;        /* secondary */
  --text-3: #58586E;        /* muted */

  /* Semantic */
  --green: #00DC82;          /* profit, running, success */
  --red: #FF4757;            /* loss, error, danger */
  --amber: #FFB84D;          /* warning, paused */
  --blue: #4DA6FF;           /* info, links */
  --purple: #A78BFA;         /* AI/ML indicators */

  /* Accent */
  --accent: #00DC82;         /* primary action color — same as green */

  /* Spacing scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
}
```

**Layout principle:** Three-column on desktop (sidebar | main | context panel), single-column on mobile. The sidebar collapses to icons. The context panel slides in from the right on mobile.

---

## 3. Information Architecture

### 3.1 Navigation — 5 Destinations (Not 12)

Every trader needs exactly five things. Map them to five tabs:

| Tab | Label | Icon | What It Shows | Primary API |
|---|---|---|---|---|
| 1 | **Command** | `dashboard` | Account health, open trades, live P&L, quick actions | `/api/status`, `/api/trades`, `/api/events` |
| 2 | **Chart** | `candlestick_chart` | Full trading chart with symbol selector, timeframe bar, trade markers | `/api/candles`, `/api/candles/trades`, `/api/candles/fibonacci` |
| 3 | **History** | `history` | Closed trades, analytics, equity curve, win rate by symbol/session | `/api/analytics`, `/api/trades?all=true` |
| 4 | **Risk** | `shield` | Drawdown gauges, guard status, exposure map, position sizing config | `/api/risk`, `/api/status` |
| 5 | **System** | `settings` | Bot health, agent feed, learning metrics, broker accounts, settings | `/api/events`, `/api/learning`, `/api/intelligence`, `/api/broker/accounts` |

That's it. Five tabs. Same five on desktop and mobile. Desktop shows them as a left sidebar. Mobile shows them as a bottom tab bar.

### 3.2 Page Content Map

#### Tab 1: Command Center (Home)

```
┌─────────────────────────────────────────────────────────┐
│ STATUS BAR: [●] Running | Equity $10,234 | P&L +$87.50  │
│             Balance $10,000 | 3 Open | London Session    │
├────────────────────────────┬────────────────────────────┤
│                            │                            │
│   OPEN POSITIONS TABLE     │   LIVE EVENT FEED          │
│   Symbol | Dir | Entry     │   [scrolling agent events] │
│   BTCUSD   BUY   67,450   │   ● strategy: BUY signal   │
│   EURUSD   SELL  1.0842   │   ● risk: APPROVED          │
│   GBPJPY   BUY   192.30   │   ● execution: FILLED       │
│                            │   ● trade_mgr: TP1 hit     │
│   [Close] [Close All]     │                            │
│                            │                            │
├────────────────────────────┴────────────────────────────┤
│ QUICK ACTIONS: [Pause] [Resume] [Close All] [Kill]      │
│ MACRO STRIP: VIX 18.2 | Spread Normal | Risk CLEAR      │
└─────────────────────────────────────────────────────────┘
```

**Data sources:**
- Status bar → `useBotStatus()` (SWR, 5s refresh)
- Open positions → `useTrades()` (SWR, 5s refresh)
- Event feed → WebSocket (real-time) with SWR fallback (`useAgentEvents()`)
- Quick actions → POST `/api/commands`
- Macro strip → `/api/intelligence` (SWR, 30s refresh)

**Components to build:**
- `StatusBar` — single row, always visible at the top of every page
- `PositionsCard` — open trades table with close buttons (merges `TradeTable`, `OpenTradesTable`)
- `EventStream` — real-time agent event feed (replaces `SmartAlertFeed`, `AgentFeed`)
- `QuickActions` — pause/resume/close all/kill with confirmation modal
- `MacroStrip` — one-line macro summary (replaces `WorldStrip`)

#### Tab 2: Chart

```
┌─────────────────────────────────────────────────────────┐
│ STATUS BAR (same as above — always present)             │
├──────┬──────────────────────────────────────────────────┤
│      │ [M1][M5][M15][M30][H1][H4][D1][W1]    BTCUSD ▾ │
│  S   │                                                  │
│  Y   │                                                  │
│  M   │        CANDLESTICK CHART                         │
│  B   │        (lightweight-charts)                      │
│  O   │        + trade entry/exit markers                │
│  L   │        + fibonacci levels                        │
│      │        + SL/TP price lines                       │
│  L   │                                                  │
│  I   │                                                  │
│  S   ├──────────────────────────────────────────────────┤
│  T   │ ICT SETUP PANEL (collapsible)                    │
│      │ Active OBs | FVGs | Liquidity sweeps | Sessions  │
└──────┴──────────────────────────────────────────────────┘
```

**Data sources:**
- Candles → `/api/candles?symbol=X&timeframe=Y&count=500`
- Trade markers → `/api/candles/trades?symbol=X`
- Fibonacci → `/api/candles/fibonacci?symbol=X`
- ICT setups → `/api/ict?symbol=X`
- Symbol list → hardcoded from `config/symbols.py` (served via `/api/status` or a new `/api/symbols`)

**Components to build:**
- `Chart` — wrapper around lightweight-charts (refactor `TradingChart.tsx`, keep logic, strip inline styles)
- `TimeframeBar` — button group for timeframe selection
- `SymbolDrawer` — collapsible left panel with categorized symbol list (refactor `SymbolSidebar.tsx`)
- `ICTPanel` — collapsible bottom panel showing active ICT structures

#### Tab 3: History

```
┌─────────────────────────────────────────────────────────┐
│ STATUS BAR                                              │
├─────────────────────────────────────────────────────────┤
│ EQUITY CURVE (area chart, full width)                   │
│ ██████████████████████████████████████████████████████   │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Win Rate     │ Profit Factor│ Total P&L    │ Avg RR     │
│   68.2%      │    1.84      │   +$2,340    │   1.52     │
├──────────────┴──────────────┴──────────────┴────────────┤
│ FILTER: [All Symbols ▾] [All Directions ▾] [30d ▾]     │
├─────────────────────────────────────────────────────────┤
│ CLOSED TRADES TABLE                                     │
│ # | Symbol | Dir | Entry  | Exit   | P&L   | Duration  │
│ 1 | BTCUSD | BUY | 67,200 | 68,100 | +$180 | 4h 12m   │
│ 2 | EURUSD | SELL| 1.0850 | 1.0790 | +$42  | 2h 05m   │
│ ...                                                     │
├─────────────────────────────────────────────────────────┤
│ BREAKDOWN TABS: [By Symbol] [By Session] [By Day]       │
│ Win rate heatmap / bar chart per breakdown dimension     │
└─────────────────────────────────────────────────────────┘
```

**Data sources:**
- Equity curve → `/api/analytics` → `dailyPnl` array
- KPIs → `/api/analytics` → `kpis`
- Closed trades → `/api/analytics` → `closedTrades`
- Symbol stats → `/api/analytics` → `symbolStats`
- Direction stats → `/api/analytics` → `directionStats`

**Components to build:**
- `EquityCurve` — refactor existing, add cumulative P&L line
- `KPIRow` — 4-6 stat chips in a responsive row
- `TradeHistory` — sortable, filterable table of closed trades (merge `TradesPage` + `AnalyticsPage`)
- `BreakdownChart` — bar chart showing win rate by symbol/session/direction

#### Tab 4: Risk

```
┌─────────────────────────────────────────────────────────┐
│ STATUS BAR                                              │
├────────────────────────────┬────────────────────────────┤
│ DAILY DRAWDOWN GAUGE       │ EQUITY DRAWDOWN GAUGE      │
│ ████████░░░░ 3.2% / 5%    │ ████░░░░░░░░ 1.8% / 8%    │
├────────────────────────────┼────────────────────────────┤
│ MONTHLY P&L GAUGE          │ OPEN EXPOSURE              │
│ ████████████░ +$420 / -8%  │ 3 of 5 max positions       │
├────────────────────────────┴────────────────────────────┤
│ GUARD STATUS TABLE                                      │
│ Guard              │ Status  │ Threshold │ Current      │
│ DailyDrawdown      │ ● PASS  │ 5%        │ 3.2%         │
│ EquityDrawdown     │ ● PASS  │ 8%        │ 1.8%         │
│ MaxPositionSize    │ ● PASS  │ 2.0 lots  │ 0.05 lots    │
│ Cooldown           │ ● PASS  │ 300s      │ idle         │
│ MarketHours        │ ● PASS  │ —         │ London       │
│ VIX                │ ⚠ WARN  │ 40.0      │ 38.2         │
│ Spread             │ ● PASS  │ 3 pips    │ 1.2 pips     │
├─────────────────────────────────────────────────────────┤
│ CORRELATION MAP                                         │
│ Visual showing which symbols are correlated and blocked │
├─────────────────────────────────────────────────────────┤
│ POSITION SIZING CONFIG (read-only)                      │
│ Mode: equity_pct | Risk/trade: 2% | Max lots: 50       │
│ Kelly: enabled (half) | Min trades: 20 | Lookback: 90d │
└─────────────────────────────────────────────────────────┘
```

**Data sources:**
- All gauges → `/api/risk`
- Guard status → `/api/risk` (the backend should enumerate guard states — see Section 6)
- Position sizing → `/api/risk` (reads from env vars on the server)

**Components to build:**
- `DrawdownGauge` — arc/bar gauge showing current vs. threshold (refactor `ArcGauge.tsx`)
- `GuardTable` — table of all 11 guards with pass/warn/fail status
- `CorrelationMap` — matrix or node graph showing blocked correlation pairs
- `SizingConfig` — read-only display of position sizing parameters

#### Tab 5: System

This page has **sub-tabs** (not separate nav items):

```
┌─────────────────────────────────────────────────────────┐
│ STATUS BAR                                              │
├─────────────────────────────────────────────────────────┤
│ [Health] [Learning] [Agents] [Broker] [Config]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  (content of selected sub-tab)                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Sub-tab: Health** — Bot uptime, last heartbeat, loop metrics, MT5 connection status, DB pool health, error/warning counts. Replaces `HealthPage.tsx`.

**Sub-tab: Learning** — Strategy confidence table, trade score history, WFO assessment results, regime performance breakdown. Replaces `LearningPage.tsx`.

**Sub-tab: Agents** — Full scrollable agent event log with agent/level filters. Replaces `AgentFeed.tsx`. Shows every agent event with expandable JSON `data` payloads.

**Sub-tab: Broker** — Broker account management (add/edit/delete/activate). Replaces settings page broker section.

**Sub-tab: Config** — Read-only display of all current settings grouped by category. NOT editable (settings are env-driven). Shows: risk params, orchestration params, guard params, strategy params.

---

## 4. Component Architecture

### 4.1 Component Hierarchy

```
app/layout.tsx
└── AppShell (provides BotStatus context + WebSocket connection)
    ├── StatusBar (always visible, top of viewport)
    ├── Navigation (sidebar on desktop, bottom tabs on mobile)
    └── app/dashboard/layout.tsx
        └── <page content>
            ├── /dashboard/           → CommandPage
            ├── /dashboard/chart      → ChartPage
            ├── /dashboard/history    → HistoryPage
            ├── /dashboard/risk       → RiskPage
            └── /dashboard/system     → SystemPage
                                        ├── HealthTab
                                        ├── LearningTab
                                        ├── AgentsTab
                                        ├── BrokerTab
                                        └── ConfigTab
```

### 4.2 Shared Components (The Component Library)

Build these first. Every page uses them.

| Component | Purpose | Props |
|---|---|---|
| `StatusBar` | Always-visible account metrics bar | None (reads from AppShell context) |
| `Nav` | 5-tab navigation, sidebar or bottom bar | `activeTab` |
| `Card` | Container with title, optional actions | `title`, `actions`, `children` |
| `Stat` | Single metric display (label + value + trend) | `label`, `value`, `trend`, `color` |
| `Table` | Sortable data table with column definitions | `columns`, `data`, `onSort` |
| `Badge` | Direction/status/agent badges | `variant`, `children` |
| `Gauge` | Arc or bar progress indicator | `value`, `max`, `label`, `color` |
| `Modal` | Confirmation/action modal | `title`, `onConfirm`, `onCancel` |
| `EventItem` | Single agent event with timestamp and level | `event` |
| `Skeleton` | Loading placeholder | `variant` ("text", "card", "chart") |
| `Tooltip` | Hover info tooltip | `content`, `children` |

### 4.3 Data Layer — Single Source of Truth

**Problem:** Today, `TopBar`, `IntelligencePanel`, `TradeTable`, `BotStatusBar`, `StatusStrip` all independently fetch `/api/status`. That's 5 parallel requests for the same data every 8 seconds.

**Solution:** One SWR cache per data type, shared via React context.

```typescript
// lib/data.ts — THE ONLY data fetching module

// 1. Bot status — polled every 5s, shared across all components
export function useBotStatus() {
  return useSWR<BotStatus>("/api/status", fetcher, { refreshInterval: 5000 });
}

// 2. Open trades — polled every 5s
export function useOpenTrades() {
  return useSWR<Trade[]>("/api/trades", fetcher, { refreshInterval: 5000 });
}

// 3. Agent events — polled every 3s as WebSocket fallback
export function useEvents(limit = 100) {
  return useSWR<AgentEvent[]>(`/api/events?limit=${limit}`, fetcher, { refreshInterval: 3000 });
}

// 4. Analytics — polled every 60s (doesn't change fast)
export function useAnalytics(since?: string, symbol?: string) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (symbol) params.set("symbol", symbol);
  return useSWR(`/api/analytics?${params}`, fetcher, { refreshInterval: 60000 });
}

// 5. Risk — polled every 10s
export function useRisk() {
  return useSWR("/api/risk", fetcher, { refreshInterval: 10000 });
}

// 6. Intelligence — polled every 30s
export function useIntelligence() {
  return useSWR("/api/intelligence", fetcher, { refreshInterval: 30000 });
}

// 7. Candles — fetched on demand (no polling)
export function useCandles(symbol: string, timeframe: string, count = 500) {
  return useSWR(`/api/candles?symbol=${symbol}&timeframe=${timeframe}&count=${count}`, fetcher);
}
```

**Rule:** Components NEVER call `fetch()` directly. They call `useX()` hooks from `lib/data.ts`. SWR deduplicates requests automatically — if 3 components call `useBotStatus()`, only 1 HTTP request fires.

### 4.4 WebSocket — App-Level, Not Component-Level

Move the WebSocket connection into `AppShell`:

```typescript
// Inside AppShell provider:
export default function AppShell({ children }: { children: React.ReactNode }) {
  const { data: status } = useBotStatus();
  const [wsEvents, setWsEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!WS_URL) return;
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (msg) => {
      const events = JSON.parse(msg.data);
      setWsEvents(prev => [...events, ...prev].slice(0, 200));
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  return (
    <AppShellContext.Provider value={{ status, wsEvents, isRunning: status?.state === "running" }}>
      <StatusBar />
      <div className="flex">
        <Nav />
        <main className="flex-1">{children}</main>
      </div>
    </AppShellContext.Provider>
  );
}
```

Now every page can read `wsEvents` from context — no reconnection on navigation.

---

## 5. Page-by-Page Implementation Spec

### 5.1 Command Center (`/dashboard/`)

**File:** `app/dashboard/page.tsx` → renders `CommandPage.tsx`

**Layout:** Two columns (60/40 on desktop, stacked on mobile)

**Left column:**
1. **Account snapshot** — 4 `Stat` components in a row: Equity, Balance, Daily P&L, Open Trades
2. **Open positions table** — `Table` component with columns: Symbol, Direction, Entry, Current, P&L, Age, Actions (Close button). Row click → navigate to chart for that symbol.
3. **Quick actions** — `Pause`, `Resume`, `Close All`, `Kill Switch`. Kill requires double confirmation via `Modal`.

**Right column:**
1. **Live event stream** — scrolling `EventItem` list from `wsEvents` context. Filter by level (info/warn/error). Each event shows: timestamp, agent badge, message. Truncated to 50 most recent.
2. **Macro summary** — 3 inline `Stat` components: VIX, Spread Condition, Trading Session. Sourced from `useIntelligence()`.

**Responsive:** On mobile, the event stream moves below positions. Quick actions become a floating action button with a bottom sheet.

### 5.2 Chart (`/dashboard/chart`)

**File:** `app/dashboard/chart/page.tsx` → renders `ChartPage.tsx`

**Layout:** Full-width chart with collapsible left sidebar (symbol list) and collapsible bottom panel (ICT setups).

**Chart implementation:** Keep `lightweight-charts` (it's the right library). Refactor `TradingChart.tsx`:
- Remove all inline styles → use CSS classes
- Add trade entry/exit markers (green/red triangles on the candle at `open_time`/`close_time`)
- Add horizontal price lines for SL (red dashed) and TP1/TP2/TP3 (green dashed) of open trades on that symbol
- Add Fibonacci retracement overlay when available from `/api/candles/fibonacci`

**Symbol selector:** Collapsible sidebar with categories (Crypto, Forex Major, etc.). Search box at top. Clicking a symbol updates the chart. The current symbol is shown in the timeframe bar.

**Timeframe bar:** `M1 M5 M15 M30 H1 H4 D1 W1` — button group. Active timeframe highlighted.

**ICT panel:** Below chart, 200px tall, collapsible. Shows:
- Active order blocks (price, direction, freshness)
- Active FVGs (price range, filled %)
- Recent liquidity sweeps (price, timestamp)
- Current session context (killzone active? dealing range?)

Sourced from `/api/ict?symbol=X`. If no ICT data, panel shows "No active ICT structures for {symbol}".

### 5.3 History (`/dashboard/history`)

**File:** `app/dashboard/history/page.tsx` → renders `HistoryPage.tsx`

**Layout:** Full-width content area, no sidebar.

**Top section:** Equity curve — `AreaChart` from recharts, full width, 200px tall. X-axis: dates. Y-axis: cumulative P&L. Green fill when above 0, red fill when below.

**KPI row:** Below curve. 6 `Stat` components: Win Rate, Profit Factor, Total P&L, Avg Win, Avg Loss, Expectancy. Derived client-side from the `closedTrades` array.

**Filters:** Row of dropdowns: Symbol (all/specific), Direction (all/BUY/SELL), Period (7d/30d/90d/all). Filters update the `/api/analytics?since=X&symbol=Y` call.

**Trade table:** Full closed trades list. Sortable by: P&L, duration, symbol, date. Paginated (25 per page). Each row shows: date, symbol, direction badge, entry price, exit price, P&L (colored), duration, strategy, close reason.

**Breakdown section:** Below the table. Three tabs:
- **By Symbol** — horizontal bar chart: win rate per symbol
- **By Session** — horizontal bar chart: win rate per session (asian/london/overlap/newyork)
- **By Day** — horizontal bar chart: win rate per day of week

### 5.4 Risk (`/dashboard/risk`)

**File:** `app/dashboard/risk/page.tsx` → renders `RiskDashboard.tsx`

**Layout:** Grid of cards, full width.

**Top row — 4 gauges:**
- Daily Drawdown: current % vs. max allowed %
- Equity Drawdown: current % vs. max allowed %
- Monthly P&L: current $ vs. max loss limit
- Position Count: current vs. max allowed

Each gauge is a `Gauge` component — semi-circle arc, green when <50% of limit, amber when 50-80%, red when >80%.

**Middle row — Guard Status:**
`Table` with columns: Guard Name, Status (● PASS / ⚠ WARN / ✕ FAIL), Threshold, Current Value, Last Check.

This requires a new API field. The `/api/risk` route should return a `guards` array:
```json
{
  "guards": [
    { "name": "DailyDrawdown", "status": "pass", "threshold": "5%", "current": "3.2%" },
    { "name": "EquityDrawdown", "status": "pass", "threshold": "8%", "current": "1.8%" },
    ...
  ]
}
```

**Backend change needed:** The Python bot already has all 11 guards in `agents/guards.py`. Add a method `GuardPipeline.get_status() -> list[dict]` that returns each guard's name, pass/fail status, threshold, and current value. Expose this via the heartbeat → `bot_status` table → `/api/risk`.

**Bottom row — Config display:**
Two `Card` components side by side:
- **Position Sizing** — mode, risk per trade, min/max lot, Kelly params
- **Correlation Map** — list of currently blocked pairs (from `_CORRELATED_PAIRS` in risk_agent, or eventually from `CorrelationGate`)

### 5.5 System (`/dashboard/system`)

**File:** `app/dashboard/system/page.tsx` → renders `SystemPage.tsx`

**Layout:** Sub-tab navigation at top (pill buttons), content below.

**Sub-tab: Health**
- Uptime display (formatted from `uptime_start`)
- Last heartbeat timestamp
- Loop metrics (from agent events — scan/rank/exec latency)
- MT5 connection status
- DB pool health (if exposed)
- Error count (last 24h) and warning count (last 24h)

**Sub-tab: Learning**
- Strategy confidence table: strategy name, confidence %, total trades, avg score, trend arrow
- Recent trade scores: last 20 scored trades with symbol, score, P&L
- WFO assessment: last result (overfitting score, stability score, regime breakdown)
Data from `/api/learning`.

**Sub-tab: Agents**
- Full agent event log. Filterable by agent name (dropdown with all agent names) and level (info/warn/error). Scrollable, auto-refreshing. Each event expandable to show full JSON `data` payload.

**Sub-tab: Broker**
- List of broker accounts. Active account highlighted.
- Actions: Add Account, Edit, Delete, Activate.
- Each account shows: name, account number, server, demo/live flag, connection status.
Data from `/api/broker/accounts`.

**Sub-tab: Config**
- Read-only grouped display of current bot settings.
- Groups: Risk, Execution, Guards, Orchestration, Sniper, ICT, Telegram, ML.
- Each setting shows: name, current value, description.
Data from a new `/api/config` endpoint that reads from `config/settings.py` and returns the flattened values. Or simply hardcode the display from `/api/risk` + `/api/status` combined.

---

## 6. Backend API Changes Required

### 6.1 New Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/symbols` | GET | Return the full symbol list with categories and active status |
| `GET /api/config` | GET | Return current bot settings (read-only, grouped) |

### 6.2 Modified Endpoints

| Endpoint | Change |
|---|---|
| `GET /api/risk` | Add `guards` array with per-guard status/threshold/current |
| `GET /api/status` | Add `loop_count`, `last_scan_latency_ms`, `last_reconnect_at` |

### 6.3 Endpoints to Delete

| Endpoint | Reason |
|---|---|
| `/api/agents/leaderboard` | Feature not in the redesign (remove later if unused) |
| `/api/subscriptions/*` | Feature not in the redesign |
| `/api/skills/*` | Feature not in the redesign |
| `/api/tools` | Feature not in the redesign (tool system is backend-only) |
| `/api/world` | Merged into `/api/intelligence` |

Don't delete them now — just don't build UI for them. They can be cleaned up after the redesign ships.

---

## 7. File Structure

```
web/src/
├── app/
│   ├── layout.tsx                    # Root layout with AppShell
│   ├── page.tsx                      # Redirect to /dashboard
│   ├── login/page.tsx                # Auth (keep existing)
│   ├── dashboard/
│   │   ├── layout.tsx                # Dashboard shell (StatusBar + Nav + main)
│   │   ├── page.tsx                  # Tab 1: Command Center
│   │   ├── chart/page.tsx            # Tab 2: Chart
│   │   ├── history/page.tsx          # Tab 3: History
│   │   ├── risk/page.tsx             # Tab 4: Risk
│   │   └── system/page.tsx           # Tab 5: System (with sub-tabs)
│   └── api/                          # Keep all existing API routes
│       ├── status/route.ts
│       ├── trades/route.ts
│       ├── events/route.ts
│       ├── commands/route.ts
│       ├── analytics/route.ts
│       ├── risk/route.ts
│       ├── intelligence/route.ts
│       ├── candles/route.ts
│       ├── learning/route.ts
│       ├── broker/accounts/route.ts
│       ├── ict/route.ts
│       ├── signals/route.ts
│       └── ...
├── components/
│   ├── shell/
│   │   ├── AppShell.tsx              # Context provider + WebSocket
│   │   ├── StatusBar.tsx             # Always-visible top bar
│   │   └── Nav.tsx                   # 5-tab navigation (sidebar + bottom)
│   ├── shared/
│   │   ├── Card.tsx
│   │   ├── Stat.tsx
│   │   ├── Table.tsx
│   │   ├── Badge.tsx
│   │   ├── Gauge.tsx
│   │   ├── Modal.tsx
│   │   ├── EventItem.tsx
│   │   ├── Skeleton.tsx
│   │   └── Tooltip.tsx
│   ├── command/
│   │   ├── CommandPage.tsx
│   │   ├── PositionsCard.tsx
│   │   ├── EventStream.tsx
│   │   ├── QuickActions.tsx
│   │   └── MacroStrip.tsx
│   ├── chart/
│   │   ├── ChartPage.tsx
│   │   ├── Chart.tsx                 # lightweight-charts wrapper
│   │   ├── TimeframeBar.tsx
│   │   ├── SymbolDrawer.tsx
│   │   └── ICTPanel.tsx
│   ├── history/
│   │   ├── HistoryPage.tsx
│   │   ├── EquityCurve.tsx
│   │   ├── KPIRow.tsx
│   │   ├── TradeHistory.tsx
│   │   └── BreakdownChart.tsx
│   ├── risk/
│   │   ├── RiskDashboard.tsx
│   │   ├── DrawdownGauge.tsx
│   │   ├── GuardTable.tsx
│   │   ├── CorrelationMap.tsx
│   │   └── SizingConfig.tsx
│   └── system/
│       ├── SystemPage.tsx
│       ├── HealthTab.tsx
│       ├── LearningTab.tsx
│       ├── AgentsTab.tsx
│       ├── BrokerTab.tsx
│       └── ConfigTab.tsx
├── lib/
│   ├── data.ts                       # ALL SWR hooks (single file)
│   ├── db.ts                         # Server-side DB queries (keep existing)
│   ├── auth.ts                       # Auth config (keep existing)
│   ├── format.ts                     # Price/USD/time formatting (consolidate)
│   └── ws.ts                         # WebSocket client logic
└── styles/
    └── globals.css                   # CSS variables, base styles, Tailwind config
```

### Components to Delete

These are replaced by the redesign. Delete them after the new components ship:

```
components/NewDashboard.tsx       → replaced by CommandPage
components/MissionControl.tsx     → replaced by CommandPage
components/TopBar.tsx             → replaced by StatusBar
components/BotStatusBar.tsx       → replaced by StatusBar
components/StatusStrip.tsx        → replaced by StatusBar
components/DashNav.tsx            → replaced by Nav
components/DashBottomNav.tsx      → replaced by Nav
components/DashHeader.tsx         → replaced by Nav
components/DashSidebar.tsx        → replaced by Nav
components/TradeTable.tsx         → replaced by PositionsCard
components/OpenTradesTable.tsx    → replaced by PositionsCard
components/TradesWidget.tsx       → replaced by PositionsCard
components/TradesPage.tsx         → replaced by TradeHistory
components/AnalyticsPage.tsx      → replaced by HistoryPage
components/AnalyticsPanel.tsx     → replaced by HistoryPage
components/SmartAlertFeed.tsx     → replaced by EventStream
components/AgentFeed.tsx          → replaced by AgentsTab
components/WorldStrip.tsx         → replaced by MacroStrip
components/MarketIntel.tsx        → replaced by MacroStrip
components/IntelligencePanel.tsx  → replaced by MacroStrip + StatusBar
components/MacroPage.tsx          → replaced by MacroStrip
components/HealthPage.tsx         → replaced by HealthTab
components/LearningPage.tsx       → replaced by LearningTab
components/SignalsPage.tsx        → merged into EventStream
components/RiskPage.tsx           → replaced by RiskDashboard
components/CommandPanel.tsx       → replaced by QuickActions
components/NewsTicker.tsx         → deleted (unused)
components/TerminalButton.tsx     → deleted (unused)
components/TerminalInput.tsx      → deleted (unused)
```

That's **28 components deleted**, replaced by **25 focused components** with zero overlap.

---

## 8. Implementation Order

### Phase 1: Foundation (Day 1)

1. Create `styles/globals.css` with all CSS variables from Section 2
2. Create `lib/data.ts` with all SWR hooks from Section 4.3
3. Create `lib/format.ts` — consolidate the 8 duplicate `fmtUsd()`, `fmtPrice()`, `relTime()` functions scattered across components
4. Create `lib/ws.ts` — extract WebSocket logic from `SmartAlertFeed.tsx`
5. Build `components/shell/AppShell.tsx` — context provider with `useBotStatus()` + WebSocket
6. Build `components/shell/StatusBar.tsx` — reads from AppShell context
7. Build `components/shell/Nav.tsx` — 5 tabs, sidebar on desktop, bottom bar on mobile
8. Wire into `app/dashboard/layout.tsx`

**Verification:** Navigate between all 5 tab routes. StatusBar shows live data. Nav highlights correct tab. WebSocket connects once and stays connected.

### Phase 2: Shared Components (Day 1-2)

Build all 10 shared components from Section 4.2. Test each in isolation. Use Tailwind for styling — no inline styles.

### Phase 3: Command Center (Day 2)

Build `CommandPage.tsx` + `PositionsCard.tsx` + `EventStream.tsx` + `QuickActions.tsx` + `MacroStrip.tsx`. Wire to `/dashboard/` route.

**Verification:** Open trades display correctly. Events stream in real-time. Pause/Resume/Close All work. P&L updates every 5 seconds.

### Phase 4: Chart (Day 3)

Refactor `TradingChart.tsx` into `Chart.tsx`. Build `ChartPage.tsx` + `TimeframeBar.tsx` + `SymbolDrawer.tsx` + `ICTPanel.tsx`. Wire to `/dashboard/chart`.

**Verification:** Chart loads candles, symbol/timeframe switching works, trade markers show, fibonacci overlay shows.

### Phase 5: History (Day 3-4)

Build `HistoryPage.tsx` + `EquityCurve.tsx` + `KPIRow.tsx` + `TradeHistory.tsx` + `BreakdownChart.tsx`. Wire to `/dashboard/history`.

**Verification:** Equity curve renders, KPIs are mathematically correct (spot-check against DB), filters work, breakdown charts populate.

### Phase 6: Risk (Day 4)

Build `RiskDashboard.tsx` + `DrawdownGauge.tsx` + `GuardTable.tsx` + `CorrelationMap.tsx` + `SizingConfig.tsx`. Wire to `/dashboard/risk`.

**Verification:** Gauges show correct percentages, guard status matches what the Python bot logs.

### Phase 7: System (Day 5)

Build `SystemPage.tsx` + all 5 sub-tabs. Wire to `/dashboard/system`.

**Verification:** All sub-tabs render, broker account CRUD works, agent log filters work.

### Phase 8: Delete Old Components (Day 5)

Delete all 28 components listed in Section 7. Remove unused API routes. Run `tsc --noEmit` to catch broken imports. Fix any remaining references.

**Total estimated time: 5 working days** for a single developer who knows React and Next.js.

---

## 9. Mobile Design

**Principle:** Same 5 tabs, same data, smaller viewport. No separate "mobile version" — just responsive breakpoints.

| Breakpoint | Layout |
|---|---|
| `>= 1280px` (xl) | Sidebar nav (left) + full content + optional right panel |
| `768px – 1279px` (md) | Collapsed sidebar (icons only) + full content |
| `< 768px` (sm) | Bottom tab bar + stacked content, no sidebar |

**Mobile-specific behaviors:**
- Symbol drawer slides in from left as an overlay (not inline)
- ICT panel slides up from bottom as a sheet
- Event stream collapses to last 3 events with "See all" button
- Quick actions become a floating action button (bottom-right, above tab bar) that opens a bottom sheet
- Tables become horizontally scrollable cards on very small screens

**Critical: No horizontal scrolling on the page itself.** Individual components can scroll horizontally (tables, chart), but the page container never overflows.

---

## 10. Performance Budget

| Metric | Target |
|---|---|
| First Contentful Paint | < 1.2s |
| Largest Contentful Paint | < 2.0s |
| Total blocking time | < 200ms |
| Cumulative Layout Shift | < 0.05 |
| Bundle size (gzipped) | < 250KB JS |
| API calls per page load | ≤ 3 (SWR dedup) |
| API calls per 10-second idle | ≤ 2 (polling) |
| WebSocket messages per second | ≤ 5 avg |

**How to achieve this:**
- Code-split pages with Next.js dynamic imports — the chart page (which imports `lightweight-charts`) should not load on the command page
- Keep `lightweight-charts` and `recharts` as lazy imports
- Remove `three`, `@react-three/fiber`, `@react-three/drei` from dependencies (18MB of unused 3D libraries in `package.json`)
- Use `useSWR` with `keepPreviousData: true` so page transitions don't flash empty

---

## 11. Dependencies to Add/Remove

### Remove
```
@react-three/drei       # unused 3D library
@react-three/fiber      # unused 3D library
three                   # unused 3D library
@types/three            # unused 3D types
react-markdown          # unused markdown renderer
```

### Keep
```
lightweight-charts      # trading chart (essential)
recharts                # equity curve and bar charts
swr                     # data fetching and caching
next-auth               # authentication
pg                      # database client
bcryptjs                # password hashing
ws                      # WebSocket server
```

### Add
```
clsx                    # conditional className utility (tiny)
```

No new dependencies. The current stack (Next.js + Tailwind + SWR + recharts + lightweight-charts) is the right stack. Just remove the dead weight.
