# PulseTrade Frontend Redesign Specification
### Version 1.0 — 2026-04-13
### Author: Senior Frontend Architecture Review

---

## PART 0 — EXECUTIVE SUMMARY

This document defines a complete frontend redesign for the PulseTrade Trading Command Center. The existing codebase has a solid foundation — a working App Router, SWR data fetching, and meaningful design tokens — but suffers from inconsistent component patterns, duplicated files, placeholder pages, and no unified design system. This redesign addresses those structural problems and transforms the UI into a professional-grade trading platform.

**Key Numbers:**
- 8 pages to design (5 exist, 3 are placeholders)
- 20+ UI primitives (many duplicated or inconsistent)
- 1 unified design system to establish
- ~20 component files to restructure

---

## PART 1 — FRONTEND ARCHITECTURE

### 1.1 Target Folder Structure

```
web/src/
├── app/
│   ├── globals.css                        # Design tokens (CSS custom props)
│   ├── layout.tsx                          # Root layout (fonts, providers)
│   ├── page.tsx                            # Landing / redirect to /dashboard
│   ├── login/page.tsx                      # Auth page
│   └── dashboard/
│       ├── layout.tsx                      # Dashboard shell (sidebar + header)
│       ├── page.tsx                        # → MissionControl
│       ├── signals/page.tsx                # → SignalsIntelligence
│       ├── trades/page.tsx                 # → TradesPositions
│       ├── risk/page.tsx                   # → RiskExposure
│       ├── agents/page.tsx                 # → AgentObservability
│       ├── health/page.tsx                # → SystemHealth
│       ├── learning/page.tsx               # → LearningAI
│       ├── settings/page.tsx               # → Settings
│       └── chart/page.tsx                 # → TradingChart (existing, migrate)
│
├── components/
│   ├── app/                                # App-level layout primitives
│   │   ├── AppShell.tsx                   # Context provider + WebSocket bridge
│   │   ├── AppShellLayout.tsx             # Sidebar + header shell
│   │   ├── Sidebar.tsx                    # Left nav (desktop)
│   │   ├── MobileNav.tsx                  # Bottom nav (mobile)
│   │   ├── Header.tsx                     # Top bar (bot status, KPIs, clock)
│   │   └── CommandPalette.tsx             # ⌘K command palette
│   │
│   ├── ui/                                # Pure design primitives (no business logic)
│   │   ├── primitives/                    # Radix-backed primitives
│   │   │   ├── button.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── tooltip.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── select.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── separator.tsx
│   │   │   └── sheet.tsx                  # Drawer (replaces custom drawers)
│   │   │
│   │   ├── data-display/                  # Data display primitives
│   │   │   ├── stat-card.tsx              # KPI card (value + label + trend)
│   │   │   ├── data-table.tsx             # TanStack Table wrapper
│   │   │   ├── column-def.ts              # Shared TanStack ColumnDef helpers
│   │   │   ├── event-feed.tsx             # Scrollable live event list
│   │   │   ├── gauge.tsx                  # Radial/fill gauge (drawdown, confidence)
│   │   │   ├── sparkline.tsx              # Inline trend line
│   │   │   └── pulse-dot.tsx              # Live status indicator
│   │   │
│   │   ├── layout/                        # Layout primitives
│   │   │   ├── panel.tsx                  # Card with title slot
│   │   │   ├── drawer-panel.tsx           # Sheet-based detail drawer
│   │   │   ├── section-header.tsx         # Section label + optional action
│   │   │   └── stack.tsx                  # Vertical gap container
│   │   │
│   │   └── feedback/                      # Transient UI
│   │       ├── toast.tsx                  # Radix Toast
│   │       ├── skeleton.tsx               # Loading placeholder
│   │       └── empty-state.tsx            # No-data state
│   │
│   ├── features/                          # Business-domain components (composed of ui primitives)
│   │   ├── mission-control/
│   │   │   ├── MissionControl.tsx         # Main dashboard page
│   │   │   ├── KpiRow.tsx                 # Equity / Balance / Daily P&L / Open / Loops / Bot
│   │   │   ├── MacroStrip.tsx             # VIX / Regime / Session / Spread strip
│   │   │   ├── PositionsCard.tsx          # Open positions mini-table
│   │   │   ├── QuickActions.tsx           # Pause / Resume / Force Scan buttons
│   │   │   └── AlertsFeed.tsx             # Critical alerts list
│   │   │
│   │   ├── signals/
│   │   │   ├── SignalsPage.tsx            # Signals intelligence page
│   │   │   ├── SignalsTable.tsx           # TanStack Table of signals
│   │   │   ├── SignalRow.tsx              # Single signal row (hover to expand)
│   │   │   ├── SignalDetailDrawer.tsx     # Sheet with reasoning, confidence breakdown
│   │   │   └── ConfidenceBar.tsx           # Visual confidence score
│   │   │
│   │   ├── trades/
│   │   │   ├── TradesPage.tsx             # Active trades + history
│   │   │   ├── ActivePositions.tsx        # Currently open trades
│   │   │   ├── TradeHistoryTable.tsx     # Historical trades
│   │   │   ├── PnlChart.tsx              # Daily P&L bar chart
│   │   │   ├── TradeLifecycle.tsx         # Entry → TP/SL tracking visual
│   │   │   └── TradeDetailDrawer.tsx     # Trade deep-dive sheet
│   │   │
│   │   ├── risk/
│   │   │   ├── RiskPage.tsx              # Risk & exposure page
│   │   │   ├── ExposureGrid.tsx          # Per-symbol exposure cards
│   │   │   ├── LimitsPanel.tsx           # Max positions, daily loss cap
│   │   │   ├── GuardPipeline.tsx         # Guard status table
│   │   │   ├── DrawdownGauge.tsx         # Current drawdown gauge
│   │   │   └── BlockedTrades.tsx        # Recently blocked trades log
│   │   │
│   │   ├── agents/
│   │   │   ├── AgentsPage.tsx            # Agent observability page
│   │   │   ├── AgentStatusGrid.tsx      # Card per agent (status, last event, latency)
│   │   │   ├── AgentEventLog.tsx        # Full event stream (filterable by agent)
│   │   │   ├── AgentDetailDrawer.tsx    # Per-agent deep dive
│   │   │   └── PipelineFlow.tsx        # Visual pipeline flow diagram
│   │   │
│   │   ├── health/
│   │   │   ├── HealthPage.tsx           # System health page
│   │   │   ├── ApiHealthGrid.tsx       # Per-API health cards
│   │   │   ├── LatencyChart.tsx        # API latency over time
│   │   │   ├── ErrorLog.tsx           # Recent errors table
│   │   │   └── UptimeCard.tsx         # Uptime percentage per service
│   │   │
│   │   ├── learning/
│   │   │   ├── LearningPage.tsx        # AI learning page
│   │   │   ├── DriftAlert.tsx          # Concept drift banner
│   │   │   ├── ConfidenceGauge.tsx    # Model confidence per symbol
│   │   │   ├── RewardHistory.tsx      # Reward scoring timeline
│   │   │   └── DecisionLog.tsx       # AI decision history with reasoning
│   │   │
│   │   ├── chart/
│   │   │   ├── ChartPage.tsx         # Trading chart page
│   │   │   ├── SymbolSelector.tsx    # Symbol search + select
│   │   │   ├── TimeframeBar.tsx     # TF selector strip
│   │   │   ├── TradingChart.tsx      # Lightweight charts wrapper
│   │   │   └── ChartSidebar.tsx     # Indicators / annotations panel
│   │   │
│   │   └── settings/
│   │       ├── SettingsPage.tsx       # Settings page
│   │       ├── BrokerSettings.tsx   # MT5 connection config
│   │       ├── RiskLimitsForm.tsx   # Risk parameter form
│   │       ├── StrategyConfig.tsx   # Strategy on/off toggles
│   │       └── ApiKeysForm.tsx     # Crucix / HKU / Telegram keys
│   │
│   └── shared/                         # Cross-cutting components
│       ├── BotStatusBadge.tsx         # LIVE / IDLE / PAUSED badge
│       ├── SessionBadge.tsx           # London / NY / Asian / Overlap badge
│       ├── DirectionBadge.tsx         # BUY / SELL badge
│       ├── StrategyBadge.tsx          # Strategy name chip
│       ├── AgentBadge.tsx             # Colored agent name
│       ├── PnlCell.tsx               # Green/red P&L value cell
│       ├── TimeCell.tsx              # Formatted timestamp cell
│       └── PriceCell.tsx             # Formatted price cell
│
├── hooks/                              # Custom React hooks
│   ├── useDataTable.ts                # TanStack Table wrapper (existing)
│   ├── useAppShell.ts                 # AppShell context hook
│   ├── useWebSocket.ts               # WebSocket event subscription
│   ├── useKeyboard.ts                # Keyboard shortcut hook (⌘K)
│   ├── useCommandPalette.ts          # Command palette state
│   └── usePriceFeed.ts              # Real-time price subscription
│
├── lib/                               # Utilities and API layer
│   ├── api/                          # API client layer
│   │   ├── client.ts                # Base fetch wrapper (auth, error handling)
│   │   ├── status.ts               # /api/status
│   │   ├── trades.ts              # /api/trades
│   │   ├── risk.ts               # /api/risk
│   │   ├── signals.ts            # /api/signals
│   │   ├── events.ts             # /api/events
│   │   ├── intelligence.ts      # /api/intelligence
│   │   ├── learning.ts          # /api/learning
│   │   └── health.ts            # /api/health
│   │
│   ├── swr.ts                      # Keep existing SWR hooks (backwards compat)
│   ├── format.ts                   # Formatting utilities (existing)
│   ├── ws.ts                       # WebSocket client
│   └── utils.ts                    # General utilities
│
└── types/                           # Shared TypeScript types
    ├── api.ts                      # API response shapes
    ├── bot.ts                      # Bot status, trade, signal types
    ├── agent.ts                    # Agent event types
    └── risk.ts                     # Risk / guard types
```

