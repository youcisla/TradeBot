# TradingBot — Claude Code Project Rules

## MANDATORY: Do This Before Every Response

1. **Read the relevant skills** in `.claude/skills/` that apply to the task (use the `Skill` tool or read files directly)
2. **Read the current state of the files** you are about to touch — never assume you remember them from a previous session
3. **Check memory** at `C:\Users\Youcef\.claude\projects\c--Users-Youcef-Downloads-TradeBot\memory\` for any relevant user preferences or project state
4. **Only then act** — plan, implement, verify

Never skip step 1-3. Never write code based on memory alone. Always read → then write.

---

## Project Identity

**Name:** PulseTrade TradingBot
**Stack:** Python (bot) + Next.js 14 App Router (dashboard)
**Broker:** PU Prime via MetaTrader 5
**DB:** PostgreSQL (Supabase) — 7 tables
**Dashboard URL:** Next.js app in `web/`
**Primary strategy:** LSTM Neural Network (per-symbol, auto-trained on 2yr H1 history)
**Legacy strategies:** ICT/SMC engine, SMA Crossover (kept for reference, not active in main loop)

---

## Skill Index

| Skill | When to use |
|---|---|
| `trading-bot-overview` | Architecture decisions, agent pipeline, system design |
| `implement-agent` | Building or modifying any agent |
| `add-strategy` | Creating or modifying a trading strategy |
| `trade-execution` | SL/TP/partial close/breakeven logic |
| `learning-system` | Reward scoring, confidence adjustment |
| `configure-infra` | Infra, API keys, deployment, broker config |
| `coding-standards` | UI/UX, code style, frontend patterns (READ THIS for any web work) |
| `prompt-guide` | How to write expert prompts for DeepSeek/Claude |
| `guard-pipeline` | GuardPipeline, guards.py, ExposureCoach — pre-execution safety |
| `ml-pipeline` | LGBMEnsemble, GARCH regime, Kalman filter, feature pipeline |
| `intelligence-sweep` | IntelligenceSweep, MacroSnapshot, FRED/yfinance/EIA/GDELT sources |

**Before writing any frontend code → read `coding-standards` skill first.**

---

## Agent Pipeline (current)

```
PIPELINE:  crucix → market → analysis → strategy → neural → council → risk → execution → trade_manager
SUPPORT:   learning · model_manager · logging · debate · exposure · memory
```

Agent event keys in DB (for `AgentFeed.tsx`):
- `crucix`, `market`, `analysis`, `strategy`, `neural`, `council`, `risk`, `execution`, `trade_manager`
- `learning`, `model_manager`, `logging`, `debate`, `exposure`, `memory`

---

## Key Files

```
main.py                          ← Bot entry point
agents/
  crucix_agent.py                ← Macro intelligence (wraps CrucixClient)
  market_agent.py                ← Candles, ATR/RSI/SMA, news blackout
  analysis_agent.py              ← Regime, trend direction, session
  strategy_agent.py              ← Runs all strategies, returns best Signal
  council_agent.py               ← 4-expert LLM gate
  risk_agent.py                  ← Lot sizing, spread check, daily loss cap
  execution_agent.py             ← Opens orders, TP lot splits, GuardPipeline gate
  trade_manager.py               ← Monitors trades, TP hits, SL, breakeven
  learning_agent.py              ← Reward scoring, confidence updates
  logging_agent.py               ← DB events, CSV journal, Telegram summary
  debate_agent.py                ← Bull/bear LLM debate gate (DEBATE_ENABLED)
  exposure_agent.py              ← Portfolio exposure directive (EXPOSURE_ENABLED)
  memory_agent.py                ← Cross-session memory blocks (bot_memory table)
  guards.py                      ← GuardPipeline + 7 guards
  exposure_coach.py              ← Concentration/correlation advisor
  deepseek_strategy.py           ← DeepSeek LLM strategy (via StrategyAgent)
  reflector.py                   ← Post-trade reflection utility
  signal_postmortem.py           ← Trade postmortem analysis

filters/
  crucix_client.py               ← CrucixClient + MacroContext
  intelligence_sweep.py          ← Async FRED/yfinance/EIA/GDELT macro aggregator
  data_validator.py              ← Input data validation

