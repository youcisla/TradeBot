# Trading Bot

Autonomous Python trading bot with a Next.js web dashboard. Connects to MetaTrader 5 for live/demo trading, stores everything in PostgreSQL (Supabase), and shows real-time status on a Vercel-hosted UI. Features an ICT/SMC strategy engine and a smart scan-rank-execute pipeline that never misses the best opportunity.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Vercel          │      │  Supabase        │      │  Your PC / VPS   │
│  (Next.js UI)    │◄────►│  PostgreSQL      │◄────►│  (Python bot)    │
│  Dashboard       │      │  (shared DB)     │      │  main.py         │
└─────────────────┘      └──────────────────┘      └──────────────────┘
                                                          │
                                                    ┌─────┴─────┐
                                                    │ MetaTrader │
                                                    │    5       │
                                                    └───────────┘
```

- **Python bot** runs locally or on a VPS — manages the trading loop, agents, and broker connection
- **Next.js dashboard** runs on Vercel — read-only view + command panel
- **PostgreSQL** is the shared state — both sides read/write the same DB
- Communication is via the `bot_commands` table (command queue pattern)

## Project Structure

```
├── agents/                  # 8 autonomous agents
│   ├── market_agent.py      # Fetches & validates live market data (250 candles)
│   ├── analysis_agent.py    # SMA, RSI, ATR, regime detection
│   ├── strategy_agent.py    # Runs ALL strategies, collects ALL signals
│   ├── risk_agent.py        # 7-step risk validation gate
│   ├── execution_agent.py   # Places orders via broker
│   ├── trade_manager.py     # TP/SL, breakeven, trailing, partial close
│   ├── learning_agent.py    # Scores trades, adjusts confidence
│   └── logging_agent.py     # Structured logs, CSV journal, Telegram
├── broker/
│   ├── connector.py         # Abstract BrokerConnector ABC
│   ├── mock_connector.py    # In-memory mock for testing
│   └── mt5_connector.py     # Real MetaTrader 5 connector
├── config/
│   ├── settings.py          # All params from .env
│   └── symbols.py           # 30 symbols across 5 asset classes
├── database/
│   ├── db.py                # PostgreSQL (psycopg2) — 7 tables
│   └── cleanup_mock_data.sql # SQL to purge mock/demo data
├── filters/
│   ├── data_validator.py    # Stuck quote / spike detection
│   └── news_filter.py       # Economic calendar blackout
├── models/
│   ├── trade.py             # Trade dataclass
│   ├── signal.py            # Signal + EntrySnapshot
│   ├── market_data.py       # Candle, MarketData, MarketContext
│   └── ict_models.py        # ICT/SMC data structures (30+ dataclasses)
├── state/
│   └── persistence.py       # DB + broker reconciliation
├── strategies/
│   ├── base_strategy.py     # Strategy ABC
│   ├── sma_crossover.py     # SMA crossover w/ ATR stops (fallback)
│   ├── ict_strategy.py      # ICT/SMC strategy (primary)
│   └── ict/                 # ICT/SMC engine — 10 modules
│       ├── engine.py        # Unified orchestrator
│       ├── structure.py     # Swing points, BOS/MSS, dealing ranges
│       ├── liquidity.py     # BSL/SSL mapping, sweep detection
│       ├── displacement.py  # Impulsive candle detection
│       ├── fvg.py           # Fair Value Gap detection + fill tracking
│       ├── orderblock.py    # Order Block detection + validation
│       ├── session.py       # Killzones, macros, PDH/PDL/PWH/PWL
│       ├── bias.py          # HTF bias, regime, premium/discount
│       ├── scoring.py       # 0-100 confidence scoring (10 components)
│       └── setups.py        # 6 setup model detectors
├── backtesting/
│   └── engine.py            # CSV-based backtester with SL+3 TPs
├── utils/
│   ├── helpers.py           # Session/day utilities, market hours
│   └── telegram_bot.py      # Telegram alerts + commands
├── tests/                   # Unit tests (pytest)
│   ├── test_ict_engine.py   # 30+ ICT engine tests
│   ├── test_strategy_agent.py
│   ├── test_risk_agent.py
│   ├── test_execution_agent.py
│   ├── test_trade_manager.py
│   ├── test_learning_agent.py
│   ├── test_market_agent.py
│   ├── test_analysis_agent.py
│   └── test_logging_agent.py
├── logs/                    # Runtime logs (auto-created)
│   ├── bot_YYYY-MM-DD.log   # Rotating daily log (DEBUG level)
│   └── trade_journal.csv    # Every trade open/close for analysis
├── web/                     # Next.js dashboard
│   ├── src/app/             # Pages: dashboard, trades, learning, analytics, ICT, strategy
│   ├── src/components/      # BotStatusBar, AgentFeed, OpenTradesTable, SymbolFilter, etc.
│   ├── src/lib/             # auth.ts, db.ts, time.ts
│   └── vercel.json          # Deployment config
├── main.py                  # Entry point — scan-rank-execute pipeline
├── start.ps1                # Windows launcher script
├── .env.example             # Template for all env vars
└── requirements.txt         # Python dependencies
```

## Strategies

### ICT/SMC Strategy (Primary)
Full Inner Circle Trader / Smart Money Concepts engine with 10 analysis modules:

- **Market Structure** — Swing highs/lows, Break of Structure (BOS), Market Structure Shift (MSS), dealing ranges
- **Liquidity** — Buy-Side/Sell-Side Liquidity mapping, sweep detection
- **Displacement** — Impulsive candle detection (large body, small wicks)
- **Fair Value Gaps** — FVG detection, fill/failure tracking
- **Order Blocks** — OB detection, validation, high-probability marking
- **Sessions** — Killzone timing (London, NY, Asia), macro windows, PDH/PDL/PWH/PWL
- **Bias** — HTF directional bias, premium/discount zones, market regime
- **Scoring** — 0–100 weighted confidence across 10 components
- **Setups** — 6 ICT setup models (OB Retracement, FVG Fill, Liquidity Sweep, BOS Continuation, MSS Reversal, Macro Scalp)

Ships with 200 H4 candles for HTF analysis. Minimum confidence threshold: 55/100.

### SMA Crossover (Fallback)
Simple moving average crossover with ATR-based stops. Used as a secondary strategy when ICT conditions aren't met.

## Signal Pipeline

The bot uses a **scan-all → rank → execute-best** pipeline to never miss the highest-confidence opportunity:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: SCAN                                                  │
│  For each symbol (30 symbols, 5 asset classes):                 │
│    MarketAgent → AnalysisAgent → StrategyAgent.detect_all()     │
│    Collect ALL signals from ALL strategies                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  PHASE 2: RANK                                                  │
│  Sort all signals by confidence (highest first)                 │
│  Deduplicate by (symbol, direction) — best signal wins          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  PHASE 3: EXECUTE                                               │
│  For each ranked signal:                                        │
│    RiskAgent.validate() → ExecutionAgent.open_trade()            │
│    Stop when MAX_OPEN_TRADES reached or all signals processed   │
└─────────────────────────────────────────────────────────────────┘
```

