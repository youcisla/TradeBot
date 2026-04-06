# PulseTrade — Operator Dashboard Redesign

> Strategic UX redesign for the PulseTrade autonomous trading engine operator interface.
> Produced after full codebase analysis: agents, strategies, filters, models, API routes, and existing UI.

---

## 1. Product Understanding Summary

PulseTrade is **not a trading terminal**. It is an **operator command center** for a live autonomous trading engine.

The system runs continuously without human input per trade. The operator's role is:
- **Supervise** — understand what the machine is doing and why
- **Intervene** — pause, resume, close, override only when necessary
- **Diagnose** — understand failures, model drift, risk exceedances
- **Evaluate** — review performance, adjust parameters, trigger retraining

The operator does NOT want to trade manually. They want to trust the machine and get out of its way unless intervention is genuinely needed.

**Core system domains:**
- Multi-agent pipeline: `crucix → market → analysis → strategy → neural → council → risk → execution → trade_manager`
- ICT/SMC signal generation with LSTM + LGBM ML filtering
- Macro intelligence: Crucix + FRED/yfinance/EIA/GDELT feeds
- GuardPipeline: 7 pre-execution safety guards
- Post-trade learning: reward scoring, confidence adjustment, model drift detection
- MetaTrader 5 broker execution via Python connector
- PostgreSQL shared state via Supabase

**Critical distinction:** The bot makes 90%+ of decisions autonomously. Human intervention is the exception, not the norm. The UI must communicate this clearly — confidence and reasoning are as important as raw data.

---

## 2. User Personas

### Primary: Bot Owner / Operator / Strategist

**Goals:**
- Start the day knowing the bot is healthy and trading is proceeding normally
- Understand why specific signals were taken or rejected without deep-diving into logs
- Know when to intervene vs. when to trust the system
- Track performance over time and adjust parameters

**Critical information:**
- Bot state (running / paused / error)
- Broker connection
- Current positions + unrealized PnL
- Daily PnL vs. balance
- Top signals: what the system is acting on, why, and with what confidence
- Risk approval / rejection of signals (with reasons)
- Critical alerts: GuardPipeline blocks, model staleness, macro blackout

**Pain points:**
- Existing UI hides signal reasoning — operator sees "BUY" but not why ICT beat LSTM beat SMA
- Agent failures are invisible until they cause downstream problems
- No visibility into why a signal was rejected by RiskAgent
- Brain page exists but is disconnected from the operator's real decision flow

**Actions (high-risk):**
- Pause / resume bot ← reversible, low risk
- Close all positions ← high risk, requires confirmation
- Adjust risk parameters ← medium risk
- Force agent cycle ← low risk

**Actions (low-risk, should be fast):**
- View signal reasoning
- Browse agent outputs
- Review recent closed trades
- Check model drift status

---

### Secondary: Technical Reviewer / Developer

**Goals:**
- Understand agent-by-agent behavior and outputs
- Diagnose why a signal performed poorly
- Track model drift and retraining triggers
- Access structured logs and postmortems

**Critical information:**
- Full agent event stream with timestamps
- Each agent's latest output and reasoning
- Model confidence over time
- Signal postmortem data (entry snapshot fields)
- Data validation failures

**Actions:**
- Browse event stream
- Filter by agent, severity, time range
- Export structured data

---

### Tertiary: Investor / Observer (read-only, future)

**Goals:**
- See equity curve and portfolio health
- Understand current positions
- View high-level performance metrics
- See risk status without understanding technical details

**Actions:** Read-only dashboard, no controls.

---

## 3. Information Architecture

### Area Map

```
Mission Control        /dashboard/         ← PRIMARY: everything in one glance
Signal Intelligence    /dashboard/signals  ← Signal ranking, reasoning, approval path
Trade Operations      /dashboard/trades   ← Full trade lifecycle
Risk & Exposure       /dashboard/risk     ← Portfolio risk, concentration, blocks
Agent Observability   /dashboard/agents   ← Pipeline health, agent outputs, warnings
Macro Intelligence    /dashboard/macro    ← Regime, Crucix, geopolitical, flash alerts
Performance           /dashboard/analytics ← Win rate, expectancy, equity curve, drift
Learning              /dashboard/learning  ← Model training, reward scoring, drift
System Health         /dashboard/health   ← Infra, DB, broker latency, uptime
Controls & Settings   /dashboard/settings ← Parameters, broker accounts, commands
```

