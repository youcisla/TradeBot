---
name: trading-bot-overview
description: "Full PulseTrade system reference — architecture, agent pipeline, key files, DB schema, strategy stack."
category: project
risk: none
source: project
date_added: "2026-03-28"
date_updated: "2026-04-06"
---

# PulseTrade TradingBot — System Overview

## Identity
- **Name:** PulseTrade TradingBot
- **Stack:** Python (bot) + Next.js 16 App Router (dashboard)
- **Broker:** PU Prime via MetaTrader 5 (Windows only)
- **DB:** PostgreSQL (Supabase) — 7 tables
- **Primary strategy:** LSTM Neural Network (per-symbol, auto-trained on 2yr H1 history)
- **Mode:** DEMO_MODE = False (hardcoded, Phase 1)

---

## Agent Pipeline

```
PIPELINE:  crucix → market → analysis → strategy → neural → council → risk → execution → trade_manager
SUPPORT:   learning · model_manager · logging · debate · exposure · memory
```

| Agent | File | Responsibility |
|---|---|---|
| CrucixAgent | `agents/crucix_agent.py` | Macro intel from Crucix server (localhost:3117) — FLASH/PRIORITY tier, VIX, OSINT |
| MarketAgent | `agents/market_agent.py` | Fetch candles, compute ATR/RSI/SMA, detect news blackout |
| AnalysisAgent | `agents/analysis_agent.py` | Regime (trending/ranging), trend direction, session |
| StrategyAgent | `agents/strategy_agent.py` | Runs all strategies, returns highest-confidence Signal |
| CouncilAgent | `agents/council_agent.py` | 4-expert LLM gate: ICT + DanialFX + Traditional + WorldContext |
| RiskAgent | `agents/risk_agent.py` | Lot sizing, spread check, daily loss cap, open trade limit |
| ExecutionAgent | `agents/execution_agent.py` | Opens orders via GuardPipeline gate, splits lots for TP1/2/3/4 |
| TradeManager | `agents/trade_manager.py` | Monitors open trades, handles TP hits, SL, breakeven |
| LearningAgent | `agents/learning_agent.py` | Reward scoring, confidence updates, daily summary |
| LoggingAgent | `agents/logging_agent.py` | DB events, CSV journal, Telegram daily summary |
| DebateAgent | `agents/debate_agent.py` | Bull/bear LLM debate gate (opt-in: `DEBATE_ENABLED=true`) |
| ExposureAgent | `agents/exposure_agent.py` | Portfolio exposure directive: NEW_ENTRY_ALLOWED / REDUCE_ONLY / CASH_PRIORITY (opt-in: `EXPOSURE_ENABLED=true`) |
| MemoryAgent | `agents/memory_agent.py` | Cross-session memory blocks in `bot_memory` table (8 labeled blocks) |

**Support utilities in `agents/`:**
- `guards.py` — GuardPipeline + 7 guards (runs inside ExecutionAgent)
- `reflector.py` — post-trade reflection

---

## Strategy Stack

| Strategy | File | Status |
|---|---|---|
| ICT/SMC | `strategies/ict_strategy.py` + `strategies/ict/` | **Active** — primary |
| Neural LSTM | `agents/neural_strategy.py` | **Active** — secondary (via ModelManager) |
| Unified | `strategies/unified_strategy.py` | Aggregator across all strategies |

### DeepSeek Multi-Agent Mode
- `DEEPSEEK_AGENT_SWARM_ENABLED=true` enables parallel specialist LLM roles (trend/structure/risk)
- Responses aggregated into one consensus signal (`deepseek_swarm`) with averaged SL/TP and confidence
- Off by default; guarded behind env flags in `config/settings.py`

### ICT Engine (10 modules in `strategies/ict/`)
`engine.py` → `liquidity.py`, `market_structure.py`, `fair_value_gaps.py`, `order_blocks.py`, `displacement.py`, `fibonacci.py`, `sessions.py`, `scoring.py`, `models.py`