### 1.2 Separation of Concerns

| Layer | Rule | Examples |
|---|---|---|
| `ui/primitives` | Zero business logic. Only presentation. | `Button`, `Badge`, `Dialog` |
| `ui/data-display` | Display logic only (formatting, sorting prep). No API calls. | `StatCard`, `DataTable`, `Gauge` |
| `features/*` | Composes `ui/*`. Contains business logic. Calls SWR hooks. | `SignalsTable`, `GuardPipeline` |
| `hooks/*` | State and side effects. No JSX. | `useDataTable`, `useKeyboard` |
| `lib/api/*` | Pure fetch functions. Returns typed data. No React. | `getTrades()`, `postPause()` |

---

## PART 2 — DESIGN SYSTEM

### 2.1 Color System

All colors are CSS custom properties defined in `globals.css`. Never use raw hex in components.

```css
/* ── Surfaces ─────────────────────────────────────────────────────────── */
--bg:              #0D0D0F;   /* Page background */
--bg-2:            #141417;   /* Card / panel surface */
--bg-3:            #1C1C21;   /* Elevated surface, input backgrounds */
--bg-4:            #252529;   /* Hover state, active tabs */
--bg-5:            #2E2E34;   /* Tooltip, popover */

/* ── Borders ─────────────────────────────────────────────────────────── */
--border:           rgba(255, 255, 255, 0.07);   /* Default border */
--border-subtle:    rgba(255, 255, 255, 0.04);   /* Dividers */
--border-active:    rgba(240, 180, 41, 0.35);    /* Active / focus ring */
--border-focus:     var(--accent);               /* Keyboard focus */

/* ── Text ───────────────────────────────────────────────────────────── */
--text-1:           #F4F4F5;   /* Primary text */
--text-2:           rgba(244, 244, 245, 0.55);  /* Secondary text */
--text-3:           rgba(244, 244, 245, 0.30);  /* Tertiary / placeholder */
--text-disabled:    rgba(244, 244, 245, 0.18);  /* Disabled state */

/* ── Semantic Status Colors ──────────────────────────────────────────── */
--positive:         #30D158;   /* Profit, gain, pass, healthy */
--positive-dim:     rgba(48, 209, 88, 0.12);
--negative:         #FF453A;   /* Loss, fail, error, critical */
--negative-dim:     rgba(255, 69, 58, 0.12);
--warning:          #FF9F0A;   /* Warn, caution, near-limit */
--warning-dim:      rgba(255, 159, 10, 0.12);
--info:             #64D2FF;   /* Info, neutral event, session */
--info-dim:         rgba(100, 210, 255, 0.10);
--accent:           #00DC82;   /* Primary action, live indicator, links */

/* ── Instrument Colors ───────────────────────────────────────────────── */
--buy:              #30D158;   /* Long / buy direction */
--sell:             #FF453A;   /* Short / sell direction */
--hold:             #FF9F0A;   /* Neutral / hold signal */

/* ── Agent Accent Colors ─────────────────────────────────────────────── */
--agent-crucix:     #64D2FF;
--agent-market:     #32ADE6;
--agent-analysis:  #A0A0A8;
--agent-strategy:  #30D158;
--agent-neural:    #BF5AF2;
--agent-council:   #FF9F0A;
--agent-risk:      #FF453A;
--agent-execution: #F0B429;
--agent-trade-mgr: #64D2FF;
--agent-learning:  #30D158;
--agent-debate:   #BF5AF2;
--agent-exposure: #FF9F0A;
--agent-memory:    #64D2FF;

/* ── Chart Colors ────────────────────────────────────────────────────── */
--chart-1:  #64D2FF;   /* Cyan — primary data series */
--chart-2:  #30D158;   /* Green — positive series */
--chart-3:  #F0B429;   /* Gold — benchmark / reference */
--chart-4:  #BF5AF2;   /* Purple — secondary series */
--chart-5:  #FF9F0A;   /* Orange — tertiary series */
```