### Area Definitions

#### Mission Control (`/dashboard/`)
- **Purpose:** The operator's primary view — answer "is everything OK?" in under 5 seconds
- **Primary widgets:** Health strip (bot/broker/DB), Live Positions, Top Signals, Risk Status, Macro Snapshot, Agent Feed, Command Console
- **Data importance:** Critical first, everything else secondary
- **Actions available:** Pause/resume, Close all (confirm), Force cycle
- **Relationships:** Pulls from all domains — this is the aggregation layer

#### Signal Intelligence (`/dashboard/signals`)
- **Purpose:** Understand what the system is evaluating and why each signal ranked the way it did
- **Primary widgets:** Signal ranking table (symbol, direction, confidence, source, macro alignment, risk verdict, age), Signal detail drawer (full reasoning, ML filter impact, bull/bear case, entry snapshot), Approval path visualization (agent chain with pass/fail at each stage)
- **Data importance:** Confidence and reasoning > everything else
- **Actions available:** None (read-only monitoring)
- **Relationships:** Driven by StrategyAgent + LearningAgent outputs

#### Trade Operations (`/dashboard/trades`)
- **Purpose:** Full trade lifecycle — from signal acceptance through execution to postmortem
- **Primary widgets:** Open positions table (entry, SL, TP1/2/3/4, partial hit progress, unrealized PnL, age), Pending signals (approved but not yet executed), Closed trades (PnL, outcome, close reason, postmortem score), Trade detail panel (entry snapshot, execution quality, TP progression)
- **Data importance:** PnL and outcome > entry details
- **Actions available:** Close individual position, Add manual SL/TP
- **Relationships:** Driven by TradeManager + ExecutionAgent

#### Risk & Exposure (`/dashboard/risk`)
- **Purpose:** Real-time portfolio risk — am I overexposed?
- **Primary widgets:** Exposure heatmap (symbol × direction), Daily loss cap progress bar, Concentration risk (per-symbol, per-direction limits), Correlation risk matrix, Spread monitoring, Blocked signals list with GuardPipeline reasons, Crucix status card (risk tier, lot scale factor)
- **Data importance:** Exceedances and blocks > raw numbers
- **Actions available:** Adjust risk parameters (medium risk, confirmation required)
- **Relationships:** Driven by RiskAgent + ExposureAgent + CrucixClient

#### Agent Observability (`/dashboard/agents`)
- **Purpose:** Is every agent in the pipeline healthy? What did each one just do?
- **Primary widgets:** Pipeline health grid (12 agents with status badge, latest message, last-seen, event count), Agent detail (latest event, message history, timing, error count), Event stream (all agent events, filterable by agent + severity)
- **Data importance:** Failures and stalls > activity logs
- **Actions available:** Force agent cycle, Clear error state
- **Relationships:** Driven by LoggingAgent + each agent's event emission

#### Macro Intelligence (`/dashboard/macro`)
- **Purpose:** What macro conditions are affecting signal generation right now?
- **Primary widgets:** Macro regime card (yield curve, VIX, USD index, oil), Flash alert banner (red, Crucix FLASH events), Volatility state (GARCH regime: low/normal/high/crisis), FRED key series (10Y, 2Y, T10Y2Y, DXY), EIA crude signal, GDELT sentiment tone, Blackout indicator (active = no new trades), Lot scale factor display
- **Data importance:** FLASH blackout > regime state > individual indicators
- **Actions available:** None (read-only)
- **Relationships:** Driven by CrucixClient + IntelligenceSweep

#### Performance (`/dashboard/analytics`)
- **Purpose:** Is the bot profitable? Is performance degrading?
- **Primary widgets:** Equity curve (daily PnL, balance over time), Win rate gauge (overall + per-symbol + per-strategy), Expectancy (avg win × win rate - avg loss × loss rate), Drawdown waterfall, Strategy performance breakdown (ICT vs SMA vs DeepSeek), Model drift indicator, Retraining trigger status
- **Data importance:** Trend > absolute numbers
- **Actions available:** Trigger model retraining
- **Relationships:** Driven by LearningAgent + model_manager