models/
  signal.py                      ← Signal dataclass (tp1–tp4, structural_be, bull/bear_case)
  trade.py                       ← Trade dataclass (tp1–tp4 lots/hits, structural_be)
  agent_mesh.py                  ← AgentNode, AgentEdge, AgentMeshState (DeepSeek mesh)
  lgbm_ensemble.py               ← LightGBM 3-class classifier (BUY/SELL/HOLD)
  lgbm_price_model.py            ← LightGBM price prediction model
  lgbm_model.pkl                 ← Saved LGBM weights
  garch_regime.py                ← GARCH(1,1) + EWMA regime detector
  market_data.py                 ← Market data helpers
  ict_models.py                  ← ICT dataclasses (OB, FVG, etc.)
  memories/                      ← Model memory storage

features/
  macro_features.py              ← MacroSnapshot → 15-float z-scored vector
  microstructure.py              ← Spread, imbalance, Kyle's lambda, wick asymmetry

strategies/
  ict_strategy.py                ← ICT/SMC engine (primary active strategy)
  ict/                           ← 10 ICT modules (engine, liquidity, fvg, ob, etc.)
  unified_strategy.py            ← Strategy aggregator
  plugin_loader.py               ← Dynamic strategy loading
  base_strategy.py               ← Strategy base class
  sma_crossover.py               ← Legacy / reference only

broker/
  connector.py                   ← BrokerConnector interface
  mt5_connector.py               ← MetaTrader 5 implementation
  mock_connector.py              ← Test mock

state/
  persistence.py                 ← StatePersistence
  event_log.py                   ← NDJSON event logger
  heartbeat.py                   ← Daemon heartbeat writer

utils/
  helpers.py                     ← local_now(), is_weekend(), current_session()
  telegram_bot.py                ← send_message(), pause(), resume()
  telegram_reports.py            ← Formatted Telegram report builders
  mesh_bus.py                    ← mesh_span() tracing context
  skill_manager.py               ← Runtime skill management
  tool_system.py                 ← Tool registry
  ops_doctor.py                  ← Self-diagnostics
  kalman_filter.py               ← 2D Kalman price smoother
  dynamic_position_sizer.py      ← Kelly/ATR-based lot sizing
  concept_drift_detector.py      ← Model drift detection
  correlation_gate.py            ← Cross-symbol correlation filter
  hedge_stripper.py              ← Hedge detection/removal
  symbol_event_tracker.py        ← Per-symbol event tracking

backtesting/
  engine.py                      ← Backtesting engine
  walk_forward.py                ← Walk-forward validation
  walk_forward_optimizer.py      ← WF parameter optimizer
  factor_library.py              ← Alpha factor library
  research_intake.py             ← Research candidate scoring + promotion
  baseline_benchmarks.py         ← Benchmark comparison
  public_api_intake.py           ← Public API data ingestion
  report.py                      ← Backtest report generator

config/
  settings.py                    ← All env-driven config
  symbols.py                     ← Symbol metadata (pip size, contract size, etc.)

scripts/
  backtest.py                    ← CLI backtest runner
  train_lgbm.py                  ← Train LGBM ensemble
  train_lgbm_price.py            ← Train LGBM price model
  ops_doctor.py                  ← Ops diagnostics runner
  first_run_wizard.py            ← Guided first-run setup
  replay_session.py              ← Replay a past trading session

database/db.py                   ← PostgreSQL client (psycopg2 ThreadedConnectionPool)
tests/                           ← 422 tests; run: python -m pytest --tb=no -q
web/                             ← Next.js 14 dashboard
  src/app/dashboard/             ← Pages: overview, analytics, trades, learning,
                                    strategy, ict, settings, chart, agent_theater, world
  src/components/                ← Shared components
```

---

## Skills Infrastructure

Project-specific skills live in `.claude/skills/` (read by Claude at the start of each session).

1,322 general-purpose skills are installed globally from the antigravity submodule:
```
antigravity-awesome-skills/   ← git submodule (https://github.com/youcisla/antigravity-awesome-skills)
~/.claude/skills/             ← installed via: node antigravity-awesome-skills/tools/bin/install.js --claude
```

To reinstall after pulling submodule updates:
```bash
git submodule update --remote antigravity-awesome-skills
node antigravity-awesome-skills/tools/bin/install.js --claude
```

---

## Skill Update Rule

When you learn something new about this project (new file, new pattern, design decision, user preference), **update the relevant skill file immediately**. Skills must always reflect the current state of the project — they are the source of truth for future sessions.

---

## What NOT to Do

- Do not use Tailwind CSS classes on any new or modified frontend file — always use inline styles
- Do not use `className` in new JSX (existing ones being migrated, do not add new ones)
- Do not skip reading files before editing them
- Do not invent file paths or API shapes — verify them first
- Do not commit without asking
- Do not push without asking