### 2.2 Typography Scale

```css
/* Font Families */
--font-mono:  'IBM Plex Mono', 'Fira Code', monospace;   /* All numeric data */
--font-ui:    'IBM Plex Sans Condensed', system-ui;        /* UI labels, nav */
--font-data:  'JetBrains Mono', 'Fira Code', monospace;    /* Dense table data */

/* Scale (font-size / line-height) */
--text-xs:   10px / 1.4;   /* Table column headers, badges */
--text-sm:   12px / 1.5;   /* Secondary labels, timestamps */
--text-base: 14px / 1.5;   /* Body text, form inputs */
--text-lg:   16px / 1.4;   /* Card titles, section headers */
--text-xl:   20px / 1.3;   /* Page titles */
--text-2xl:  24px / 1.2;   /* Large stat values */
--text-3xl:  32px / 1.1;   /* Hero KPI values (equity) */
--text-4xl:  44px / 1.0;   /* Mission control main equity display */
```

**Rule:** All numeric values (prices, P&L, counts, percentages) MUST use `font-family: var(--font-mono)`. Never use proportional fonts for numbers.

### 2.3 Spacing System

```css
--space-1:  4px;    /* Icon-to-text gap, tight list items */
--space-2:  8px;    /* Intra-component padding */
--space-3:  12px;   /* Card padding, button padding */
--space-4:  16px;   /* Between related elements */
--space-5:  24px;   /* Section gap, modal padding */
--space-6:  32px;   /* Between major sections */
--space-7:  48px;   /* Page-level padding top/bottom */
```

**Rule:** Use `gap` via Tailwind for flex/grid layouts. Use `--space-*` for padding (cards, panels, modals).

### 2.4 Border Radius

```css
--radius-sm:  3px;    /* Badges, small chips */
--radius-md:  4px;    /* Buttons, inputs, small cards */
--radius-lg:  8px;    /* Modals, drawers, large panels */
--radius-xl:  12px;   /* Page-level containers */
--radius-pill: 999px; /* Pills, status badges */
```

### 2.5 Shadows & Elevation

```css
--shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.4);   /* Card resting */
--shadow-md:  0 4px 12px rgba(0, 0, 0, 0.5);   /* Dropdowns, popovers */
--shadow-lg:  0 8px 32px rgba(0, 0, 0, 0.6);   /* Modals, drawers */
--shadow-glow-positive: 0 0 8px rgba(48, 209, 88, 0.4);   /* Live/positive glow */
--shadow-glow-negative: 0 0 8px rgba(255, 69, 58, 0.4);  /* Negative/warn glow */
--shadow-glow-accent:   0 0 8px rgba(0, 220, 130, 0.4);   /* Accent glow */
```

### 2.6 Animation Guidelines

```css
/* Duration */
--duration-instant: 50ms;   /* Hover color */
--duration-fast:    100ms;  /* Active states */
--duration-normal:  200ms;  /* Panel open/close */
--duration-slow:    400ms;  /* Page transitions */

/* Easing */
--ease-out:    cubic-bezier(0.16, 1, 0.3, 1);   /* UI transitions */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* Bouncy (rare use) */
```

**Rule:** Animations serve function (feedback, state change communication), never decoration. No infinite loops except pulse indicators for live states.

### 2.7 Component Philosophy

| Pattern | When to use | Rule |
|---|---|---|
| `Panel` | Grouping related content with a title | Has border, bg-2, rounded-md |
| `Drawer / Sheet` | Deep-dive on a row item without leaving page | Opens from right, 480px wide |
| `Command Palette` | Global actions without navigation | ⌘K to open, fuzzy search |
| `Toast` | Transient feedback (trade filled, error) | Bottom-right, 3s auto-dismiss |
| `Alert Banner` | Persistent warning/error (drift, daily loss cap) | Top of page, dismissable |
| `Skeleton` | Loading state while data fetches | Match exact shape of content |
| `Empty State` | No data for a view | Show meaningful message + action |

---

## PART 3 — CORE SCREENS

### 3.1 Mission Control (`/dashboard`)

**Purpose:** At-a-glance situational awareness. What is the bot doing right now?

```
┌─────────────────────────────────────────────────────────────────┐
│ [Header: PulseTrade logo]  [Equity $X] [Daily P&L ±X] [LIVE ●]  │
├────────┬────────────────────────────────────────────────────────┤
│        │  KPI ROW: Equity | Balance | Daily P&L | Open | Loops │
│ Side   ├────────────────────────────────────────────────────────┤
│ bar    │  MACRO STRIP: Session [●LONDON] VIX [14.2] Reg [TREND]│
│        ├────────────────────────────┬───────────────────────────┤
│  Nav   │  POSITIONS (open trades)  │  AGENT EVENTS (live feed) │
│        │  Symbol | Dir | P&L | TP  │  [timestamp] agent: event  │
│        │  [Click row → TradeDrawer] │  [Click row → AgentDrawer] │
│        ├────────────────────────────┴───────────────────────────┤
│        │  QUICK ACTIONS: [Pause] [Resume] [Force Scan]          │
└────────┴────────────────────────────────────────────────────────┘
```