#### Learning (`/dashboard/learning`)
- **Purpose:** How is the bot updating its confidence? What did recent trades teach it?
- **Primary widgets:** Reward scoring feed (recent trades scored), Confidence adjustment log, Post-mortem analysis (clean vs messy signal classification), Model retraining status, Drift detector status
- **Data importance:** Drift alerts > scoring activity
- **Actions available:** Trigger retraining, Acknowledge drift alert
- **Relationships:** Driven by LearningAgent + model_manager

#### System Health (`/dashboard/health`)
- **Purpose:** Is the infrastructure stable?
- **Primary widgets:** Bot uptime, Broker connection latency, DB connection pool status, API response time trends, Disk/memory usage (if available), Cron/heartbeat status, Error rate (last 1h / 24h), Active session count
- **Data importance:** Down services > degraded performance
- **Actions available:** Restart service (emergency only)
- **Relationships:** Driven by heartbeat + logging_agent

#### Controls & Settings (`/dashboard/settings`)
- **Purpose:** Configure parameters, manage broker accounts, review command history
- **Primary widgets:** Risk parameters (max risk/trade, daily loss cap, max positions), Broker account management (add/edit/delete, test connection), Command history (all bot commands with status + audit trail), Pending review commands (high-risk commands awaiting approval)
- **Actions available:** All configuration changes
- **Relationships:** Writes to settings.py + DB

---

## 4. Operator Decision Flow

The UI layout must follow this cognitive sequence:

```
1. IS THE BOT HEALTHY?          → Health strip (top-left)
2. IS TRADING ALLOWED?          → Bot state pill + Crucix blackout indicator
3. ARE BROKER + DB CONNECTED?   → Health strip (top-right)
4. WHAT POSITIONS ARE OPEN?     → Live Positions (left column)
5. WHAT IS THE PnL?             → Equity / Daily PnL card (top-center)
6. WHAT SIGNALS ARE STRONGEST?  → Top Signals card (center)
7. DID RISK APPROVE THEM?       → Risk verdict badges on signals
8. IS EXPOSURE SAFE?            → Exposure mini-bar (bottom-left)
9. WHAT IS MACRO DOING?         → Macro snapshot (bottom-right)
10. DID EXECUTION SUCCEED?      → Agent feed (right column)
11. IS INTERVENTION NEEDED?      → Command Console (bottom strip)
```

The Mission Control layout MUST follow this exact order spatially — top to bottom, left to right.

---

## 5. Screen-by-Screen Design Strategy

### A. Mission Control — `/dashboard/`

**Layout:** Three-column + top strip + bottom strip

```
┌─────────────────────────────────────────────────────────────┐
│  TOP STRIP: Health indicators + Bot State + Daily PnL       │
├──────────────┬────────────────────────┬────────────────────┤
│ LEFT COLUMN  │   CENTER COLUMN         │  RIGHT COLUMN       │
│ Live         │   Top Signals          │  Agent Feed        │
│ Positions    │   (ranked, with        │  (recent events,   │
│ + Unrealized │   risk verdict badges)  │   filterable)      │
│ PnL          │                        │                    │
│              │   Risk Status mini     │  Macro Snapshot    │
│ Exposure     │   (daily loss cap,     │  (regime, VIX,     │
│ heatmap      │   concentration)       │   flash alerts)    │
├──────────────┴────────────────────────┴────────────────────┤
│  BOTTOM STRIP: Command Console (Pause/Resume | Close All)    │
└─────────────────────────────────────────────────────────────┘
```

**Top strip (left to right):**
1. Bot state pill: `RUNNING` (green pulse) / `PAUSED` (amber) / `ERROR` (red)
2. Broker status: `MT5 Connected` / `Disconnected`
3. DB status: `PostgreSQL OK` / `Latency: Xms` / `Error`
4. Separator
5. Balance: `$XX,XXX.XX`
6. Equity: `$XX,XXX.XX` (green if > balance, red if <)
7. Daily PnL: `+$XXX.XX` (green) or `-$XXX.XX` (red)
8. Win rate: `XX% (X/X last 20)`

