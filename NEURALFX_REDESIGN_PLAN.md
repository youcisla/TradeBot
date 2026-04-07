# NeuralFX TradingBot — Full Redesign Master Plan
> Complete audit of all 160+ files. Every feature catalogued. Zero dropped.

---

## AUDIT: What Exists Today

### Python Backend (20,545 lines across 50+ files)

**Agents (14 agents)**
| File | Lines | Purpose |
|------|-------|---------|
| `agents/crucix_agent.py` | ~200 | Macro intelligence wrapper; runs IntelligenceSweep + CrucixClient |
| `agents/market_agent.py` | ~180 | MT5 candle/tick fetch, ATR/RSI/SMA calc, news blackout check |
| `agents/analysis_agent.py` | 274 | Regime detection, trend direction, session classification |
| `agents/strategy_agent.py` | 339 | Orchestrates all strategies, returns ranked Signal list |
| `agents/council_agent.py` | 754 | 4-expert algorithmic gate (ICT, DanialFX, Traditional, World) |
| `agents/risk_agent.py` | 1216 | Lot sizing, spread check, daily loss cap, Kelly sizing |
| `agents/execution_agent.py` | 365 | Opens orders via MT5, TP lot splits, GuardPipeline gate |
| `agents/trade_manager.py` | 638 | Monitors open trades, TP hits, SL moves, breakeven logic |
| `agents/learning_agent.py` | 621 | Reward scoring, confidence updates, WFO, daily snapshots |
| `agents/logging_agent.py` | ~200 | DB event log, CSV journal, Telegram daily summary |
| `agents/debate_agent.py` | 280 | Bull/bear LLM debate gate (DEBATE_ENABLED flag) |
| `agents/exposure_agent.py` | 352 | Portfolio exposure directive |
| `agents/memory_agent.py` | ~150 | Cross-session memory blocks via `bot_memory` table |
| `agents/guards.py` | 265 | GuardPipeline: 7 independent pre-execution safety guards |
| `agents/exposure_coach.py` | ~100 | Concentration/correlation advisor |
| `agents/reflector.py` | ~120 | Post-trade BM25 episodic reflection utility |
| `agents/signal_postmortem.py` | ~100 | Trade outcome classifier (TRUE_POS / FALSE_POS / REGIME_MISMATCH) |
| `agents/deepseek_strategy.py` | 891 | DeepSeek LLM strategy via OpenAI-compat API |

**Strategies (5)**
| File | Purpose |
|------|---------|
| `strategies/ict_strategy.py` (544L) | ICT/SMC engine: FVGs, OBs, sweeps, killzones, multi-TF |
| `strategies/unified_strategy.py` | Combines all strategies, deduplicates by (symbol, direction) |
| `strategies/sma_crossover.py` | Legacy SMA crossover (reference, not in main pipeline) |
| `strategies/base_strategy.py` | Abstract base class |
| `strategies/plugin_loader.py` | Dynamic plugin loader from STRATEGY_PLUGINS env var |

**Models / ML (8 files)**
| File | Purpose |
|------|---------|
| `models/lgbm_ensemble.py` (295L) | LightGBM ensemble with SHAP explainability |
| `models/lgbm_price_model.py` (461L) | Price direction LightGBM model |
| `models/lgbm_train_state.py` | Training state persistence |
| `models/garch_regime.py` | GARCH(1,1) volatility regime detection |
| `models/ict_models.py` (408L) | ICT dataclasses: FVG, OrderBlock, SwingPoint, Liquidity |
| `models/market_data.py` | MarketContext, Candle, Indicator dataclasses |
| `models/signal.py` | Signal dataclass |
| `models/trade.py` | Trade dataclass |
| `models/agent_mesh.py` | Agent state mesh bus |

**Utilities (17 files)**
| File | Purpose |
|------|---------|
| `utils/kalman_filter.py` | Kalman price smoother (pre-LSTM preprocessing) |
| `utils/dynamic_position_sizer.py` (239L) | Kelly + ATR-based position sizing |
| `utils/correlation_gate.py` (239L) | Currency correlation checker |
| `utils/concept_drift_detector.py` (272L) | ML model drift detection |
| `utils/mesh_bus.py` | Agent message bus, coherence tracking |
| `utils/orchestration_profiler.py` | Loop timing profiler, adaptive worker scaling |
| `utils/opportunity_lifecycle.py` | Per-symbol opportunity state machine |
| `utils/symbol_event_tracker.py` | Last candle/signal/trade timestamps per symbol |
| `utils/tool_system.py` (530L) | Autonomous tool system (self-improvement) |
| `utils/skill_manager.py` | SKILL.md reader/applier |
| `utils/telegram_bot.py` (436L) | Polling bot: /status, /graph, /kill, /pause, /resume |
| `utils/telegram_reports.py` | PnL curve PNG builder for Telegram |
| `utils/terminal_ui.py` | Rich live terminal dashboard |
| `utils/hedge_stripper.py` | LLM hedge-language stripper |
| `utils/candle_server.py` (253L) | HTTP candle server for dashboard charts |
| `utils/walk_forward_optimizer.py` | WFO engine |
| `utils/helpers.py` | Session detection, market hours, timezone helpers |
| `utils/memory.py` | Memory utilities |
| `utils/crypto.py` | AES-256-CBC credential encryption |
| `utils/ops_doctor.py` | System health diagnostics |