**Key UX decisions:**
- Equity is the largest text on screen (44px, `--text-4xl`)
- Bot LIVE indicator pulses green in header
- Positions table has only 4 columns — too much data is distracting
- Agent events feed scrolls live; new events prepend
- All row clicks open a drawer for details (no modal interruptions)

### 3.2 Signals Intelligence (`/dashboard/signals`)

**Purpose:** Understand every generated signal before execution.

```
┌─────────────────────────────────────────────────────────────────┐
│  Signals Intelligence                    [Filter: All|Signals] │
├─────────────────────────────────────────────────────────────────┤
│  [Search: symbol, strategy...]         [Sort: Conf|Rank|Time]  │
├─────────────────────────────────────────────────────────────────┤
│  ● BUY  EUR/USD  ICT Silver Bullet  conf [████████░░] 82%     │
│  ● SELL  XAU/USD  ICT Orderflow     conf [██████░░░░] 67%     │
│  ● HOLD  GBP/USD  SMA Crossover     conf [████░░░░░░] 48%     │
├─────────────────────────────────────────────────────────────────┤
│  ← Click any row → Signal Detail Drawer opens from right         │
└─────────────────────────────────────────────────────────────────┘
```

**Signal Detail Drawer contains:**
- Symbol, direction, strategy name, confidence score
- Reasoning: Why was this signal generated? (bull/bear case text)
- Entry price, TP1–TP4 levels
- Structural break level, session filter
- Rank vs other signals in current scan
- "Execute Now" or "Block" action buttons

### 3.3 Trades / Positions (`/dashboard/trades`)

**Purpose:** Monitor open trades and review closed ones.

**Sub-tabs:** Active | Closed | All

```
┌─────────────────────────────────────────────────────────────────┐
│  Trades & Positions           [Active] [Closed] [All]           │
├─────────────────────────────────────────────────────────────────┤
│  ACTIVE:                                                        │
│  Symbol | Dir | Entry | Current | P&L | TP Progress | Age      │
│  EUR/USD | BUY | 1.0842 | 1.0851 | +$142 | [██░░░] 1/3 TP hits | 2h │
│                                                               [↗] │
│  Closed (last 5):                                               │
│  Symbol | Exit | P&L | Duration | Strategy | Closed at          │
│  GBP/USD | 1.2651 | +$89  | 4h  | ICT Silver | 14:32           │
└─────────────────────────────────────────────────────────────────┘
```

**Trade Detail Drawer:**
- Full trade lifecycle: Entry → modifications → TP/SL hits
- TP1/TP2/TP3/TP4 hit markers with timestamps
- Breakeven trigger event
- Commission cost, net P&L after fees
- Trade review notes (from Learning system)

### 3.4 Risk & Exposure (`/dashboard/risk`)

**Purpose:** Never breach a limit. See all guard states.

```
┌─────────────────────────────────────────────────────────────────┐
│  Risk & Exposure                                                │
├─────────────────────────────────────────────────────────────────┤
│  POSITION SLOTS:  [████████░░░░] 8/10  80% utilisation         │
│                                                                │
│  DRAWDOWN:  [Gauge: -2.3% / -5% max]  ⚠ NEAR LIMIT             │
│                                                                │
│  GUARD PIPELINE:                    Status      Current / Limit │
│  ● Max Open Trades         PASS     8 trades    / 10           │
│  ● Daily Loss Cap          WARN     -$340       / -$500        │
│  ● Spread Check            PASS     1.2 pip     / 3.0 max      │
│  ● Market Hours            PASS     London      / active session │
│  ● Correlation Gate       PASS     0.72        / 0.85 max      │
│  ● News Blackout           PASS     —           / active       │
│  ● Equity Gate            PASS     $12,450     / $10,000 min  │
│                                                                │
│  RECENTLY BLOCKED:                                              │
│  GBP/USD BUY blocked: Daily loss cap reached (-$480/$500)      │
│  EUR/CHF SELL blocked: Spread too wide (4.2 pip / 3.0 max)    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 Agent Observability (`/dashboard/agents`)

**Purpose:** See every agent's health, latency, and recent output.

```
┌─────────────────────────────────────────────────────────────────┐
│  Agent Observability                                            │
├─────────────────────────────────────────────────────────────────┤
│  ● CRUCIX    [█████ alive]  latency 42ms   last: macro snapshot│
│  ● MARKET    [█████ alive]  latency 18ms   last: candles       │
│  ● ANALYSIS  [█████ alive]  latency 31ms   last: regime detect │
│  ● STRATEGY  [█████ alive]  latency 89ms   last: 3 signals    │
│  ● NEURAL    [███░░ warn]   latency 204ms  last: model infer  │
│  ● COUNCIL   [█████ alive]  latency 150ms  last: 1 approved    │
│  ● RISK      [█████ alive]  latency 12ms   last: lot sizing    │
│  ● EXECUTION [█████ alive]  latency 8ms    last: order filled  │
│                                                                │
│  AGENT EVENT LOG (all agents, newest first):                   │
│  14:32:01  EXECUTION  ORDER FILLED  EUR/USD BUY  +0.01 lot    │
│  14:32:00  RISK       LOT SIZED    0.01 lot / $142 risk       │
│  14:31:58  COUNCIL    APPROVED     Signal #4412  conf 82%     │
│  14:31:55  STRATEGY   SIGNAL       ICT OB  GBP/USD  conf 76%  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 System Health (`/dashboard/health`)

**Purpose:** Is everything up? What broke?