**Signal card (center):** Shows top 3 ranked signals with:
- Symbol + direction badge (BUY/SELL with color)
- Confidence bar (0–100%, colored by tier)
- Source strategy icon (ICT/LSTM/SMA/DeepSeek)
- Risk verdict: `APPROVED` (green) / `BLOCKED: [reason]` (red) / `PENDING` (amber)
- Time since signal
- Expand to see full reasoning

**Agent feed (right):** Scrolling event stream, newest first:
- Agent color dot + agent name
- Truncated message
- Relative timestamp
- Severity badge for errors

**Command console (bottom):**
- Pause/Resume (toggles label, color changes)
- Close All Positions (red, requires confirmation modal)
- Force Weekly Snap (neutral, immediate)

---

### B. Signal Intelligence — `/dashboard/signals`

**Primary view:** Sortable table of all signals (pending + recent)

Columns:
- Symbol
- Direction (BUY/SELL badge)
- Age (time since generated)
- Source (ICT / LSTM / SMA / DeepSeek)
- Confidence (%)
- Macro Alignment (aligned / neutral / opposed)
- Risk Verdict (approved / blocked / pending)
- Block Reason (if blocked — GuardPipeline reason)
- Actions: Expand (shows full reasoning drawer)

**Signal detail drawer (slide-in from right):**
- Full human-readable `reason` string
- Structural reasoning: what ICT components fired (FVG / OB / sweep / MSS / session)
- Bull case / Bear case (from LLM debate)
- Entry snapshot: spread, RSI alignment, trend alignment, volume, near news flag, market condition, session, day of week
- ML filter impact: was confidence boosted or reduced by LGBM/GARCH?
- Approval chain: which agents approved / rejected each stage
- Entry price, SL, TP1/2/3/4 levels
- Structural breakeven level

---

### C. Trade Operations — `/dashboard/trades`

**Tabs:** Open | Pending | Closed | All

**Open tab columns:**
- Symbol
- Direction
- Entry price
- Current price
- Unrealized PnL (colored)
- SL
- TP1 / TP2 / TP3 / TP4 with hit indicators (● = hit, ○ = pending)
- Lot size remaining
- Age
- Status badge (OPEN / PARTIAL)
- Actions: [Close] [Edit SL]

**Partial TP progression visual:**
```
TP1 ●───● TP2 ●─ TP3 ○─ TP4 ○
     40%   30%   20%   10%
```
Shows which tiers are hit and how lots were reduced at each tier.

**Closed tab columns:**
- Symbol
- Direction
- Entry / Exit price
- PnL (colored)
- Close reason (TP1 / TP2 / TP3 / TP4 / SL / MANUAL / EMERGENCY)
- Open time / Close time / Duration
- Postmortem score (clean / mixed / messy)
- Expand to see entry snapshot

**Trade detail drawer:**
- Full Trade model fields
- Entry snapshot visualization
- Execution quality: spread at entry vs. expected, slippage
- TP progression timeline
- Post-mortem: clean vs messy classification

---

### D. Risk & Exposure — `/dashboard/risk`

**Top section:** Three KPI cards
- Daily PnL vs. Loss Cap (progress bar)
- Open Exposure (lots + notional value)
- Concentration Score (0–100, red if > 70)

**Exposure heatmap:**
```
         LONG    SHORT   NET
EURUSD   ████    ░░░░    +2.1
GBPUSD   ██      ██      0.0
XAUUSD   █████           +4.3
```

Each cell colored by intensity. Click to drill down.

**Risk per trade table:**
- Recent 10 signals with: symbol, direction, lot size, risk $ (SL distance × lot), risk % of equity

**Blocked signals list:**
- Signals rejected by RiskAgent
- Block reason: GuardPipeline failure name + message
- Timestamp
- Operator can override with confirmation