**Broker (3 files)**
| File | Purpose |
|------|---------|
| `broker/mt5_connector.py` (610L) | Full MT5 integration: connect, orders, positions, tick data |
| `broker/mock_connector.py` (317L) | Full mock for backtesting/dev |
| `broker/connector.py` | Abstract BrokerConnector interface |

**Filters (3 files)**
| File | Purpose |
|------|---------|
| `filters/intelligence_sweep.py` (347L) | FRED + yfinance + EIA async sweep, delta scoring |
| `filters/crucix_client.py` (360L) | HTTP client for external Crucix server |
| `filters/data_validator.py` | Market data validation, stuck quote detection |

**Features (2 files)**
| File | Purpose |
|------|---------|
| `features/microstructure.py` | Bid/ask advance time, volume imbalance from MT5 ticks |
| `features/macro_features.py` | FRED-derived ML features for LSTM/LGBM |

**Backtesting (8 files)**
| File | Purpose |
|------|---------|
| `backtesting/engine.py` (290L) | Backtest engine with commission/slippage |
| `backtesting/walk_forward.py` | Walk-forward runner |
| `backtesting/walk_forward_optimizer.py` | WFO parameter optimizer |
| `backtesting/mock_broker.py` (317L) | Realistic mock for backtests |
| `backtesting/report.py` (256L) | SQN + Sharpe + drawdown report generator |
| `backtesting/data_downloader.py` | Historical OHLCV downloader |
| `backtesting/baseline_benchmarks.py` | Buy-and-hold + random baselines |
| `backtesting/factor_library.py` | WorldQuant-style alpha factors |
| `backtesting/public_api_intake.py` | Public API data ingestion |
| `backtesting/research_intake.py` | Research signal intake |

**LLM (1 file)**
| File | Purpose |
|------|---------|
| `llm/openrouter_gateway.py` | OpenRouter unified LLM gateway with fallback chain |

**Database (1 file, 1,716 lines)**
Tables: `trades`, `trade_scores`, `strategy_confidence`, `agent_events`, `bot_commands`, `bot_status`, `broker_accounts`, `bot_memory`, `symbol_faults`, `trade_commits`, `sessions`

**Config (2 files, 806 lines)**
`settings.py` — 60+ configurable parameters across 15 categories
`symbols.py` — Active symbol list

**Scripts (7 files)**
`backtest.py`, `first_run_wizard.py`, `import_public_apis.py`, `ops_doctor.py`, `replay_session.py`, `reset_dashboard_user.py`, `reset_learning_state.py`

**Research (6 files)**
`candidate_backlog.json`, `curated_sources.json/.yaml`, `promotion_checklist.json/.yaml`, `scoring_rubric.json/.yaml`

---

### Next.js Dashboard (web/)

**Pages (7)**
| Route | Page | Key Features |
|-------|------|-------------|
| `/` | Landing | Login redirect |
| `/login` | Auth | NextAuth credentials |
| `/dashboard` | Command Center | BotStatus, AgentPipeline, OpenTrades, AgentFeed, Equity sparkline, CommandPanel |
| `/dashboard/trades` | Trade Book | Full trade table with PnL, symbol filter, pagination |
| `/dashboard/markets` | Market Intel | TradingChart (lightweight-charts), symbol/TF selector, ICT overlays, live events |
| `/dashboard/analytics` | Performance | KPI cards, equity curve SVG, trade breakdown, strategy stats |
| `/dashboard/brain` | Agent Brain | Per-agent event stream, full event log |
| `/dashboard/risk` | Risk Console | Risk parameters, drawdown gauges, WFO status, emergency stop |
| `/dashboard/settings` | Settings | Broker info, trading params, symbol list, Crucix toggle |

**Components (17)**
`AgentFeed`, `BotStatusBar`, `ChartSymbolSelector`, `CommandPanel`, `ConfirmModal`, `DashBottomNav`, `DashHeader`, `DashNav`, `DashSidebar`, `EquityCurve`, `OpenTradesTable`, `PageHeader`, `PaginationControls`, `SymbolFilter`, `TerminalButton`, `TerminalInput`, `TimeframeSelector`, `TradingChart`

**API Routes (14)**
`/api/analytics`, `/api/auth`, `/api/broker/accounts`, `/api/candles`, `/api/candles/fibonacci`, `/api/candles/trades`, `/api/commands`, `/api/events`, `/api/ict`, `/api/learning`, `/api/risk`, `/api/skills`, `/api/status`, `/api/tools`, `/api/trades`, `/api/world`