### ICT Scoring (active upgrades)
- **Pillar 3:** Entry snapped to FVG CE or OB midpoint; staleness gate (0.5× ATR forex, 2.0× ATR crypto/XAU)
- **Pillar 4:** TP4 runner targeting HTF liquidity; structural breakeven from swing levels

### Debate Gate (DebateAgent)
When `DEBATE_ENABLED=true`, every signal that survives LGBM filter is presented to a bull/bear LLM debate:
- **PROCEED** → confidence +5%
- **CAUTIOUS** → confidence -10%
- **SKIP** → confidence -25%
- Fail-open: LLM timeout → signal passes unchanged

---

## ML / Signal Enrichment Stack

| File | Purpose |
|---|---|
| `features/macro_features.py` | Builds 15-float z-scored macro vector from MacroSnapshot |
| `features/microstructure.py` | Spread, imbalance, Kyle's lambda, wick asymmetry per bar |
| `models/lgbm_ensemble.py` | LightGBM 3-class classifier (BUY / SELL / HOLD) |
| `models/lgbm_price_model.py` | LightGBM price prediction |
| `models/garch_regime.py` | GARCH(1,1) + EWMA regime detector (low/normal/high/extreme) |
| `utils/kalman_filter.py` | 2D constant-velocity Kalman price smoother |
| `filters/intelligence_sweep.py` | Async FRED/yfinance/EIA/GDELT macro aggregator |

Train LGBM: `python scripts/train_lgbm.py`
Train price model: `python scripts/train_lgbm_price.py`
LGBM weights saved to: `models/lgbm_model.pkl`

---

## GuardPipeline (agents/guards.py)

7 guards run inside `ExecutionAgent._open_inner()` before every order:

| Guard | Blocks on |
|---|---|
| `MaxPositionSizeGuard` | `signal.lot_size_override` exceeds hard cap (only checks if override is set) |
| `SymbolWhitelistGuard` | Symbol not in whitelist |
| `CooldownGuard` | Last trade < `GUARD_COOLDOWN_SECONDS` ago |
| `DailyDrawdownGuard` | Today's loss > `GUARD_MAX_DAILY_LOSS_PCT`% |
| `MarketHoursGuard` | Outside trading session (weekend/gap) |
| `VolatilityGuard` | VIX > `GUARD_MAX_VIX` |
| `FeedFreshnessGuard` | Last tick age > `GUARD_FEED_STALENESS_SECONDS` |

All guards **fail-open** on internal exceptions. Disable entire pipeline: `GUARD_PIPELINE_ENABLED=false`.

**ExposureCoach** (`agents/exposure_coach.py`) runs after guards — advisory sizing only, does not block.

---

## Council Agent
4 experts, strategy-aware weighting:
- **ICT signal** → ICT=50%, DanialFX=17%, Traditional=17%, World=16%
- **Other signals** → equal 25% each
- **Threshold:** `COUNCIL_MIN_CONFIDENCE=0.60` (DO NOT set above 0.70)

---

## Weekend Mode
- Friday 22:00 – Sunday 22:00 UTC → crypto-only
- Symbols: `WEEKEND_SYMBOLS=BTCUSD` (comma-separated)
- Three ICT TF stacks: M15+H4, H1+D1, H4+W1

---

## DB Schema (7 tables)
```
trades              — open/closed trade records (TP1-4, structural_be, lots, pnl, bull/bear_case)
events              — structured event log (level, source, message)
agent_events        — per-agent activity feed (agent, event_type, message, metadata)
strategy_confidence — per-strategy win/loss/confidence
broker_accounts     — encrypted broker credentials
candle_cache        — OHLCV cache per symbol/timeframe
users               — dashboard user accounts (bcrypt passwords)
bot_memory          — MemoryAgent cross-session blocks (8 labeled JSON entries)
```

### Migration pattern (safe for existing tables):
```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE ...) THEN
    ALTER TABLE trades ADD COLUMN ...;
  END IF;
END $$;
```

### DB Connection Pool
- `_connect()` → `ThreadedConnectionPool(minconn=1, maxconn=20)` — used at startup
- `_reconnect()` → `SimpleConnectionPool(minconn=1, maxconn=5)` — used after stale detection
- `_get_conn()` — validates connection liveness (`SELECT 1`), auto-reconnects on `OperationalError`