**Crucix status card:**
- Risk tier badge: CLEAR / ROUTINE / PRIORITY / FLASH
- Lot scale factor: 0% / 50% / 75% / 100%
- Active flash alerts (count + brief description)
- Last sweep age

---

### E. Agent Observability — `/dashboard/agents`

**Pipeline health grid (12 agents):**
```
[RUNNING] [RUNNING] [IDLE] [STALE] [ERROR] ...
```
Each cell: agent name, status badge, last-seen time, event count, latest message truncated.

**Click agent → detail panel:**
- Agent name + color
- Status badge + timing info
- Last 10 events from this agent (full message)
- Error count if any
- Processing time average

**Event stream (below grid):**
- Full event feed with filters: agent, severity, time range
- Each event: agent badge, severity indicator, message, timestamp, event_type tag

---

### F. Macro Intelligence — `/dashboard/macro`

**Flash alert banner (red, full-width, persistent until acknowledged):**
```
🚨 FLASH ALERT: [Crucix message] — All new trades blocked until cleared
```

**Regime summary card:**
- GARCH regime: LOW / NORMAL / HIGH / CRISIS (color coded)
- Yield curve: NORMAL / INVERTED (color coded)
- VIX level with threshold lines
- USD index with direction

**Key macro indicators (grid):**
| Indicator | Value | Signal |
|---|---|---|
| DGS10 (10Y yield) | X.XX% | ↑↓ |
| DGS2 (2Y yield) | X.XX% | ↑↓ |
| T10Y2Y (spread) | X.XX | ↑↓ |
| VIX | XX.XX | ↑↓ |
| DXY | XXX.XX | ↑↓ |
| WTI Crude | $XX.XX | ↑↓ |
| GDELT Tone | X.XX | ↑↓ |

**Active blackout indicator:**
- If Crucix `is_blackout = True` → large red banner: "MACRO BLACKOUT — NO NEW TRADES"
- Lot scale factor shown prominently

---

### G. Performance — `/dashboard/analytics`

**Top strip:** Equity curve (area chart, daily PnL filled)
- Balance line
- Equity line
- Drawdown shading (red)

**KPI row:**
- Total PnL (all time)
- Win Rate %
- Expectancy ($ per trade)
- Best trade / Worst trade
- Avg trade duration
- Total trades

**Performance by strategy (bar chart):**
- ICT SMC
- LSTM
- SMA Crossover
- DeepSeek

**Performance by symbol (table):**
- Symbol, total trades, win rate, avg PnL, total PnL

**Drawdown chart:**
- Waterfall chart showing drawdown periods

**Model drift indicator:**
- Current drift score vs. threshold
- Status: NOMINAL / DRIFTING / RETRAIN RECOMMENDED

---

### H. Learning — `/dashboard/learning`

**Reward scoring feed:**
- Recent 20 closed trades
- Score: 0–100
- Classification: clean / mixed / messy
- Key reasons: spread, RSI aligned, trend aligned, volume sufficient, near news event
- Learning feedback: confidence adjusted up/down

**Confidence adjustment log:**
- Per-strategy, per-symbol
- Shows direction and magnitude of last N adjustments

**Post-mortem quality classifier:**
- Visual breakdown: spread quality, timing quality, setup quality
- Clean setups: green, Messy setups: red

**Model training status:**
- Last trained: [timestamp]
- Training status: IDLE / TRAINING / ERROR
- Dataset size, lookback period
- [Trigger Retraining] button

---

### I. System Health — `/dashboard/health`

**Status grid:**
| Service | Status | Latency | Uptime |
|---|---|---|---|
| Bot (main.py) | ● RUNNING | — | 4h 23m |
| MT5 Broker | ● Connected | 12ms | — |
| PostgreSQL | ● OK | 4ms | — |
| Crucix API | ● Available | 87ms | — |
| FRED | ● Available | — | — |
| IntelligenceSweep | ● Active | — | Last: 3m ago |
| Heartbeat | ● OK | — | — |

**Error rate chart:** Last 24h error count by hour

**API response times:** p50 / p95 / p99 for each API endpoint

**Disk / Memory:** If available from system metrics

---

### J. Controls & Settings — `/dashboard/settings`