**Current Design System**
- Font: SF Pro (system) + SF Mono (code) + JetBrains Mono (terminal)
- Theme: iOS dark mode color palette (pure black `#000`, `#1C1C1E` surfaces)
- Tailwind: 0px border radius everywhere (sharp corners), synthetic terminal palette
- Layout: fixed sidebar (240px) + header (64px) + bottom nav (mobile)

---

## REDESIGN PLAN

### Philosophy

The current design is split-personality: the Tailwind config says "synthetic terminal" but the actual components use iOS system UI patterns with Apple system fonts. The result is neither terminal nor iOS — it's a confused middle ground.

**New direction: Precision Instrument**
Think Bloomberg Terminal crossed with a Formula 1 pit display crossed with a top-tier quant desk. Dark charcoal base. Sharp amber/gold accent (replacing blue as primary). Monospaced data everywhere. Every pixel earns its place. Zero decoration that doesn't carry information.

Concretely:
- **Font:** `IBM Plex Mono` for ALL data/numbers (replaces SF Mono), `IBM Plex Sans Condensed` for labels/nav
- **Colors:** Near-black `#0D0D0F` base, `#1A1A1E` surfaces, `#F0B429` amber as primary (up), `#FF453A` red (down), `#64D2FF` cyan (active/info), `#30D158` green (confirms)
- **Layout:** Tighter, denser. Less padding. Data-first. Numbers big and prominent.
- **No decorative gradients** — structural only (sidebar separator, active state glow)
- **No rounded corners except on pills/badges** — sharp everywhere else
- **Motion:** Subtle only. Counter animations on KPIs at load. Pulse on live indicators.

---

### Phase 1 — Foundation (Do First, Everything Depends On It)

#### 1A. Design System Reset (`web/src/app/globals.css` + `tailwind.config.js`)

**globals.css — complete replacement:**
```css
/* IBM Plex fonts from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Sans+Condensed:wght@300;400;500;600;700&display=swap');

:root {
  /* Base surfaces */
  --bg:           #0D0D0F;   /* page background */
  --bg-2:         #141417;   /* card / panel */
  --bg-3:         #1C1C21;   /* input / elevated card */
  --bg-4:         #252529;   /* hover state */
  --border:       rgba(255, 255, 255, 0.07);
  --border-active: rgba(240, 180, 41, 0.35);

  /* Typography */
  --text-1:       #F4F4F5;   /* primary text */
  --text-2:       rgba(244, 244, 245, 0.55); /* secondary */
  --text-3:       rgba(244, 244, 245, 0.30); /* disabled/hint */

  /* Semantic colors */
  --gold:         #F0B429;   /* primary accent / long / up */
  --gold-dim:     rgba(240, 180, 41, 0.15);
  --red:          #FF453A;   /* short / down / danger */
  --red-dim:      rgba(255, 69, 58, 0.12);
  --cyan:         #64D2FF;   /* info / active / live */
  --cyan-dim:     rgba(100, 210, 255, 0.10);
  --green:        #30D158;   /* confirmed / success */
  --green-dim:    rgba(48, 209, 88, 0.10);
  --purple:       #BF5AF2;   /* neural / AI */
  --orange:       #FF9F0A;   /* council / warning */

  /* Agent accent map */
  --agent-crucix:       #64D2FF;
  --agent-market:       #32ADE6;
  --agent-analysis:     #F4F4F5;
  --agent-strategy:     #30D158;
  --agent-neural:       #BF5AF2;
  --agent-council:      #FF9F0A;
  --agent-risk:         #FF453A;
  --agent-execution:    #F0B429;
  --agent-trade-mgr:    #64D2FF;
  --agent-learning:     #30D158;
  --agent-logging:      rgba(244,244,245,0.25);
  --agent-debate:       #BF5AF2;
  --agent-exposure:     #FF9F0A;
  --agent-memory:       #64D2FF;

  /* Fonts */
  --font-mono:  'IBM Plex Mono', 'Fira Code', monospace;
  --font-ui:    'IBM Plex Sans Condensed', system-ui, sans-serif;

  /* Layout */
  --sidebar-w:  220px;
  --header-h:   52px;
  --radius-sm:  3px;
  --radius-md:  4px;
  --radius-pill: 999px;
}
```

**tailwind.config.js — update tokens to match new system**

---

#### 1B. Layout Shell

**`DashHeader.tsx` — redesign:**
- Height: `52px` (down from 64px — reclaim vertical space)
- Left: `NeuralFX` wordmark in IBM Plex Mono, weight 600, gold color + `◆` prefix
- Center: live ticker strip — 3 key indicators inline: `EURUSD 1.0842 ▲0.03%` · `XAUUSD 2,341.20 ▼0.12%` · `BTC 67,240 ▲1.2%` (auto-refresh 10s)
- Right: Bot state badge (`● LIVE` / `⏸ PAUSED` / `✗ STOPPED`) + equity chip + Telegram icon
- No decorative gradient in header — solid `var(--bg-2)` with 1px bottom border