```
┌─────────────────────────────────────────────────────────────────┐
│  System Health                              All Systems Operational │
├─────────────────────────────────────────────────────────────────┤
│  MT5 BROKER     [██████████] Connected   latency 12ms     🟢   │
│  SUPABASE DB    [██████████] Connected   latency 28ms     🟢   │
│  CRUCIX API     [██████░░░░] Degraded   latency 380ms     🟡   │
│  TELEGRAM       [██████████] OK          latency 90ms     🟢   │
│  HKU MARKET     [██████░░░░] Circuit Brk latency —        🟡   │
│                                                                │
│  ERROR LOG (last 24h):                                         │
│  14:28  CRUCX  HTTP 503  Macro feed unavailable              │
│  13:45  MT5    Timeout  Order request stalled (retry OK)     │
│  11:02  DB     Slow    Query > 2s (campaign scan)            │
│                                                                │
│  UPTIME:  MT5 99.8% | Supabase 99.99% | Crucix 94.2%         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.7 Learning / AI (`/dashboard/learning`)

**Purpose:** Understand what the bot is learning and where it doubts itself.

```
┌─────────────────────────────────────────────────────────────────┐
│  Learning & AI                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ⚠ CONCEPT DRIFT DETECTED  Model accuracy dropped 12% in 48h │
│     [View Drift Report]  [Retrain Model]                       │
│                                                                │
│  MODEL CONFIDENCE (per symbol):                               │
│  EUR/USD  [████████░░] 82%  ▲ stable   trained 2 days ago    │
│  GBP/USD  [██████░░░░] 61%  ▼ falling  trained 5 days ago    │
│  XAU/USD  [██████████] 91%  ▲ rising   trained 1 day ago     │
│                                                                │
│  RECENT REWARDS:                                               │
│  +0.12  EUR/USD BUY  TP hit  (pattern matched ICT OB)         │
│  -0.08  GBP/USD SELL SL hit  (false breakout)                 │
│  +0.05  XAU/USD HOLD confidence correctly maintained          │
│                                                                │
│  DECISION LOG (last 20):                                      │
│  14:30  NEURAL  infer  GBP/USD HOLD  conf 58%  reason: ...   │
│  14:29  RISK    block  GBP/USD BUY   reason: daily cap near  │
│  14:28  STRATEGY signal GBP/USD SELL  conf 71%  reason: ...   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.8 Settings (`/dashboard/settings`)

**Purpose:** Configure the bot without restarting.

```
┌─────────────────────────────────────────────────────────────────┐
│  Settings                                                      │
├──────────────────────────┬──────────────────────────────────────┤
│  BROKER CONNECTION       │  RISK LIMITS                        │
│  MT5 Status: Connected   │  Max Open Trades    [10    ]         │
│  Account: 12345678       │  Max Daily Loss     [-$500 ]         │
│  Server: PU Prime Live   │  Max Position Size  [0.50 lot]       │
│  [Disconnect] [Reconnect] │  Spread Max (pips)  [3.0    ]       │
│                          │  Guard Pipeline  [●ON] [○OFF]        │
├──────────────────────────┼──────────────────────────────────────┤
│  STRATEGY               │  INTELLIGENCE SUITE                  │
│  ICT Silver Bullet  [●]  │  Crucix Macro      [●ON] [○OFF]     │
│  ICT Orderflow      [●]  │  VIX Regime Filter [●ON] [○OFF]     │
│  SMA Crossover     [○]  │  News Blackout     [●ON] [○OFF]     │
│  LSTM Neural       [●]  │  HKU Marketplace   [○ON] [○OFF]     │
│                          │  [Save All Changes]                  │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## PART 4 — UX PRINCIPLES

### 4.1 Operator-First Rules

1. **Most critical info above the fold** — equity, daily P&L, bot state visible without scrolling on any dashboard page
2. **Zero-click monitoring** — live data streams without user interaction; no "refresh" buttons
3. **Action cost is high** — Pause/Resume are destructive by design; require confirmation but are one tap
4. **Escalation hierarchy** — PASS → WARN → FAIL; every visual treatment maps to this
5. **Context without navigation** — drawer-based detail views; operator never loses their place

### 4.2 Density Rules

1. **Data tables: 30-50 rows per page** — not 10, not 100
2. **Card content fits without scrolling** — if a card needs scroll, it needs redesign
3. **Sidebar: icon + label, no icons-only** — never guess what an icon means under pressure
4. **KPI row: 6 items max per page** — more = split across rows or use tabs
5. **Stat cards: value + label only in compact views** — trend line or sparkline is a bonus

### 4.3 Interaction Patterns

| Action | Pattern | Why |
|---|---|---|
| View details of a row | Click → Drawer opens from right | Stay in context |
| Sort a table column | Click header → toggle asc/desc/none | Standard expectation |
| Filter a table | Search input + filter chips | Fast, repeatable |
| Change bot state | Button in header → confirmation dialog | Prevent accidents |
| Navigate pages | Sidebar (desktop) / bottom nav (mobile) | Persistent location |
| Global action | ⌘K command palette | Power user speed |
| Error feedback | Toast (bottom-right) | Non-blocking |
| Persistent warning | Alert banner (top of page) | Can't be missed |

### 4.4 Color = Status, Not Decoration

Every color in the UI communicates one of five states:

| Color | Meaning |
|---|---|
| `--positive` (#30D158) | Healthy, profit, pass, live, connected |
| `--negative` (#FF453A) | Loss, fail, error, critical, blocked |
| `--warning` (#FF9F0A) | Near limit, degraded, warn state |
| `--info` (#64D2FF) | Session, neutral event, informational |
| `--accent` (#00DC82) | Primary action, links, focus |

**Rule:** Never use `--text-2` for important status. Never use green for a warning. Never use red for a positive event.

### 4.5 Drawer-Based Deep Dives

All detail views open as right-side drawers (480px wide Sheet component). No modal dialogs for viewing data. Modals are only for: confirmation (pause bot), destructive actions, and forms.

```
[Table Row] --click--> [Drawer: 480px Sheet from right]
                          - Header: "EUR/USD Trade Detail"
                          - Close: X or click outside
                          - Scroll: internal scroll if content is tall
                          - Actions: bottom of drawer (fixed)
```

---

## PART 5 — COMPONENT SYSTEM

### 5.1 DataTable (TanStack-based)

The most critical component. Must be consistent across all pages.

**API:**
```tsx
<DataTable
  data={signals}
  columns={signalColumns}  // ColumnDef<Signal>[]
  pageSize={30}
  searchable={true}        // Shows search bar
  filterable={true}       // Shows filter chips slot
  sortable={true}         // All columns sortable
  paginated={true}        // Shows pagination controls
  selectable={false}      // Checkbox column (for bulk actions)
  onRowClick={(row) => openDrawer(row)}  // Opens detail drawer
  emptyMessage="No signals match your filters"