**Sections:**
1. Risk Parameters (editable with save)
2. Broker Accounts (list + add + test + delete)
3. Command History (table with status, timestamp, result)
4. Pending Review Commands (high-risk commands awaiting approval)
5. API Keys / Secrets (masked, rotatable)

---

## 6. Component System

### Health Strip
- **What it communicates:** Is the whole system up and working?
- **When used:** Top of every page (persistent header)
- **Priority:** Critical — always visible
- **Interactive behavior:** Click any indicator → navigate to System Health
- **Compact mode:** Single row of pills. Expanded mode: Health page with full details
- **States:** Healthy (green), Degraded (amber), Critical (red), Unknown (gray)

### Status Pill
- **What it communicates:** Bot running state at a glance
- **States:** RUNNING (green pulse), PAUSED (amber), ERROR (red pulse)
- **Behavior:** Click → toggles pause/resume (with optimistic UI update)

### Confidence Bar
- **What it communicates:** How confident the system is in a signal or trade
- **Visual:** Horizontal bar, width = confidence%, color by tier:
  - 0–40%: red (low conviction)
  - 40–65%: amber (moderate)
  - 65–85%: cyan (high)
  - 85–100%: green (very high)
- **Display:** Always show numeric % + bar together

### Severity Badge
- **Variants:** ERROR (red), WARNING (amber), INFO (blue), SUCCESS (green), NEUTRAL (gray)
- **Size:** Small (9px font) for inline use, Medium (11px) for cards

### Agent Badge
- **What it communicates:** Which agent produced an event or signal
- **Visual:** Colored background matching agent color, agent name uppercase, 9px font
- **Agent colors (fixed):**
  - crucix: #5AC8FA
  - market: #0A84FF
  - analysis: #E8EAED
  - strategy: #34C759
  - neural: #BF5AF2
  - council: #FF9F0A
  - risk: #FF3B30
  - execution: #E8EAED
  - trade_manager: #5AC8FA
  - learning: #30D158
  - model_manager: #BF5AF2
  - logging: rgba(232,234,237,0.35)

### Signal Card
- **What it communicates:** A ranked signal with its approval status
- **Fields:** Symbol, direction badge, confidence bar, source strategy, risk verdict, age
- **Expanded:** Full reasoning, entry levels, approval chain
- **Hover:** Subtle highlight
- **Click:** Opens detail drawer

### Trade Row
- **What it communicates:** A position or historical trade
- **Visual:** Grid layout matching table columns, color-coded PnL
- **TP Progress:** Inline dot indicators for TP1/2/3/4 hit status
- **Hover:** Row highlight
- **Click:** Opens trade detail drawer

### Exposure Heatmap Cell
- **What it communicates:** Directional exposure intensity per symbol
- **Visual:** Background color intensity proportional to exposure
- **Positive (long):** Green tint
- **Negative (short):** Red tint
- **Neutral:** Dark / empty
- **Hover:** Shows exact lot count and notional value

### Event Feed Item
- **What it communicates:** A single event from the agent pipeline
- **Visual:** Agent badge + message + relative timestamp
- **Severity:** Error events get red left border
- **Hover:** Subtle background
- **Click:** Expands to show full message

### Command Console Panel
- **What it communicates:** Available operator actions
- **Actions:** Pause/Resume (toggle), Close All (danger, modal), Force Weekly Snap
- **Feedback:** Inline success/error message after command
- **Danger actions:** Visually distinct (red border), require confirmation modal

### Warning Banner
- **Variants:** FLASH (red, full-width, persistent), ERROR (red, dismissible), WARNING (amber, dismissible), INFO (blue, dismissible)
- **FLASH:** Cannot be dismissed — must be cleared by system when condition resolves

### Skeleton Loader
- **Use:** Any data that is loading
- **Visual:** Matches the shape of the real content (card skeleton, row skeleton, etc.)
- **Animation:** Subtle shimmer, not a spinner

### Confirmation Modal
- **Use:** Close All, any high-risk parameter change
- **Visual:** Dark overlay, centered card, clear title, description, cancel + confirm buttons
- **Danger variant:** Red confirm button

---