**`DashSidebar.tsx` — redesign:**
- Width: `220px`
- Nav items: uppercase condensed label + icon (Google Material Symbols outlined)
- Active: left 2px gold border + `var(--gold-dim)` background
- Section separators: just 8px spacing + `var(--text-3)` 11px label (no horizontal rules)
- Bottom: bot health indicator (colored dot + "All systems nominal" or error text)
- Remove gradient background — solid `var(--bg-2)` with 1px right border

**`DashBottomNav.tsx` — mobile only, 5 items max, redesign to match new tokens**

---

### Phase 2 — Dashboard Pages (Rebuild Each Page)

#### 2A. `/dashboard` — Command Center (Main Page)

**Current problems:** Cramped agent pipeline, equity sparkline too small, no real-time feel, command panel buried.

**New layout (desktop, 3-column grid):**
```
┌─────────────────────────────────────────────────────────────────────┐
│ ROW 1: Bot Status Bar — full width, 4 KPI chips inline             │
│ Balance | Equity | Daily P&L | Open Trades                         │
├──────────────────────────────────┬──────────────────────────────────┤
│ COL 1 (60%)                      │ COL 2 (40%)                      │
│ Agent Pipeline (vertical flow)   │ Open Trades table                │
│ Each agent: name + status dot +  │ Compact: symbol, dir, PnL        │
│ last action text                 │                                  │
├──────────────────────────────────┴──────────────────────────────────┤
│ ROW 3: Live Agent Feed (full width, scrolling log, last 50 events) │
├──────────────────────────────────┬──────────────────────────────────┤
│ COL 1 (50%): Quick Commands      │ COL 2 (50%): Equity Sparkline    │
│ [PAUSE] [CLOSE ALL] [KILL]       │ 24h equity curve, current value  │
└──────────────────────────────────┴──────────────────────────────────┘
```

**Key component upgrades:**
- **Bot Status Bar:** Each KPI chip has: label (tiny, text-3), value (large, mono), trend arrow. Gold = positive, red = negative, cyan = neutral.
- **Agent Pipeline:** Replace horizontal node diagram with vertical card stack. Each agent card: colored left border (agent color), agent name, live status dot (pulsing green = active, grey = idle, red = error), last event message truncated. Click to jump to Brain page filtered to that agent.
- **Open Trades table:** Inline PnL with live update (poll 5s). Direction shown as colored pill (`LONG` gold, `SHORT` red). Entry price mono font. Duration shown as `2h 14m`.
- **Live Feed:** Dark `var(--bg-2)` card. Each row: `[agent]` colored tag + message + timestamp. Auto-scroll to bottom. Pause-on-hover. Color-coded by level (info=text-2, warn=orange, error=red).
- **Command Panel:** Three big action buttons in a row. PAUSE = cyan outline, CLOSE ALL = orange outline, KILL = red filled. Each shows confirm modal before executing.
- **Equity Sparkline:** Replace SVG homebrew with a proper area chart using the existing `lightweight-charts` library (already in package.json). Gradient fill below line.

---

#### 2B. `/dashboard/trades` — Trade Book

**Current problems:** Table is functional but aesthetically flat. No visual hierarchy. Status column useless for open trades. No quick stats header.

**New design:**
- **Top bar:** 4 stat chips: Total Trades | Win Rate | Avg Win | Avg Loss (computed from visible filter)
- **Filters row:** Status toggle (ALL / OPEN / CLOSED) + Symbol multiselect + Strategy filter + Date range
- **Table redesign:**
  - `Direction` → colored pill (`LONG` gold background, `SHORT` red background)
  - `Symbol` → uppercase mono font, bold
  - `Entry` → mono font right-aligned
  - `P&L` → mono font, green if positive, red if negative, right-aligned with sign
  - `Duration` → human format (show as `3h 42m` for open, `1d 4h` for closed)
  - `Strategy` → pill badge (ICT = cyan, DeepSeek = purple, SMA = grey, Ensemble = orange)
  - `Status` → only shown for closed trades; shows close reason pill (SL_HIT = red, TP1 = green, TP2 = gold, etc.)
  - Remove: raw timestamps (replace with relative time for recent, absolute for old)
- **Row click:** Expand inline to show: SL/TP levels, confidence at entry, council verdict, lot size, commission, MAE/MFE if available
- **Pagination:** Keep existing PaginationControls component but restyle

---

#### 2C. `/dashboard/markets` — Market Intel

**Current problems:** Chart is good (lightweight-charts) but the surrounding UI is weak. Symbol selector is basic. ICT overlays are not visible in the UI.