This replaces the old sequential per-symbol loop. A 95-confidence GBPUSD setup always beats a 56-confidence EURUSD signal, regardless of iteration order.

## Symbols

30 symbols across 5 asset classes:

| Class | Symbols |
|---|---|
| **Forex Majors** | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD |
| **Forex Crosses** | EURGBP, EURJPY, GBPJPY, AUDJPY, NZDUSD, EURAUD, GBPAUD, EURCHF, GBPCHF, AUDNZD, CADJPY, CHFJPY |
| **Commodities** | XAUUSD, XAGUSD, USOIL, UKOIL |
| **Crypto** | BTCUSD, ETHUSD, LTCUSD, XRPUSD, SOLUSD |
| **Exotics** | USDZAR, USDMXN |

Market hours are automatically detected — crypto trades 24/7, forex/commodities skip weekends (Fri 22:00–Sun 22:00 UTC).

## Setup

### 1. Python Bot

```bash
# Clone and enter
git clone https://github.com/youcisla/TradeBot.git
cd TradeBot

# Create venv
python -m venv .venv
.venv\Scripts\Activate.ps1    # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Run
python main.py
# Or use the launcher:
.\start.ps1
```

### 2. Web Dashboard (Vercel)

```bash
cd web
npm install
npm run dev    # Local dev at http://localhost:3000
```