## 7. Visual Design Direction

### Aesthetic
Professional dark interface — closer to a **mission control room** or **risk operations desk** than a retail fintech app.

**Reference points:** Bloomberg Terminal (information density), Vercel Dashboard (clean precision), Linear (operational clarity), not Binance or TradingView.

### Color System
```
Background:      #08090B (near-black, slightly blue-tinted)
Surface-1:       #0D0F12 (card background)
Surface-2:       #12151A (elevated card / modal)
Border:          rgba(255,255,255,0.08)
Border-strong:   rgba(255,255,255,0.15)

Text-primary:    #E8EAED
Text-secondary:  rgba(232,234,237,0.55)
Text-muted:     rgba(232,234,237,0.30)

Accent-cyan:    #63D4FF (system indicators, links)
Positive:       #30D158 (wins, approvals)
Negative:       #FF453A (losses, errors, blocks)
Warning:        #FF9F0A (caution, stalls)
Flash:          #FF453A with red glow (FLASH blackout)

Agent colors:   (see Agent Badge spec above — fixed per agent)
```

### Typography
```
System:         -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui
Monospace:      "SF Mono", ui-monospace, Menlo, Monaco (for prices, times, IDs)
Font sizes:     11px labels / 13px body / 15px subheadings / 20px headings / 28px KPIs
Letter-spacing:  0.5px on uppercase labels, -0.5px on large numbers
```

### Spacing System
```
4px   — xs (between tightly related elements)
8px   — sm (within components)
12px  — md (between related components)
20px  — lg (between sections)
32px  — xl (major section gaps)
```

### Motion Philosophy
- **Functional only:** No decorative animation
- **State transitions:** 150ms ease for hovers, color changes
- **Entrance:** Fade-in 200ms for loading states (skeleton → content)
- **Modals:** Fade + scale 200ms ease-out
- **No:** Bouncing, pulsing glows (except status indicators), parallax

### Layout Rhythm
- **3-column layout** for Mission Control: positions (30%) / signals + risk (40%) / feed + macro (30%)
- **Single column** for detailed pages (signals, trades, agents)
- **Dense tables** with 40px row height — prioritize information density
- **Card padding:** 20px standard, 16px compact
- **Card radius:** 12px everywhere — consistent
- **Border-separation over whitespace-separation** for related data

---

## 8. UX Mistakes to Avoid

### Do NOT do:
1. **Full-page loading spinner** — blocks all information. Use skeletons that match real content shape.
2. **Bury risk status** — risk approval/rejection must be visible on every signal, not hidden on a separate page.
3. **Hide agent failures** — stale or error-state agents must be visually prominent.
4. **Show everything at once** — use progressive disclosure (hover for preview, click for detail).
5. **Sequential API calls** — use `Promise.all` to fetch all needed data in parallel.
6. **Multiple status polls** — single source of truth for shared state (AppShell context).
7. **Render-blocking fonts** — serve Material Symbols locally.
8. **Overflow-breaking layouts** — use `minWidth: 0`, `overflow: hidden`, `flexWrap: wrap` correctly.
9. **One-size-fits-all cards** — compact mode for dense tables, expanded for detail drawers.
10. **Generic Binance-style UI** — this is an operations center, not a trading terminal.

---

## 9. Final Proposed Layout for Main Dashboard