/>
```

**Visual spec:**
- Border: `1px solid var(--border)`, border-radius: `--radius-lg`
- Header row: `bg: var(--bg-3)`, font: `--font-mono`, 9px, uppercase, letter-spacing 0.06em
- Data rows: `bg: var(--bg-2)`, hover `bg: var(--bg-3)`, transition 100ms
- Selected row: `bg: var(--bg-4)`, left border `2px solid var(--accent)`
- Sticky header on scroll
- Pagination: show range "1–30 of 342" + first/prev/next/last page buttons

### 5.2 StatCard

```tsx
interface StatCardProps {
  label: string;        // "Equity", "Daily P&L"
  value: string;        // "$12,450.00", "+$340.00"
  subValue?: string;    // Secondary info: "$12,110.00" (prev close)
  color?: "positive" | "negative" | "neutral" | "accent";
  trend?: "up" | "down" | "flat";  // Arrow indicator
  size?: "sm" | "md" | "lg";
  pulse?: boolean;       // Live indicator dot
}
```

### 5.3 Gauge (Radial / Fill)

Used for: drawdown, confidence, utilization.

```tsx
interface GaugeProps {
  value: number;         // Current value (e.g., -2.3)
  max: number;          // Maximum (e.g., -5.0)
  label: string;        // "Max Drawdown"
  type: "fill" | "radial";
  thresholds?: {
    warnAt: number;     // e.g., -3.0 → amber
    criticalAt: number; // e.g., -4.5 → red
  };
}
```

### 5.4 EventFeed (Live Scroll)

```tsx
interface EventFeedProps {
  events: AgentEvent[];
  maxHeight?: string;   // "320px" — scrolls internally
  filterByAgent?: string;
  onEventClick?: (event: AgentEvent) => void;
  autoScroll?: boolean; // New events prepend, auto-scroll to top
}
```

**Visual:** Each event is a single line: `[timestamp] [AgentBadge] [message]`. Color-coded by agent. Max 200 events kept in memory (older ones dropped).

### 5.5 CommandPalette (⌘K)

Global command bar. Opens with `⌘K` (Mac) / `Ctrl+K` (Windows).

Commands:
- `pause` — Pause the bot
- `resume` — Resume the bot
- `scan now` — Force a scan cycle
- `goto signals` — Navigate to signals page
- `goto trades` — Navigate to trades page
- `settings` — Open settings
- `dark mode` / `light mode` — Theme toggle

### 5.6 DrawerPanel (Sheet from Radix)

```tsx
interface DrawerPanelProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;  // Fixed at bottom (actions)
  width?: "sm" | "md" | "lg";  // 360 / 480 / 640
}
```

---

## PART 6 — CODE EXAMPLES

### 6.1 AppShell Layout

```tsx
// components/app/AppShellLayout.tsx
"use client";

import { useAppShell } from "@/hooks/useAppShell";
import { Sidebar } from "@/components/app/Sidebar";
import { MobileNav } from "@/components/app/MobileNav";
import { Header } from "@/components/app/Header";
import { CommandPalette } from "@/components/app/CommandPalette";

export function AppShellLayout({ children }: { children: React.ReactNode }) {
  const { status, isRunning } = useAppShell();

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* Desktop sidebar — hidden on mobile */}
      <div className="hidden lg:flex flex-col" style={{ width: "var(--sidebar-w)" }}>
        <Sidebar />
      </div>

      {/* Main content column */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top header bar */}
        <Header isRunning={isRunning} status={status} />

        {/* Page content — scrolls independently */}
        <main className="flex-1 overflow-y-auto p-5" style={{ padding: "var(--space-5)" }}>
          {children}
        </main>
      </div>

      {/* Mobile bottom nav */}
      <div className="lg:hidden">
        <MobileNav />
      </div>

      {/* Global command palette */}
      <CommandPalette />
    </div>
  );
}
```

### 6.2 Mission Control Page

```tsx
// components/features/mission-control/MissionControl.tsx
"use client";

import { useAppShell } from "@/hooks/useAppShell";
import { KpiRow } from "./KpiRow";
import { MacroStrip } from "./MacroStrip";
import { PositionsCard } from "./PositionsCard";
import { AlertsFeed } from "./AlertsFeed";
import { QuickActions } from "./QuickActions";
import { EventFeed } from "@/components/ui/data-display/event-feed";

export function MissionControl() {
  const { status, isRunning, openTrades, events, intelligence } = useAppShell();

  return (
    <div className="flex flex-col gap-4">
      {/* KPI row — always visible */}
      <KpiRow
        equity={status?.equity ?? 0}
        balance={status?.balance ?? 0}
        dailyPnl={status?.daily_pnl ?? 0}
        openCount={openTrades.length}
        loopCount={status?.loop_count ?? 0}
        isRunning={isRunning}
      />

      {/* Macro context strip */}
      <MacroStrip intelligence={intelligence} />

      {/* Main grid: positions + events */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Open positions — click to expand */}
        <PositionsCard
          trades={openTrades}
          onTradeClick={(trade) => { /* open TradeDetailDrawer */ }}
        />

        {/* Live agent events feed */}
        <EventFeed
          events={events}
          maxHeight="340px"
          onEventClick={(event) => { /* open AgentDrawer */ }}
        />
      </div>

      {/* Critical alerts — only shows when there are warnings */}
      <AlertsFeed />

      {/* Quick actions */}
      <QuickActions isRunning={isRunning} />
    </div>
  );
}
```

### 6.3 Signals Table

```tsx
// components/features/signals/SignalsTable.tsx
"use client";

import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-display/data-table";
import { useDataTable } from "@/hooks/useDataTable";
import { SignalDetailDrawer } from "./SignalDetailDrawer";
import { DirectionBadge } from "@/components/shared/DirectionBadge";
import { ConfidenceBar } from "./ConfidenceBar";
import { fmtDateTime } from "@/lib/format";

type Signal = {
  id: string;
  symbol: string;
  direction: "BUY" | "SELL" | "HOLD";
  strategy: string;
  confidence: number;  // 0-100
  created_at: string;
  entry_price: number;
  tp_levels: number[];
};