**New design:**
- **Toolbar:** Symbol selector (prominent, large mono text) + Timeframe row (M5 M15 H1 H4 D1 W1 buttons) + toggle buttons for overlays (FVG, OB, Sweeps, Fibonacci)
- **Chart:** Keep TradingChart.tsx but:
  - Set background to `var(--bg)` to blend with page
  - Update crosshair color to gold
  - ICT FVG overlays: bullish = semi-transparent green rectangle, bearish = semi-transparent red rectangle, labeled
  - Trade entry/exit markers: upward triangle (LONG, gold) / downward triangle (SHORT, red)
  - Add volume histogram at bottom (semi-transparent, auto-hiding when too small)
- **Right panel (240px):** Live market stats for selected symbol:
  - Bid/Ask with spread
  - Session (London/NY/Asia badge)
  - Daily range (high/low bar)
  - RSI gauge (semicircle)
  - Trend direction indicator
  - Last ICT signal if any (with confidence %)
- **Bottom strip:** Recent agent events filtered to selected symbol only

---

#### 2D. `/dashboard/analytics` — Performance

**Current problems:** Custom SVG sparklines are fragile and low-quality. KPI layout is not scannable. No comparison view.

**New design:**
- **Top row (5 KPI cards):** Daily P&L | Weekly P&L | Monthly P&L | Win Rate | Profit Factor — each card: large number (mono, colored), sparkline underneath (7-day), trend arrow
- **Main section (2-col):**
  - Left (60%): Equity curve — proper area chart via lightweight-charts, 1m/3m/6m/1y/All toggle, show drawdown periods in red below the zero line
  - Right (40%): Trade distribution — bar chart by strategy (LGBM, ICT, DeepSeek) + bar chart by symbol
- **Lower section:** Trade log table (compact version of /trades, last 20 closed only) + performance heatmap by weekday × session (color intensity = avg P&L)
- **Stats row at bottom:** Total trades | Avg hold time | Avg win/loss ratio | Sharpe (if available) | SQN (if available from last backtest)

---

#### 2E. `/dashboard/brain` — Agent Brain

**Current problems:** Flat list of events. Hard to monitor specific agents. No way to see agent health at a glance.

**New design:**
- **Agent health grid (top):** 9 agent cards (one per pipeline agent). Each: agent name, colored dot (green=healthy/active in last 5min, amber=slow/warn, red=error/stale), last event preview, event count last hour. Click to filter feed below.
- **Feed section:** Full-width scrolling log.
  - Left sidebar (180px): agent filter checklist — click agents to show/hide their events in the feed
  - Level filter: ALL / INFO / WARN / ERROR buttons
  - Search input (filter by message text)
  - Feed rows: `HH:MM:SS` timestamp + `[AGENT]` colored pill + message + optional data preview (collapsed JSON, click to expand)
- **Active filter shows highlighted** — if filtering to "council" only, all other agent rows are dimmed not hidden (context preservation)
- **Auto-scroll:** Pause on hover/scroll-up, resume button appears when paused

---

#### 2F. `/dashboard/risk` — Risk Console

**Current problems:** Static rows of settings. No visual gauges. Emergency stop section not prominent enough.

**New design:**
- **Emergency stop banner (top, full-width):** Only visible when `emergency_stop = true`. Red filled banner. "EMERGENCY STOP ACTIVE — [reason]". Pulsing border.
- **Gauge row (4 gauges):**
  - Daily Loss Used: arc gauge, 0 to max_daily_loss_pct, fills red as approaches limit
  - Total Drawdown: arc gauge
  - Open Position Count: number gauge, n/max
  - Equity at Risk: percentage number, colored
- **Risk parameters table:** Two-column: parameter name | current value (mono). Grouped: Position Sizing, Drawdown Limits, Trade Limits, Guard Pipeline settings.
- **WFO status card:** Last run date, overfitting score, parameter stability, emergency cap status (on/off), next scheduled run
- **Guard status grid:** 7 guards in a 2-col grid. Each: guard name + pass/fail indicator (green check / red X) + last check time. Shows which guard is currently most restrictive.
- **Learning system card:** Win rate trend (mini sparkline), confidence per strategy table, last retrain date, next scheduled retrain.

---

#### 2G. `/dashboard/settings` — Settings

**Current problems:** Read-only display of settings. No way to change anything from the UI. Crucix section is misleadingly labeled.

**New design:**
- **Broker card:** MT5 connection status (live indicator), account number/server/type display, connect/disconnect button. Show last connected time.
- **Trading parameters (editable):** Risk per trade slider (0.5% - 5%), Max daily loss input, Max concurrent trades stepper. "Save changes" button that writes to DB and triggers bot reload. All changes require confirmation modal.
- **Symbol management:** Draggable list of active symbols. Toggle each on/off. "Add symbol" input.
- **Strategy configuration:** Toggle each strategy (ICT, DeepSeek, SMA, plugins). Council enabled toggle. Council mode (blocking / advisory) selector.
- **Intelligence Suite card** (was "Crucix"): IntelligenceSweep status, last sweep time, sources enabled/disabled toggle, FRED key status, yfinance status.
- **Notifications card:** Telegram bot token status, chat ID, noise filter toggle, rate limit display.
- **Danger zone:** Reset learning state button, clear symbol faults button. Both require typing "CONFIRM" before executing.