### Mission Control (`/dashboard/`) — Spatial Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ TOP STRIP (56px fixed height)                                          │
│ [●] NeuralFX │ RUNNING │ MT5: Connected │ DB: OK │ │ $50,000 │ $51,234 │ +$1,234 │ 62% │ [⏸ Pause] │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ MAIN CONTENT (flex: 1, overflow-y: auto, padding: 24px)                 │
│                                                                         │
│  ┌───────────────┐  ┌──────────────────────────┐  ┌──────────────────┐  │
│  │ LIVE POSITIONS│  │ TOP SIGNALS              │  │ AGENT FEED       │  │
│  │ (30% width)   │  │ (40% width)              │  │ (30% width)      │  │
│  │               │  │                          │  │                  │  │
│  │ Symbol Dir PnL│  │ #1 XAUUSD BUY 82%        │  │ ●crucix 12s      │  │
│  │ XAUUSD 🟢+$340│  │    APPROVED | ICT+LSTM   │  │ ●market 8s       │  │
│  │ EURUSD 🟢+$45 │  │    Entry $2341 SL $2330  │  │ ●analysis 45s    │  │
│  │               │  │                          │  │ ●strategy 2m     │  │
│  │ +2 more      │  │ #2 EURUSD SELL 71%       │  │ ●council 3m     │  │
│  │               │  │    PENDING | ICT only    │  │                  │  │
│  ├───────────────┤  │                          │  │ ── MACRO ─────── │  │
│  │ EXPOSURE      │  │ #3 GBPUSD BUY 58%         │  │ Regime: NORMAL   │  │
│  │ HEATMAP       │  │    BLOCKED: spread > 20  │  │ VIX: 18.4 ↑     │  │
│  │               │  │                          │  │ DXY: 104.2 ↓    │  │
│  │ LONG  ████░░  │  ├──────────────────────────┤  │ ⚠ LOT SCALE 75% │  │
│  │ SHORT ██░░░░  │  │ RISK STATUS               │  │                  │  │
│  │               │  │ Daily Cap: ████░░ 78%   │  │                  │  │
│  │ Daily: +$234  │  │ Exposure: 4.2 lots       │  │                  │  │
│  │ Max risk: OK  │  │ Concentration: 42        │  │                  │  │
│  └───────────────┘  └──────────────────────────┘  └──────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ COMMAND CONSOLE                                                     │   │
│  │ [⏸ Pause Bot]  [■ Close All Positions]  [📸 Force Weekly Snap]     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Page Routing Map

| Route | Current | Proposed |
|---|---|---|
| `/dashboard/` | Command Center (inconsistent) | Mission Control (redesigned per spec) |
| `/dashboard/trades` | Trade Book | Trade Operations (tabs: Open/Pending/Closed) |
| `/dashboard/markets` | Market Intel | Macro Intelligence |
| `/dashboard/analytics` | Performance | Performance Analytics |
| `/dashboard/brain` | Agent Brain | Agent Observability |
| `/dashboard/risk` | Risk Console | Risk & Exposure |
| `/dashboard/settings` | Settings | Controls & Settings |
| NEW | — | Signal Intelligence (`/dashboard/signals`) |
| NEW | — | Learning (`/dashboard/learning`) |
| NEW | — | System Health (`/dashboard/health`) |

---

## 10. Implementation Priority

### Phase 1: Core Shell (foundation)
1. Implement `AppShell` context (done — status polling in one place)
2. Design token system in CSS variables (done — globals.css updated)
3. Consistent card component system
4. Health strip (persistent top bar)
5. Loading skeletons (done — streaming)

### Phase 2: Mission Control Redesign
1. Redesign `/dashboard/` as 3-column Mission Control
2. Implement top health strip with all indicators
3. Live Positions card (left column)
4. Top Signals card with risk verdict badges (center)
5. Agent Feed + Macro snapshot (right column)
6. Command console (bottom)

### Phase 3: Signal Intelligence
1. New `/dashboard/signals` page
2. Signal ranking table
3. Signal detail drawer with full reasoning
4. Approval chain visualization

### Phase 4: Trade Operations
1. Tab interface (Open/Pending/Closed)
2. TP progression visual
3. Trade detail drawer with entry snapshot

### Phase 5: Risk & Exposure
1. Exposure heatmap component
2. Daily loss cap progress bar
3. Blocked signals list
4. Crucix status card

### Phase 6: Agent Observability
1. Pipeline health grid (12 agents)
2. Event stream with filters
3. Agent detail panel

### Phase 7: Remaining Pages
1. Macro Intelligence (`/dashboard/macro`)
2. Performance Analytics (upgrade existing)
3. Learning page (`/dashboard/learning`)
4. System Health page (`/dashboard/health`)

### Phase 8: Polish
1. All skeleton loaders for every async state
2. Confirmation modals for all high-risk actions
3. Warning/flash banner system
4. Progressive disclosure throughout
5. Read-only investor view mode