export function SignalsTable({ signals }: { signals: Signal[] }) {
  const [selected, setSelected] = useState<Signal | null>(null);

  const columns: ColumnDef<Signal>[] = [
    {
      id: "direction",
      header: "",
      cell: ({ row }) => <DirectionBadge direction={row.original.direction} />,
      size: 40,
    },
    {
      id: "symbol",
      header: "Symbol",
      accessorKey: "symbol",
      cell: ({ row }) => (
        <span className="font-mono font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
          {row.original.symbol}
        </span>
      ),
    },
    {
      id: "strategy",
      header: "Strategy",
      accessorKey: "strategy",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-2)" }}>{row.original.strategy}</span>
      ),
    },
    {
      id: "confidence",
      header: "Confidence",
      cell: ({ row }) => (
        <ConfidenceBar value={row.original.confidence} />
      ),
    },
    {
      id: "entry",
      header: "Entry",
      accessorKey: "entry_price",
      cell: ({ row }) => (
        <span className="font-mono" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
          {row.original.entry_price.toFixed(5)}
        </span>
      ),
    },
    {
      id: "created_at",
      header: "Time",
      accessorKey: "created_at",
      cell: ({ row }) => (
        <span style={{ color: "var(--text-3)", fontSize: "var(--text-sm)" }}>
          {fmtDateTime(row.original.created_at)}
        </span>
      ),
    },
  ];

  const { table, globalFilter, setGlobalFilter } = useDataTable({
    data: signals,
    columns,
    pageSize: 30,
  });

  return (
    <>
      <DataTable
        table={table}
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        filterPlaceholder="Search symbol, strategy…"
        onRowClick={(row) => setSelected(row)}
        noResults="No signals found"
      />

      <SignalDetailDrawer
        signal={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
      />
    </>
  );
}
```

### 6.4 Shared StatCard Component

```tsx
// components/ui/data-display/stat-card.tsx
import { cn } from "@/lib/utils";

type ColorVariant = "positive" | "negative" | "neutral" | "accent";
type TrendVariant = "up" | "down" | "flat";

interface StatCardProps {
  label: string;
  value: string;
  subValue?: string;
  color?: ColorVariant;
  trend?: TrendVariant;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
  className?: string;
}

const COLOR_MAP: Record<ColorVariant, string> = {
  positive: "var(--positive)",
  negative: "var(--negative)",
  neutral:  "var(--text-2)",
  accent:   "var(--accent)",
};

const TREND_ICON: Record<TrendVariant, string> = {
  up:   "arrow_upward",
  down: "arrow_downward",
  flat: "horizontal_rule",
};

export function StatCard({
  label,
  value,
  subValue,
  color = "neutral",
  trend,
  size = "md",
  pulse,
  className,
}: StatCardProps) {
  const textColor = COLOR_MAP[color];
  const fontSize = size === "lg" ? "var(--text-3xl)"
                : size === "sm" ? "var(--text-xl)"
                : "var(--text-2xl)";

  return (
    <div
      className={cn("flex flex-col gap-1 rounded-md p-3", className)}
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border)",
      }}
    >
      {/* Label */}
      <span
        className="font-ui uppercase tracking-widest"
        style={{
          color: "var(--text-3)",
          fontSize: "var(--text-xs)",
          letterSpacing: "0.08em",
        }}
      >
        {label}
      </span>

      {/* Value row */}
      <div className="flex items-end gap-2">
        {/* Live pulse dot */}
        {pulse && (
          <span
            className="mb-1"
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: textColor,
              animation: "pulse-dot 2s ease-in-out infinite",
              boxShadow: `0 0 6px ${textColor}`,
            }}
          />
        )}

        <span
          className="font-mono font-bold leading-none"
          style={{ color: textColor, fontSize, fontFamily: "var(--font-mono)" }}
        >
          {value}
        </span>

        {/* Trend icon */}
        {trend && (
          <span
            className="material-symbols-outlined mb-0.5"
            style={{
              fontSize: 14,
              color: color === "positive" ? "var(--positive)"
                   : color === "negative" ? "var(--negative)"
                   : "var(--text-3)",
              fontVariationSettings: "'FILL' 1, 'wght' 400",
            }}
          >
            {TREND_ICON[trend]}
          </span>
        )}
      </div>

      {/* Sub value */}
      {subValue && (
        <span
          className="font-mono"
          style={{ color: "var(--text-3)", fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}
        >
          {subValue}
        </span>
      )}
    </div>
  );
}
```

### 6.5 KpiRow Component

```tsx
// components/features/mission-control/KpiRow.tsx
"use client";

import { StatCard } from "@/components/ui/data-display/stat-card";

interface KpiRowProps {
  equity: number;
  balance: number;
  dailyPnl: number;
  openCount: number;
  loopCount: number;
  isRunning: boolean;
}

function formatCurrency(v: number, sign = false) {
  return (sign && v > 0 ? "+" : "") +
    "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
}