For production: push to GitHub, import in Vercel with Root Directory = `web`, add env vars, deploy.

### 3. Database

Create a Supabase project (or any Postgres). Tables are created automatically on first bot startup. Both the Python bot and Next.js dashboard connect to the same DB.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `BROKER_ACCOUNT` | No* | MT5 account number (empty = mock mode) |
| `BROKER_PASSWORD` | No* | MT5 password |
| `BROKER_SERVER` | No* | MT5 server (e.g. `PUPrime-Demo`) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | No | Your Telegram chat ID |
| `NEXTAUTH_SECRET` | Web | Random secret for session encryption |
| `NEXTAUTH_URL` | Web | Dashboard URL (e.g. `https://trade-bot.vercel.app`) |
| `DASHBOARD_PASSWORD` | Web | Password to access the web UI |

*If all 3 broker fields are set, the bot connects to MT5. Otherwise it uses MockConnector.

See `.env.example` for the full list including risk, execution, and loop parameters.

## Logging & Data Storage

Everything is logged for future analysis across multiple layers:

### Database (PostgreSQL)
| Table | Purpose |
|---|---|
| `trades` | Every trade: open, partial, closed — full lifecycle |
| `trade_scores` | Learning system scoring per closed trade |
| `strategy_confidence` | Per-strategy confidence values |
| `agent_events` | Persona-style log from all 8 agents (feed for dashboard) |
| `bot_commands` | Command queue (UI → bot) |
| `bot_status` | Single-row heartbeat (state, equity, open trades, daily PnL) |
| `ict_setups` | ICT/SMC setup analysis log (model, confluences, scoring) |

### File System (`logs/`)
| File | Purpose |
|---|---|
| `bot_YYYY-MM-DD.log` | Full DEBUG-level rotating log (5MB, 5 backups) |
| `trade_journal.csv` | Every trade with all fields — importable into Excel/pandas |

### Telegram
- Trade opened/closed alerts
- TP/SL hit notifications
- Daily summary (wins, losses, PnL, win rate)
- Remote commands: `/kill`, `/status`, `/pause`, `/resume`

## Risk Management

7-step validation (all must pass):
1. **Drawdown circuit breaker** — halts trading if daily loss > 5%
2. **Duplicate guard** — no same symbol+direction+strategy twice
3. **Correlation guard** — no same symbol+direction from different strategies
4. **News blackout** — no trades near high-impact news events
5. **Spread check** — rejects if spread > 3 pips
6. **Max open trades** — default 3 maximum
7. **Position sizing** — risk-based lot calculation with confidence scaling

## Tests

```bash
python -m pytest tests/ -v
```

## Web Dashboard

Terminal/hacker aesthetic at `https://trade-bot-ki33.vercel.app`:

- **Dashboard** — bot status bar, live agent feed, open trades, command panel, equity curve
- **Trades** — full trade history with TP hits, PnL, timing
- **Analytics** — performance charts, symbol breakdown, session analysis (with timezone support)
- **ICT** — ICT/SMC setup analysis: model distribution, confluence frequency, session stats, scoring breakdown
- **Strategy** — strategy explanation and methodology details
- **Learning** — strategy confidence bars, score history
- **Commands** — pause, resume, kill, close individual trades