---

## Key Configuration (`config/settings.py`)
All values from `.env`, never hardcoded. Key settings:
- `DEMO_MODE=False` — hardcoded, never change via env
- `TIMEZONE=Europe/Paris` — affects logs, day labels, daily summary
- `COUNCIL_MIN_CONFIDENCE=0.60`
- `LIMIT_ENTRY_MAX_DISTANCE_ATR=0.5` (forex), `LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO=2.0`
- `MAX_RISK_PER_TRADE=0.02`, `MAX_OPEN_TRADES=3`, `MAX_DAILY_LOSS=0.05`
- `CRUCIX_URL=http://localhost:3117`
- `DEBATE_ENABLED=false`, `EXPOSURE_ENABLED=false`
- `LGBM_ENSEMBLE_ENABLED=true`
- `GUARD_PIPELINE_ENABLED=true`
- `FRED_API_KEY=<key>` — required for IntelligenceSweep

---

## Frontend Dashboard (`web/`)
- **Framework:** Next.js 16 App Router
- **Auth:** NextAuth.js with JWT strategy + Edge middleware (`src/middleware.ts`)
- **Styling:** Tailwind CSS v3 + shadcn/ui (manually installed, no `npx shadcn add`)
- **No `className` on new JSX** — use design tokens via CSS custom properties
- **Pages:** dashboard, history, analytics, risk, chart, settings, learning, strategy, ict, system

### Dashboard API routes (`web/src/app/api/`)
`/api/status`, `/api/world`, `/api/trades`, `/api/events`, `/api/learning`, `/api/analytics`, `/api/ict`, `/api/candles`, `/api/commands`

---

## Models (`models/`)
- `Signal` — includes `take_profit_4`, `structural_be`, `bull_case`, `bear_case`
- `Trade` — includes `tp4_lots`, `tp4_hit`, `structural_be`, `bull_case`, `bear_case`
- `AgentMeshState` — DeepSeek swarm mesh graph (`models/agent_mesh.py`)
- `LSTMTradingModel` — in `models/neural_model.py`

---

## Key Utilities
- `utils/helpers.py` — `local_now()`, `is_weekend()`, `day_of_week()`, `current_session()`
- `utils/telegram_bot.py` — `send_message()`, `pause()`, `resume()`
- `utils/mesh_bus.py` — `mesh_span()` tracing context manager
- `utils/skill_manager.py` — runtime skill loading
- `utils/tool_system.py` — tool registry
- `utils/ops_doctor.py` — self-diagnostics
- `utils/dynamic_position_sizer.py` — Kelly/ATR-based lot sizing
- `utils/concept_drift_detector.py` — LGBM model drift detection
- `utils/correlation_gate.py` — cross-symbol correlation filter
- `filters/crucix_client.py` — CrucixClient, MacroContext, `get_macro_context()`
- `filters/intelligence_sweep.py` — IntelligenceSweep, MacroSnapshot

## Research Intake Workflow
- `backtesting/research_intake.py` — candidate scoring, checklist gates, promotion decision export
- `research/curated_sources.{json,yaml}` — trusted upstream source catalog
- `research/scoring_rubric.{json,yaml}` — weighted scoring model and promotion threshold
- `research/promotion_checklist.{json,yaml}` — hard gate criteria for promotion
- `research/candidate_backlog.json` — candidate queue for evaluation
- `scripts/backtest.py --research-intake` — runs the workflow

## Test Suite
- **422 tests** in `tests/` — run: `python -m pytest --tb=no -q`
- All tests use mock broker (`broker/mock_connector.py`) and `_MockDatabase` from `tests/conftest.py`
- DB resilience tests (`test_db_resilience.py`) set `_pool` directly to bypass `_connect()` (which uses `ThreadedConnectionPool`, not the patched `SimpleConnectionPool`)

---

## When to use this skill
- Before any architecture decision
- Before modifying the agent pipeline
- Before adding new symbols, strategies, or DB tables
- When unsure which file handles what