export function KpiRow({ equity, balance, dailyPnl, openCount, loopCount, isRunning }: KpiRowProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
      {/* Equity — largest, accent color */}
      <StatCard
        label="Equity"
        value={formatCurrency(equity)}
        color="accent"
        size="lg"
        className="xl:col-span-2"
      />

      <StatCard
        label="Balance"
        value={formatCurrency(balance)}
        color="neutral"
      />

      <StatCard
        label="Daily P&L"
        value={formatCurrency(dailyPnl, true)}
        color={dailyPnl >= 0 ? "positive" : "negative"}
        trend={dailyPnl > 0 ? "up" : dailyPnl < 0 ? "down" : "flat"}
        size="md"
      />

      <StatCard
        label="Open"
        value={String(openCount)}
        color={openCount > 0 ? "neutral" : "neutral"}
      />

      <StatCard
        label="Bot"
        value={isRunning ? "LIVE" : "IDLE"}
        color={isRunning ? "positive" : "negative"}
        pulse={isRunning}
        size="sm"
      />
    </div>
  );
}
```

---

## PART 7 — MIGRATION PLAN

### Phase 0 — Stabilize the Foundation (1-2 hours)

Before any redesign work, fix what's broken:

1. **Fix `guards.py` import bug** — `current_session` missing import (blocking heartbeat)
2. **Remove duplicate files** — `ui/data-table.tsx` (lowercase) vs `ui/DataTable.tsx` (uppercase); consolidate into one
3. **Remove placeholder pages** — `brain/page.tsx`, `markets/page.tsx`, `signals/page.tsx` have placeholder text; either build them or redirect to a meaningful page
4. **Audit all API routes** — verify all `/api/*` routes return correct JSON shapes; fix any 500 errors

**Files to delete:**
- `components/brain/brain-page.tsx` (placeholder)
- `components/markets/markets-page.tsx` (placeholder)
- `components/signals/signals-page.tsx` (placeholder)
- `web/src/components/ui/data-table.tsx` (duplicate, lowercase)
- `web/src/components/ui/table.tsx` (check if redundant)

### Phase 1 — Design System Infrastructure (2-3 hours)

Establish the foundation before building any features.

**1.1 Consolidate globals.css**
- Merge all token definitions (already done in current `globals.css`)
- Add the missing tokens from this spec (`--positive`, `--negative`, `--warning`, `--info`)
- Add shadow tokens
- Add animation duration/easing tokens

**1.2 Set up Tailwind config**
```js
// tailwind.config.ts
module.exports = {
  darkMode: ["class"],  // or 'media' if no class-based toggle
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { /* map all CSS vars */ },
      fontFamily: {
        mono: ["var(--font-mono)"],
        ui:   ["var(--font-ui)"],
        data: ["var(--font-data)"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

**1.3 Install shadcn primitives needed**
```bash
# Radix-backed components (use these, not the CLI to add them)
# Install manually, copy source from shadcn repo:
# - sheet (Drawer)
# - toast
# - tooltip
# - command (for ⌘K palette)
```

**1.4 Create `types/api.ts`**
- Define all API response types in one place
- Export `BotStatus`, `Trade`, `Signal`, `AgentEvent`, `RiskData`, `HealthStatus`

### Phase 2 — AppShell & Navigation (3-4 hours)

The shell is used on every page — build it once, perfectly.

**2.1 Refactor `AppShell.tsx`**
- Extract `AppShellLayout` (pure layout, no business logic)
- Extract `Sidebar` (nav items, active state)
- Extract `MobileNav` (bottom tab bar)
- Extract `Header` (bot status, live clock, session badge)
- Add `CommandPalette` hook (`useKeyboard` for ⌘K)

**2.2 Navigation items (after redesign, 8 pages):**
```
/dashboard         → Mission Control     (icon: dashboard)
/dashboard/signals → Signals Intelligence (icon: radar)
/dashboard/trades  → Trades & Positions   (icon: trending_up)
/dashboard/risk    → Risk & Exposure      (icon: shield)
/dashboard/agents  → Agent Observability  (icon: smart_toy)
/dashboard/health  → System Health        (icon: heart_monitor)
/dashboard/learning → Learning & AI       (icon: psychology)
/dashboard/settings → Settings           (icon: settings)
```

### Phase 3 — Build the Component Library (4-6 hours)

In priority order:

| # | Component | Why first |
|---|---|---|
| 1 | `StatCard` | Used on every page |
| 2 | `DataTable` | Used on 5+ pages |
| 3 | `EventFeed` | Used on Mission Control + Agents |
| 4 | `DrawerPanel` (Sheet) | Used for all detail views |
| 5 | `DirectionBadge` / `StatusBadge` | Cross-cutting |
| 6 | `Gauge` | Used on Risk + Learning |
| 7 | `CommandPalette` | UX speed feature |

### Phase 4 — Feature Pages (in order, 1 page per session)

| Week | Page | Notes |
|---|---|---|
| 1 | Mission Control | Highest traffic — must be perfect |
| 1 | Trades / Positions | Split into Active + History tabs |
| 2 | Signals Intelligence | New page (currently placeholder) |
| 2 | Risk & Exposure | Enhance existing |
| 3 | Agent Observability | Enhance existing AgentsTab |
| 3 | System Health | Enhance existing HealthTab |
| 4 | Learning / AI | Enhance existing LearningPage |
| 4 | Settings | Already exists — polish only |

### Phase 5 — Polish & Performance (1-2 hours)

1. **Remove all `console.log` statements** from production code
2. **Add loading skeletons** to every async view — never a spinner for content
3. **Add error boundaries** — every page has a graceful error fallback
4. **Verify mobile layout** — sidebar collapses to bottom nav, no horizontal scroll
5. **Test at 1920×1080 and 1366×768** — common trading monitor resolutions
6. **Keyboard navigation** — Tab through tables, Enter to open drawer, Escape to close

### Avoiding Breaking Backend Integration

The backend is a black box. The frontend must adapt to it.

**Rule 1:** Never change API route handlers. Only consume them.
**Rule 2:** If an API shape changes, update `types/api.ts` and the consuming SWR hook. Components don't change.
**Rule 3:** Test each page against the real backend before considering it done.
**Rule 4:** Keep the existing SWR hooks in `lib/swr.ts` working. Add new ones alongside, don't replace until the replacement is verified.

---

## PART 8 — STYLE DIRECTION REFERENCE

### 8.1 Visual Identity

**Reference:** Bloomberg Terminal × Vercel Dashboard × Linear

- Dark background with subtle surface elevation (--bg, --bg-2, --bg-3)
- Monospace numbers everywhere — financial data must be monospace
- Tight line heights for data density
- Minimal border radius (3-4px) — professional, not playful
- Color used only for status communication
- Accent green (`--accent: #00DC82`) for primary CTAs and live indicators

### 8.2 What to Avoid

| Anti-pattern | Why |替代 |
|---|---|---|
| Generic dashboard gradient backgrounds | Looks like a template | Solid `--bg` with elevation |
| Rounded cards (12px+) | Too soft for trading platform | `--radius-lg` max (8px) |
| Colorful chart backgrounds | Distracting | Transparent charts on `--bg-2` |
| Decorative animations | Wasteful, distracting | Functional only (pulse for live) |
| Avatars / user photos | Irrelevant for bot UI | Agent initials with accent color |
| Emoji anywhere | Not professional | Material Symbols icons only |

### 8.3 Font Usage Map

| Context | Font | Weight | Size |
|---|---|---|---|
| KPI values (equity, P&L) | `font-mono` | Bold (700) | 32-44px |
| Table data (prices, counts) | `font-mono` | Regular (400) | 12px |
| Table column headers | `font-ui` | Bold (700) | 9px uppercase |
| Page titles | `font-ui` | Semi-bold (600) | 20px |
| Nav items | `font-ui` | Medium (500) | 14px |
| Body text / labels | `font-ui` | Regular (400) | 14px |
| Secondary labels | `font-ui` | Regular (400) | 12px |
| Timestamps | `font-mono` | Regular (400) | 11px |