---

### Phase 3 — Component Library Rebuilds

#### 3A. Core Card Component

All cards use the same base:
```tsx
// Replaces all the inline style={{ background, border, borderRadius... }} scattered everywhere
<Card variant="default|elevated|ghost" accent="gold|cyan|red|none">
  <CardHeader>...</CardHeader>
  <CardBody>...</CardBody>
</Card>
```

Implementation: `src/components/ui/Card.tsx`

#### 3B. Stat Chip / KPI Component

```tsx
<StatChip
  label="Daily P&L"
  value={+234.50}
  format="currency"
  trend="+2.3%"
  sparkline={[...7 values]}
/>
```

Shows: label (small, text-3) → value (large, mono, colored by positive/negative) → trend arrow + % → mini sparkline

Implementation: `src/components/ui/StatChip.tsx`

#### 3C. Agent Pill / Badge

```tsx
<AgentBadge agent="council" />          // → orange pill "COUNCIL"
<AgentBadge agent="risk" active />      // → red pill with pulse dot
<LevelBadge level="warn" />             // → orange "WARN"
<DirectionBadge direction="LONG" />     // → gold "LONG"
<StrategyBadge strategy="ICT" />        // → cyan "ICT"
```

Implementation: `src/components/ui/Badges.tsx`

#### 3D. Data Table Component

Reusable sortable table with: mono-font data cells, colored P&L, expandable rows, loading skeleton.

Implementation: `src/components/ui/DataTable.tsx`

#### 3E. Arc Gauge

SVG arc gauge for risk display. 0–100%, configurable thresholds (green/amber/red zones).

Implementation: `src/components/ui/ArcGauge.tsx`

#### 3F. Feed / Event Log Component

Virtualized scrolling list. Pause-on-hover. Agent filter sidebar. Level filter. Search.

Implementation: `src/components/ui/EventFeed.tsx`

#### 3G. Command Button (danger variant)

Large action button with built-in confirm flow. No separate ConfirmModal needed for most cases.

Implementation: `src/components/ui/CommandButton.tsx`

---

### Phase 4 — API Layer Updates

No breaking changes. Just additions:

| Route | Change | Reason |
|-------|--------|--------|
| `/api/status` | Add `guards_status` array to response | Risk page guard grid |
| `/api/analytics` | Add `by_strategy`, `by_symbol`, `by_weekday_session` aggregates | Analytics page charts |
| `/api/events` | Add `?agent=` and `?level=` query params | Brain page filtering |
| `/api/risk` | Add `guard_results` and `wfo_status` to response | Risk page WFO card |
| `/api/trades` | Add `?expand=true` for inline trade details | Trades page row expand |
| NEW: `/api/symbols/active` | Returns current active symbol list | Settings page symbol manager |
| NEW: `/api/settings` (POST) | Writes settings changes to DB | Settings page editable params |

---

### Phase 5 — Polish

#### 5A. Animation Budget
- KPI counter animation: count up from 0 to value over 600ms on first load
- Agent status dot: pulsing CSS animation for "active" state (2s cycle)
- Feed rows: fade-in-up on new entry (`opacity: 0 → 1`, `translateY: 4px → 0`, 200ms)
- Page transitions: none (avoid latency perception)
- Chart: already animated by lightweight-charts

#### 5B. Loading States
- Skeleton loaders (not spinners) for all data cards — match exact layout of loaded state
- `src/components/ui/Skeleton.tsx` — reusable shimmer block

#### 5C. Empty States
Each page has a designed empty state (no trades yet / no events / market closed) — not just blank space.

