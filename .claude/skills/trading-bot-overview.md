---
name: trading-bot-overview
description: "Full NeuralFX system reference — architecture, agent pipeline, key files, DB schema, strategy stack."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# NeuralFX TradingBot — System Overview

## Identity
- **Name:** NeuralFX TradingBot
- **Stack:** Python (bot) + Next.js 14 App Router (dashboard)
- **Broker:** PU Prime via MetaTrader 5 (Windows only)
- **DB:** PostgreSQL (Supabase) — 7 tables
- **Primary strategy:** LSTM Neural Network (per-symbol, auto-trained on 2yr H1 history)
- **Mode:** DEMO_MODE = False (hardcoded, Phase 1)

---

## Agent Pipeline

```
PIPELINE:  crucix → market → analysis → strategy → neural → council → risk → execution → trade_manager
SUPPORT:   learning · model_manager · logging
```

| Agent | File | Responsibility |
|---|---|---|
| CrucixAgent | `agents/crucix_agent.py` | Macro intel from Crucix server (localhost:3117) — FLASH/PRIORITY tier, VIX, OSINT |
| MarketAgent | `agents/market_agent.py` | Fetch candles, compute ATR/RSI/SMA, detect news blackout |
| AnalysisAgent | `agents/analysis_agent.py` | Regime (trending/ranging), trend direction, session |
| StrategyAgent | `agents/strategy_agent.py` | Runs all strategies, returns highest-confidence Signal |
| NeuralStrategy | `agents/neural_strategy.py` | Wraps ModelManager for LSTM inference |
| CouncilAgent | `agents/council_agent.py` | 4-expert gate: ICT + DanialFX + Traditional + WorldContext |
| RiskAgent | `agents/risk_agent.py` | Lot sizing, spread check, daily loss cap, open trade limit |
| ExecutionAgent | `agents/execution_agent.py` | Opens orders, splits lots for TP1/2/3/4 |
| TradeManager | `agents/trade_manager.py` | Monitors open trades, handles TP hits, SL, breakeven |
| LearningAgent | `agents/learning_agent.py` | Reward scoring, confidence updates, daily summary |
| ModelManager | `agents/model_manager.py` | LSTM training, inference, fine-tuning |
| LoggingAgent | `agents/logging_agent.py` | DB events, CSV journal, Telegram daily summary |

---

## Strategy Stack

| Strategy | File | Status |
|---|---|---|
| ICT/SMC | `strategies/ict_strategy.py` + `strategies/ict/` | **Active** — primary |
| Neural LSTM | `agents/neural_strategy.py` | **Active** — secondary |
| DeepSeek LLM | `strategies/deepseek_strategy.py` (via StrategyAgent) | **Active** — LLM-based |
| SMA Crossover | `strategies/sma_crossover.py` | Legacy / reference |

### DeepSeek Multi-Agent Mode
- `DEEPSEEK_AGENT_SWARM_ENABLED=true` enables parallel specialist LLM roles (trend/structure/risk)
- Responses are aggregated into one consensus signal (`deepseek_swarm`) with averaged SL/TP and confidence
- Feature is off by default and guarded behind env flags in `config/settings.py`
- Adaptive neural mesh (`DEEPSEEK_MESH_*`) learns per-agent trust/coherence and penalizes slow agents to improve speed and consensus stability over time
- Mesh graph state is now modeled explicitly via `models/agent_mesh.py` (`AgentNode`, `AgentEdge`, `AgentMeshState`)

### ICT Engine (10 modules in `strategies/ict/`)
`engine.py` → `liquidity.py`, `market_structure.py`, `fair_value_gaps.py`, `order_blocks.py`, `displacement.py`, `fibonacci.py`, `sessions.py`, `scoring.py`, `models.py`

### ICT Scoring (pillar upgrades implemented)
- **Pillar 3:** Entry snapped to FVG CE or OB midpoint; staleness gate (0.5× ATR forex, 2.0× ATR crypto/XAU)
- **Pillar 4:** TP4 runner targeting HTF liquidity; structural breakeven from swing levels

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
trades         — open/closed trade records (TP1-4, structural_be, lots, pnl, etc.)
events         — structured event log (level, source, message)
agent_events   — per-agent activity feed (agent, event_type, message, metadata)
strategy_confidence — per-strategy win/loss/confidence
broker_accounts — encrypted broker credentials
candle_cache   — OHLCV cache per symbol/timeframe
users          — dashboard user accounts (bcrypt passwords)
```

### Migration pattern (safe for existing tables):
```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE ...) THEN
    ALTER TABLE trades ADD COLUMN ...;
  END IF;
END $$;
```

---

## Key Configuration (`config/settings.py`)
All values from `.env`, never hardcoded. Key settings:
- `DEMO_MODE=False` — hardcoded, never change via env
- `TIMEZONE=Europe/Paris` — affects logs, day labels, daily summary
- `COUNCIL_MIN_CONFIDENCE=0.60`
- `LIMIT_ENTRY_MAX_DISTANCE_ATR=0.5` (forex), `LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO=2.0`
- `MAX_RISK_PER_TRADE=0.02`, `MAX_OPEN_TRADES=3`, `MAX_DAILY_LOSS=0.05`
- `CRUCIX_URL=http://localhost:3117`

---

## Frontend Dashboard (`web/`)
- **Framework:** Next.js 14 App Router
- **Auth:** NextAuth.js with JWT strategy + Edge middleware (`src/middleware.ts`)
- **Styling:** NO Tailwind on new/modified files — use inline styles only
- **No `className` on new JSX** (existing ones being migrated)
- **Pages:** overview, trades, analytics, ict, learning, strategy, chart, settings, agent_theater, world

### Dashboard API routes (`web/src/app/api/`)
`/api/status`, `/api/world`, `/api/trades`, `/api/events`, `/api/learning`, `/api/analytics`, `/api/ict`, `/api/candles`, `/api/commands`

---

## Models (`models/`)
- `Signal` — strategy output, includes `take_profit_4`, `structural_be`
- `Trade` — DB record, includes `tp4_lots`, `tp4_hit`, `structural_be`
- `Candle` — OHLCV
- `MarketContext` — full analysis context passed between agents
- `LSTMTradingModel` — in `models/neural_model.py`

---

## Key Utilities
- `utils/helpers.py` — `local_now()`, `is_weekend()`, `day_of_week()`, `current_session()`
- `utils/telegram_bot.py` — send_message()
- `filters/crucix_client.py` — CrucixClient, MacroContext, `get_macro_context()`

## Research Intake Workflow
- `backtesting/research_intake.py` — candidate scoring, checklist gates, promotion decision export
- `research/curated_sources.{json,yaml}` — trusted upstream source catalog
- `research/scoring_rubric.{json,yaml}` — weighted scoring model and promotion threshold
- `research/promotion_checklist.{json,yaml}` — hard gate criteria for promotion
- `research/candidate_backlog.json` — candidate queue for evaluation
- `scripts/backtest.py --research-intake` — runs the workflow and writes `backtesting/runs/research_intake.json`
- `GODMOD3 (MSL135/GODMOD3)` — intake reference for multi-model arbitration and context autotune experiments, scoped to governance-safe patterns only

---

## When to use this skill
- Before any architecture decision
- Before modifying the agent pipeline
- Before adding new symbols, strategies, or DB tables
- When unsure which file handles what
