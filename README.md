# PulseTrade TradingBot

> **Archived — this research continued elsewhere.**
>
> This is **stage 1 of 3**, written March–September 2026 and kept unchanged so
> the design history stays auditable, including what did not work. It grew to
> roughly 50,000 lines across a multi-agent pipeline, an LSTM, a LightGBM
> ensemble, GARCH/HMM regime detection and an LLM debate layer; once it was
> finally wired to a broker, the strategy measured **no edge**: 3,271 positions,
> 37.9% win rate, −0.431R average, profit factor 0.46, negative in every symbol
> and every fold.
>
> → Stage 2: [TradeBotV2](https://github.com/youcisla/TradeBotV2) — the measurement-first rebuild
> → Stage 3, current: [Zero-Trust-Trader](https://github.com/youcisla/Zero-Trust-Trader) — statistical gates, fail-closed, stands down

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/next.js-14-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Broker: MT5](https://img.shields.io/badge/broker-MetaTrader%205-blue.svg)](https://www.metatrader5.com/)

An autonomous algorithmic trading system for MetaTrader 5 with a layered ML model stack, 12-agent pipeline, and a Next.js real-time dashboard. Designed to trade 30 instruments across forex, commodities, crypto, and exotics on the H1 timeframe.

> **2026-04-18 — DeepSeek NL layer:** The bot now runs a natural language interface via Telegram (`/brief`, `/hypothesis`, free-text commands) powered by DeepSeek. LGBM models auto-train in background on first startup if no trained model is found.

---

## Feature Highlights

- **LSTM Neural Network** — per-symbol model trained on 2 years of H1 history; auto-trained at startup and retrained every 20 closed trades
- **ICT / SMC Engine** — 10-module Inner Circle Trader analysis (structure, liquidity, FVGs, order blocks, sessions, bias, scoring, 6 setup models)
- **Trade-History LightGBM** — classifier trained on closed-trade features to filter low-probability signals; auto-trains in background on startup if not yet trained
- **Price-History LightGBM** — per-symbol LightGBM trained on 12 OHLCV-derived features; auto-trains in background on startup; all data pulled from MT5
- **GARCH(1,1) + Kalman Filter** — real-time volatility forecasting and price-velocity estimation in every `MarketContext`
- **Crucix Macro Layer** — 27 global data sources (VIX, yield curve, geopolitics, OSINT); flash blackout and adaptive lot scaling
- **Scan-Rank-Execute Pipeline** — evaluates all 30 symbols, ranks signals by final confidence, executes the highest-quality opportunity
- **DeepSeek Natural Language Interface** — Telegram NL commands (`/brief`, `/hypothesis`, free-text); pre-session market briefs; auto-hypothesis testing cycle
- **Real-Time Dashboard** — Next.js 16 UI on Vercel; agent feed, open trades, equity curve, command panel
- **Intelligent Command Center** — Adaptive dashboard that surfaces what matters: live session chip, spread condition badge, market regime, VIX, equity drawdown gauges, severity-sorted agent feed, and AI-generated market insight
- **Strategy Plugin System** — inject custom strategies at runtime without modifying orchestration code

---

## Architecture

```
+------------------+        +----------------------+        +-------------------------+
|   Vercel          |        |   Supabase            |        |   Your PC / VPS          |
|   Next.js 14 UI  |<-------->   PostgreSQL (7 tbls) |<-------->   Python Bot (main.py)  |
|   (Dashboard)    |        |   (shared state)      |        |   12-agent pipeline     |
+------------------+        +----------------------+        +-----------+-------------+
                                                                        |
                                                             +----------v----------+
                                                             |   MetaTrader 5      |
                                                             |   (PU Prime / any)  |
                                                             +---------------------+
```

- **Python bot** — runs the full inference and execution pipeline on every loop iteration
- **Next.js dashboard** — read-only live view plus command panel; communicates via the `bot_commands` table
- **PostgreSQL** — shared single source of truth for bot and dashboard
- **MetaTrader 5** — broker connection for live OHLCV data, order placement, and account management

---

## ML Model Stack

Strategy signals pass through two sequential LightGBM filters before reaching the execution layer:

```
Strategy Signal  (LSTM | ICT/SMC | SMA)
        |
        +----> LightGBM Trade Filter     [models/lgbm_model.pkl]
        |      11 features from closed-trade history
        |      Confidence adjustment: +/- 10 %
        |
        +----> LightGBM Price Filter     [models/lgbm_price_{SYMBOL}.pkl]
               12 OHLCV-derived features, per symbol
               Confidence adjustment: +/- 15 %

               Final Score --> CouncilAgent --> RiskAgent --> Execution
```

Both filters fail-open (signal passes unchanged if the model file is missing) and are gated by `LGBM_ENSEMBLE_ENABLED`. LGBM models auto-train in the background at bot startup if no trained model is found.

| Feature | Description |
|---|---|
| `rsi_norm` | RSI normalised to [-1, +1] |
| `close_vs_ema20` | Distance from 20-period EMA |
| `close_vs_ema50` | Distance from 50-period EMA |
| `bb_pos` | Position within Bollinger Bands |
| `atr_ratio` | Current ATR vs 50-bar rolling average |
| `vol_ratio` | Volume vs 20-bar rolling average |
| `ema9_slope` | Slope of 9-period EMA |
| `garch_vol` | GARCH(1,1) conditional volatility forecast |
| `kalman_velocity` | Kalman filter price velocity |
| `session_enc` | Trading session: London=0, NY=1, Asia=2, Off=3 |
| `day_enc` | Day-of-week: Monday=0 ... Friday=4 |
| `spread_norm` | Normalised bid-ask spread |

Labels derive from forward returns relative to a 1x ATR threshold: **BUY = 0**, **HOLD = 1**, **SELL = 2**.

---

## Signal Pipeline

```
+-------------------------------------------------------------------+
|  PRE-SCAN  --  CrucixAgent.run()                                  |
|  Fetch macro state: VIX, yield curve, geopolitics, OSINT (27 src) |
|  FLASH alert  -->  full trading blackout                          |
|  PRIORITY     -->  50% lot scaling                                |
+-------------------------------+-----------------------------------+
                                |
+-------------------------------v-----------------------------------+
|  PHASE 1 -- SCAN  (all 30 symbols)                               |
|  MarketAgent --> AnalysisAgent (RSI / ATR / GARCH / Kalman)      |
|  --> StrategyAgent.detect_all()  (LSTM + ICT/SMC + SMA)          |
|  --> LightGBM Trade Filter --> LightGBM Price Filter              |
+-------------------------------+-----------------------------------+
                                |
+-------------------------------v-----------------------------------+
|  PHASE 2 -- RANK                                                  |
|  Sort all signals by final confidence (highest first)            |
|  Deduplicate by (symbol, direction) -- best signal wins          |
+-------------------------------+-----------------------------------+
                                |
+-------------------------------v-----------------------------------+
|  PHASE 3 -- EXECUTE                                               |
|  For each ranked signal:                                         |
|    CouncilAgent (3-expert gate)                                  |
|    --> RiskAgent (6-step validation)                              |
|    --> ExecutionAgent.open_trade()                               |
|  Stop when MAX_OPEN_TRADES is reached                            |
+-------------------------------------------------------------------+
```

---

## Agents

| Agent | File | Responsibility |
|---|---|---|
| **CrucixAgent** | `agents/crucix_agent.py` | Macro intelligence — 27 sources, VIX, yield curve, OSINT; flash blackout; adaptive lot scaling |
| **MarketAgent** | `agents/market_agent.py` | Fetches 100 H1 + 200 H4 candles from MT5; validates data integrity |
| **AnalysisAgent** | `agents/analysis_agent.py` | RSI, ATR, SMA, ADX, GARCH(1,1) volatility, Kalman filter velocity, regime detection |
| **StrategyAgent** | `agents/strategy_agent.py` | Runs all strategies, applies both LGBM filters, collects and ranks signals |
| **NeuralStrategy** | `agents/neural_strategy.py` | LSTM strategy wrapper; delegates inference to ModelManager |
| **ModelManager** | `agents/model_manager.py` | Per-symbol LSTM training, fine-tuning, and real-time inference |
| **CouncilAgent** | `agents/council_agent.py` | 3-expert algorithmic quality gate |
| **RiskAgent** | `agents/risk_agent.py` | 6-step risk validation gate |
| **ExecutionAgent** | `agents/execution_agent.py` | Order placement via broker connector; SL/TP calculation |
| **TradeManager** | `agents/trade_manager.py` | TP hit tracking, breakeven logic, trailing stop, partial close |
| **LearningAgent** | `agents/learning_agent.py` | Scores closed trades; adjusts per-strategy confidence values |
| **LoggingAgent** | `agents/logging_agent.py` | Structured logs, CSV trade journal, Telegram alerts |

---

## Strategies

### 1. LSTM Neural Network (Primary)

Per-symbol sequence model trained on 2 years of H1 OHLCV data. Trains in the background at bot startup and fine-tunes automatically after every 20 closed trades.

| Parameter | Value |
|---|---|
| Input features | 9 |
| Sequence length | 50 bars |
| Output | 3-class softmax (BUY / SELL / HOLD) |
| Min confidence | 60% |
| SL | 2 x ATR |
| TP1 / TP2 / TP3 | 1R / 2R / 3R |

### 2. ICT / Smart Money Concepts (Secondary)

Full Inner Circle Trader engine with 10 analysis modules and 6 setup models.

**Modules:** Structure, Liquidity, Displacement, Fair Value Gaps, Order Blocks, Sessions, Bias, Scoring, Setups

**HTF context:** 200 H4 candles for directional bias and premium/discount zone mapping

**Setup models:** OB Retracement, FVG Fill, Liquidity Sweep, BOS Continuation, MSS Reversal, Macro Scalp

| Parameter | Value |
|---|---|
| Output | 0-100 composite confidence score |
| Min confidence | 55 / 100 |
| HTF candles | 200 x H4 |

### 3. SMA Crossover (Tertiary / Fallback)

ATR-filtered moving average crossover. Activates when the LSTM model is not yet trained for the symbol or ICT conditions are not met.

---

## Symbols

30 instruments across 5 asset classes:

| Class | Symbols |
|---|---|
| **Forex Majors** | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD |
| **Forex Crosses** | EURGBP, EURJPY, GBPJPY, AUDJPY, NZDUSD, EURAUD, GBPAUD, EURCHF, GBPCHF, AUDNZD, CADJPY, CHFJPY |
| **Commodities** | XAUUSD, XAGUSD, USOIL, UKOIL |
| **Crypto** | BTCUSD, ETHUSD, LTCUSD, XRPUSD, SOLUSD |
| **Exotics** | USDZAR, USDMXN |

Market hours are enforced automatically. Crypto trades 24/7. Forex and commodities skip the Fri 22:00 – Sun 22:00 UTC weekend window.

---

## Project Structure

```
TradeBot/
+-- agents/                         # 12 autonomous agents
|   +-- crucix_agent.py             # Macro intelligence: 27 sources, blackout, lot scaling
|   +-- market_agent.py             # Live data fetch + integrity validation
|   +-- analysis_agent.py           # RSI, ATR, GARCH, Kalman, regime detection
|   +-- strategy_agent.py           # Strategy runner + dual LGBM filter chain
|   +-- neural_strategy.py          # LSTM strategy wrapper
|   +-- model_manager.py            # LSTM train / fine-tune / infer per symbol
|   +-- council_agent.py            # 3-expert quality gate
|   +-- risk_agent.py               # 6-step risk validation
|   +-- execution_agent.py          # Order placement
|   +-- trade_manager.py            # TP/SL management, trailing, partial close
|   +-- learning_agent.py           # Trade scoring + confidence adjustment
|   +-- logging_agent.py            # Logs, CSV journal, Telegram
+-- broker/
|   +-- connector.py                # Abstract BrokerConnector ABC
|   +-- mock_connector.py           # In-memory mock for CI / testing
|   +-- mt5_connector.py            # MetaTrader 5 connector
+-- config/
|   +-- settings.py                 # All parameters loaded from .env
|   +-- symbols.py                  # Symbol list across 5 asset classes
+-- crucix/                         # Crucix macro intelligence server (Node.js)
+-- database/
|   +-- db.py                       # PostgreSQL interface (psycopg2), 7 tables
+-- filters/
|   +-- crucix_client.py            # CrucixClient + MacroContext dataclass
|   +-- data_validator.py           # Stuck-quote and spike detection
+-- models/                         # Data models + trained ML artefacts
|   +-- market_data.py              # Candle, MarketData, MarketContext
|   +-- signal.py                   # Signal + EntrySnapshot
|   +-- trade.py                    # Trade dataclass
|   +-- ict_models.py               # 30+ ICT/SMC dataclasses
|   +-- neural_model.py             # LSTMTradingModel + FeatureNormalizer
|   +-- lgbm_ensemble.py            # Trade-history LightGBM inference wrapper
|   +-- lgbm_price_model.py         # Price-history LightGBM inference (per symbol)
|   +-- neural/                     # Saved LSTM weights: {SYMBOL}_H1.pt + .json
+-- scripts/
|   +-- train_lgbm.py               # Train trade-history LGBM from closed trades DB
|   +-- train_lgbm_price.py         # Train price-history LGBM per symbol from OHLCV
|   +-- backtest.py                 # CSV backtester + ML4T benchmark + research intake
|   +-- replay_session.py           # Deterministic session replay + parity validation
+-- state/
|   +-- persistence.py              # DB + broker reconciliation on startup
+-- strategies/
|   +-- base_strategy.py            # Strategy ABC
|   +-- sma_crossover.py            # SMA crossover with ATR stops (fallback)
|   +-- ict_strategy.py             # ICT/SMC strategy orchestrator
|   +-- ict/                        # 10-module ICT engine
|       +-- engine.py               # Unified ICT orchestrator
|       +-- structure.py            # Swing points, BOS/MSS, dealing ranges
|       +-- liquidity.py            # BSL/SSL mapping, sweep detection
|       +-- displacement.py         # Impulsive candle detection
|       +-- fvg.py                  # Fair Value Gap detection + fill tracking
|       +-- orderblock.py           # Order Block detection + validation
|       +-- session.py              # Killzones, macros, PDH/PDL/PWH/PWL
|       +-- bias.py                 # HTF bias, regime, premium/discount zones
|       +-- scoring.py              # 0-100 weighted confidence across 10 components
|       +-- setups.py               # 6 ICT setup model detectors
+-- backtesting/
|   +-- engine.py                   # CSV backtester (SL + 3 TPs)
|   +-- data_downloader.py          # Historical OHLCV downloader
+-- tests/                          # pytest test suite (251 pass)
+-- utils/
|   +-- helpers.py                  # Session / market-hours utilities
|   +-- telegram_bot.py             # Telegram alerts + remote commands
+-- web/                            # Next.js 14 dashboard (Vercel)
|   +-- src/app/                    # Routes: dashboard, trades, analytics, ict, learning, strategy
|   +-- src/components/             # TopBar, IntelligencePanel, SmartAlertFeed, NewDashboard, WorldStrip, etc.
|   +-- src/lib/                    # auth.ts, db.ts, time.ts
|   +-- vercel.json                 # Vercel deployment config
+-- logs/                           # Runtime logs (auto-created)
+-- main.py                         # Bot entry point
+-- start.ps1                       # Windows launcher script
+-- .env.example                    # Full environment variable template
+-- requirements.txt                # Python dependencies
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Tested on 3.11 and 3.12 |
| MetaTrader 5 | Latest | Windows only; use a VPS for remote operation |
| PostgreSQL | 14+ | Supabase free tier supported |
| Node.js | 18+ | Required for the web dashboard |
| MT5 Account | Any | Set `BROKER_SERVER` to match your broker |

---

## Setup

### 1. Python Bot

```bash
# Clone the repository
git clone https://github.com/youcisla/TradeBot.git
cd TradeBot

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your values -- see the Environment Variables section

# Start the bot
python main.py

# Alternatively, use the Windows launcher
.\start.ps1
```

### 2. Web Dashboard

```bash
cd web
npm install
npm run dev   # Local dev server at http://localhost:3000
```

**Vercel production deployment:**
1. Push your repository to GitHub
2. Import the project in Vercel with **Root Directory = `web`**
3. Add all required environment variables
4. Deploy

### 3. Database

Create a Supabase project (or any PostgreSQL 14+ instance). The bot creates all 7 required tables automatically on first startup. Both the Python bot and the Next.js dashboard connect to the same `DATABASE_URL`.

---

## Training ML Models

Both LGBM models auto-train in the background when the bot starts and no trained model is found. Logs are written to `logs/ml/`.

### Price-History LightGBM (per-symbol)

Downloads OHLCV data from MT5 and trains a LightGBM 3-class classifier for each symbol. Data always comes from MT5 (no CSV fallback).

```bash
# Train all symbols with default settings (H1, 2 years)
python -m scripts.train_lgbm_price

# Train specific symbols only
python -m scripts.train_lgbm_price --symbols EURUSD GBPUSD XAUUSD

# Tune label sensitivity (forward bars and ATR multiplier)
python -m scripts.train_lgbm_price --forward-bars 3 --atr-mult 1.2
```

Saved to: `models/lgbm_price_{SYMBOL}.pkl`

### Trade-History LightGBM

Trains on closed trades stored in the database. Recommended minimum: 20 closed trades.

```bash
python -m scripts.train_lgbm
```

Saved to: `models/lgbm_model.pkl`

### LSTM Models

LSTM models train automatically at bot startup for any symbol without a saved model file. To trigger manual retraining:

```bash
# Delete the saved model and restart -- the bot will retrain on startup
del models\neural\EURUSD_H1.pt
python main.py
```

---

## Runtime Profiles

Set `BOT_PROFILE` in `.env` or pass `-Profile` to `start.ps1`.

| Profile | Description |
|---|---|
| `custom` | Use raw `.env` values unchanged (default) |
| `dev` | Demo mode, faster iteration, conservative risk |
| `paper` | Strict simulation-only operation |
| `live-safe` | Blocking council, strict risk, instant-entry disabled |
| `live-full` | Full live mode with advisory council and fast-entry |

```powershell
.\start.ps1 -Profile paper
.\start.ps1 -Profile live-safe
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | -- | PostgreSQL connection string |
| `BROKER_ACCOUNT` | -- | -- | MT5 account number (omit for mock mode) |
| `BROKER_PASSWORD` | -- | -- | MT5 account password |
| `BROKER_SERVER` | -- | -- | MT5 server name (e.g. `PUPrime-Demo`) |
| `TELEGRAM_BOT_TOKEN` | -- | -- | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | -- | -- | Your Telegram chat ID |
| `CRUCIX_URL` | -- | `http://localhost:3117` | Crucix macro intelligence server URL |
| `LGBM_ENSEMBLE_ENABLED` | -- | `true` | Master switch for both LGBM filter gates |
| `BOT_PROFILE` | -- | `custom` | Runtime profile (see above) |
| `MAX_OPEN_TRADES` | -- | `3` | Maximum concurrent open positions |
| `RISK_PER_TRADE` | -- | `0.01` | Fraction of account balance risked per trade |
| `NEXTAUTH_SECRET` | Web | -- | Secret for Next.js session encryption |
| `NEXTAUTH_URL` | Web | -- | Public dashboard URL |
| `DASHBOARD_PASSWORD` | Web | -- | Password to access the web UI |

> If all three broker fields (`BROKER_ACCOUNT`, `BROKER_PASSWORD`, `BROKER_SERVER`) are set, the bot connects to MetaTrader 5. Otherwise it falls back to the in-memory `MockConnector`.

See `.env.example` for the complete list including ICT thresholds, execution parameters, and loop timing.

---

## Risk Management

Every signal passes a mandatory 6-step validation gate before a trade is opened:

1. **Drawdown circuit breaker** — halts new trades if the daily loss exceeds 5%
2. **Macro blackout** — blocks trading when Crucix emits a FLASH-level macro alert
3. **Duplicate guard** — rejects if an open trade already matches the same symbol + direction + strategy
4. **Correlation guard** — rejects if the same symbol + direction is already open from any strategy
5. **Spread filter** — rejects when the bid-ask spread exceeds 3 pips (threshold is asset-class aware)
6. **Position sizing** — risk-based lot calculation scaled by signal confidence and Crucix macro context

**Macro lot scaling:** `CLEAR -> 100%` | `ROUTINE -> 75%` | `PRIORITY -> 50%`

---

## Logging and Data Storage

### Database Tables

| Table | Purpose |
|---|---|
| `trades` | Full lifecycle of every trade: open, partial close, close |
| `trade_scores` | LearningAgent scoring record for each closed trade |
| `strategy_confidence` | Per-strategy confidence values over time |
| `agent_events` | Timestamped entries from all 12 agents (powers the dashboard feed) |
| `bot_commands` | Command queue from dashboard UI to the bot |
| `bot_status` | Single-row heartbeat: state, equity, open trades, daily PnL, spread condition, session, regime, VIX, drawdown % |
| `ict_setups` | ICT/SMC setup analysis log with confluences and scoring breakdown |

### File Logs

| File | Purpose |
|---|---|
| `logs/backend/backend_YYYY-MM-DD.log` | Full DEBUG-level rotating log (5 MB, 5 backups) |
| `logs/backend/trade_journal.csv` | Every trade with all fields -- importable into Excel or pandas |
| `logs/ml/train_lgbm.log` | LGBMEnsemble training log (daily rotating, 14-day retention) |
| `logs/ml/train_lgbm_price.log` | Per-symbol LGBM price model training log (daily rotating, 14-day retention) |
| `logs/frontend/dev_server.log` | Next.js (frontend) stdout/stderr |

### Telegram Alerts

- Trade opened / closed notifications with symbol, direction, and lot size
- TP1 / TP2 / TP3 / SL hit alerts
- Daily summary: wins, losses, PnL, win rate
- Remote commands via chat: `/kill`, `/status`, `/pause`, `/resume`

---

## Web Dashboard

Live at `https://trade-bot-ki33.vercel.app`:

| Page | Content |
|---|---|
| **Dashboard** | Intelligent command center — live session chip, equity/KPI bar, TradingView chart, smart alert feed, trade table |
| **Trades** | Full trade history with TP hits, PnL, duration, and strategy attribution |
| **Analytics** | Performance charts, symbol breakdown, session analysis with timezone support |
| **Brain** | Neural/stategy insights and mesh visualization |
| **Learning** | Per-strategy confidence bars and score history |
| **Risk** | Real-time risk gauges — daily loss %, equity drawdown, spread condition, VIX |
| **Markets** | Market intel, session timing, spread monitoring |
| **Signals** | Active signal pipeline, confidence scores, council decisions |
| **Health** | Bot health diagnostics, agent mesh status, uptime |

---

## Strategy Plugin System

Extend the bot with custom strategies without touching orchestration code:

1. Implement a class that inherits `BaseStrategy`
2. Ensure the class is importable by dotted Python path
3. Register it in `.env`:

```env
STRATEGY_PLUGINS=my_package.my_strategy.MyStrategy
```

Plugins are auto-loaded at startup and participate in the unified scan-rank-execute pipeline.

---

## Backtesting

```bash
# CSV-based backtest with SL + 3 TPs
python scripts/backtest.py

# ML4T benchmark with purged walk-forward validation
python scripts/backtest.py --ml4t-benchmark --purge-size 5 --embargo-size 3

# Research intake scoring and promotion gates (exports experiment artefact)
python scripts/backtest.py --research-intake

# Deterministic session replay + parity validation before live rollout
python scripts/replay_session.py --symbol EURUSD --data backtesting/data/EURUSD_H1.csv
```

---

## Testing

```bash
python -m pytest tests/ -v
```

**Current baseline:** 251 pass / 23 pre-existing failures.

The 23 failures are isolated to database connection tests and execution-agent integration tests that require a live MT5 connection. They are expected to fail in CI and do not indicate any regressions from ML or strategy changes.

---

## Operations

**Incident and recovery playbook:** `docs/incident-recovery-playbook.md`

**Replay artefacts:** `backtesting/runs/*_replay_artifact.json`

**Research governance artefacts:**

```
research/curated_sources.{json,yaml}
research/scoring_rubric.{json,yaml}
research/promotion_checklist.{json,yaml}
research/candidate_backlog.json
```

Research promotion scoring is uncertainty-aware: candidate posterior scores are penalised when evidence is sparse or model uncertainty is high, before any promotion gates are evaluated.

---

## License

MIT (c) Youcef