#### 5D. Mobile Responsiveness
- Bottom nav (existing DashBottomNav) stays, restyled
- Stack all 2-col layouts to 1-col on mobile
- Agent pipeline: horizontal scroll on mobile (don't stack — too tall)
- Chart: full-width on mobile, toolbar collapses to icon-only

---

### Phase 6 — Python Backend (No Architecture Changes — Only Targeted Fixes)

The Python pipeline is solid. These are targeted improvements only, not rewrites.

| File | What to change |
|------|---------------|
| `agents/guards.py` | Add `get_status()` method returning dict of each guard's last result — consumed by new `/api/risk` endpoint |
| `database/db.py` | Add `get_guards_status()`, `get_wfo_status()`, `get_trades_expanded(id)`, `get_events_filtered(agent, level)`, `get_analytics_by_strategy()` methods |
| `config/settings.py` | Add `SETTINGS_EDITABLE_VIA_UI` bool and `save_setting(key, value)` function |
| `filters/crucix_client.py` / `filters/intelligence_sweep.py` | Expose `get_source_status()` for settings page — which sources are live/failing |
| `web/src/app/api/settings/route.ts` | New POST endpoint — validates, writes to DB settings table, triggers bot config reload |
| `web/src/app/api/symbols/active/route.ts` | New GET/POST endpoint for symbol management |

---

## COMPLETE FEATURE INVENTORY — NOTHING DROPPED

This section guarantees every existing feature survives the redesign.

### Features Preserved (must survive in new design)

**Trading Engine**
- [x] MT5 connection with mock fallback
- [x] Multi-symbol scanning with cooldown per session (London/NY faster, Asia slower)
- [x] Weekend-only crypto mode (BTCUSD, 3-TF ICT: M15+H4, H1+D1, H4+W1)
- [x] BTC priority scanning (always scanned first)
- [x] Symbol auto-disable after consecutive IPC failures
- [x] MT5 auto-reconnect on connection loss
- [x] Adaptive worker count based on loop timing
- [x] Hard budget limits per phase (scan/rank/exec/iteration)
- [x] Instant entry mode (top signal bypasses council for speed)
- [x] Fast lane mode (first N signals run hard risk check only)
- [x] Deferred entry system (re-promotes signals that failed soft risk checks)
- [x] Scan-all → rank → execute pipeline (not first-match)
- [x] Signal deduplication by (symbol, direction)
- [x] Event-driven rescan on new candle (optional)

**Agent Pipeline**
- [x] All 14 agents preserved as-is in Python
- [x] Council: 4-expert gate (ICT, DanialFX, Traditional, World)
- [x] Council modes: blocking / advisory (with confidence haircut)
- [x] GuardPipeline: 7 guards in order
- [x] Debate agent (DEBATE_ENABLED flag)
- [x] Exposure agent + ExposureCoach
- [x] Memory agent (cross-session bot_memory table)
- [x] Learning agent: reward scoring, confidence updates, BM25 reflector
- [x] Walk-forward optimizer (weekly on Sundays)
- [x] Adaptive retraining (emergency caps on overfitting detection)
- [x] Signal postmortem classification
- [x] Daily/weekly/monthly performance snapshots

**Strategies**
- [x] ICT/SMC engine: FVGs, Order Blocks, liquidity sweeps, killzones, multi-TF
- [x] DeepSeek LLM strategy
- [x] SMA crossover (kept for reference)
- [x] Dynamic strategy plugin loading
- [x] UnifiedStrategy combining all active strategies
- [x] Unified strategy deduplication

**ML / Intelligence**
- [x] LightGBM ensemble with SHAP explainability
- [x] LightGBM price model
- [x] GARCH volatility regime detection
- [x] Kalman filter price smoother
- [x] Concept drift detection
- [x] IntelligenceSweep: FRED (22 indicators) + yfinance (8 assets) + EIA + GDELT
- [x] Microstructure features from MT5 ticks
- [x] Macro features from FRED for LGBM
- [x] OpenRouter LLM gateway with fallback chain

**Risk**
- [x] Dynamic position sizing (ATR + Kelly)
- [x] Correlation gate (currency correlation check)
- [x] Daily loss cap enforcement
- [x] Spread check (reject on wide spread)
- [x] Emergency stop with configurable caps
- [x] WFO-triggered emergency caps
- [x] Hard post-entry risk check (fast lane close on full-reject)

**Trade Management**
- [x] TP1/TP2/TP3 lot-split structure
- [x] Breakeven logic (move SL to entry after TP1 hit)
- [x] Trailing stop support
- [x] Partial close on TP hits
- [x] Periodic reconciliation with MT5 (every N loops)
- [x] Startup reconciliation (crash recovery)
- [x] StatePersistence crash recovery

**Ops / Infrastructure**
- [x] Telegram bot: /status, /graph, /kill, /pause, /resume
- [x] Telegram noise filter (dedup + rate limit)
- [x] PnL curve PNG for Telegram /graph
- [x] Rich terminal UI (live dashboard in console)
- [x] Candle HTTP server (dashboard chart data)
- [x] Command queue (DB-driven: kill, pause, resume, close_all, close_trade, skill, tool)
- [x] Autonomous tool system (self-improvement)
- [x] Skill manager (SKILL.md read/apply)
- [x] Symbol fault state persistence (DB)
- [x] Session tracking (session ID, uptime, version)
- [x] Daily/weekly/monthly summary reports via Telegram
- [x] CSV trade journal export
- [x] Loop telemetry logging (KPI snapshot every N loops)
- [x] Orchestration profiler (bottleneck detection)
- [x] Graceful shutdown (SIGINT/SIGTERM)
- [x] First-run wizard
- [x] Ops doctor (system health check)
- [x] AES-256-CBC credential encryption in DB
- [x] NextAuth authentication for dashboard

**Dashboard**
- [x] All 7 pages (Command Center, Trades, Markets, Analytics, Brain, Risk, Settings)
- [x] All 14 API routes
- [x] TradingChart with lightweight-charts (candlestick + volume + ICT overlays + trade markers + fibonacci)
- [x] Live agent feed
- [x] Open trades table
- [x] Bot status bar
- [x] Command panel (pause, resume, close_all, kill)
- [x] Broker account management UI
- [x] Equity curve chart
- [x] Risk parameters display
- [x] WFO status display
- [x] Learning/confidence display
- [x] Settings display
- [x] Mobile bottom nav
- [x] Responsive layout

**Research / Backtesting**
- [x] Backtest engine with commission + slippage
- [x] Walk-forward runner + optimizer
- [x] SQN + Sharpe + drawdown report
- [x] Baseline benchmarks (buy-and-hold, random)
- [x] Factor library (WorldQuant-style alphas)
- [x] Historical data downloader
- [x] Research intake pipeline
- [x] Candidate backlog + curated sources + scoring rubric
- [x] Promotion checklist for new signals

**.claude / DevOps**
- [x] 11 SKILL.md files
- [x] .claude/commands/ slash commands (deploy, fix-issue, review)
- [x] .claude/agents/ (code-reviewer, security-auditor)
- [x] .claude/rules/ (api-conventions, code-style, testing)
- [x] CI workflow (GitHub Actions)
- [x] Dockerfile
- [x] Incident recovery playbook
- [x] start.ps1, clear-cache.ps1, update-crucix.ps1

---

## Build Order

Execute in this exact sequence to avoid breaking the working bot while redesigning:

```
WEEK 1 — Foundation
  Day 1:  1A — Design tokens (globals.css + tailwind.config.js)
  Day 1:  3A — Card component, 3B — StatChip, 3C — Badges
  Day 2:  1B — Header + Sidebar + BottomNav redesign
  Day 2:  3D — DataTable, 3E — ArcGauge
  Day 3:  3F — EventFeed, 3G — CommandButton, 3H — Skeleton

WEEK 2 — Dashboard Pages
  Day 4:  2A — Command Center (main dashboard)
  Day 5:  2B — Trade Book
  Day 6:  2C — Market Intel
  Day 7:  2D — Analytics

WEEK 3 — Remaining Pages + API
  Day 8:  2E — Agent Brain
  Day 9:  2F — Risk Console
  Day 10: 2G — Settings
  Day 11: 4A — API additions (status, analytics, events, risk, trades)
  Day 12: 4B — New API routes (symbols/active, settings POST)

WEEK 4 — Backend Touches + Polish
  Day 13: 6A — guards.py get_status(), db.py new query methods
  Day 14: 5A — Animations (counter, pulse, fade-in)
  Day 15: 5B/5C — Skeleton loaders + empty states
  Day 16: 5D — Mobile pass + final QA
```

---

## Files That Need Zero Changes

These are working and well-designed — don't touch them during the redesign:

```
All Python files in:  agents/, strategies/, models/, utils/, broker/, 
                      filters/, features/, backtesting/, llm/, state/
main.py               (pipeline is solid)
database/db.py        (only additions, no changes)
config/settings.py    (only additions)
config/symbols.py
web/src/lib/          (auth.ts, db.ts, formatPrice.ts, time.ts)
web/src/app/api/      (all existing routes — additions only)
.claude/              (all skills, commands, rules, agents)
scripts/              (all scripts)
research/             (all research files)
migrations/
docs/
```

---

## Risk Management During Redesign

**The Python bot can run 24/7 while the frontend is being rebuilt** — they're completely decoupled. The Next.js dashboard reads from the same PostgreSQL database; no Python changes are required until Week 4.

**Frontend changes are purely visual** — no API contract changes until Week 3 (Day 11-12), and those are additive only (new fields, new endpoints).

**Rollback plan:** Every page rewrite is a new file. Keep the old page as `page.old.tsx` until the new page passes QA. One-line rollback if needed.

---

## Quick Reference: New Design Tokens

| Token | Value | Use |
|-------|-------|-----|
| `--bg` | `#0D0D0F` | Page background |
| `--bg-2` | `#141417` | Cards, sidebar, header |
| `--bg-3` | `#1C1C21` | Inputs, elevated surfaces |
| `--gold` | `#F0B429` | Primary accent, LONG, UP |
| `--red` | `#FF453A` | Danger, SHORT, DOWN |
| `--cyan` | `#64D2FF` | Info, live indicators |
| `--green` | `#30D158` | Success, confirmed |
| `--purple` | `#BF5AF2` | Neural/AI context |
| `--orange` | `#FF9F0A` | Warning, Council |
| `--font-mono` | IBM Plex Mono | ALL data/numbers |
| `--font-ui` | IBM Plex Sans Condensed | Labels, nav, UI chrome |
| Sidebar | `220px` | -20px from current |
| Header | `52px` | -12px from current |
| Border radius | `3px` default | Sharp, not zero |
```
