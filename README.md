# Trading Bot

Autonomous Python trading bot with a Next.js web dashboard. Connects to MetaTrader 5 for live/demo trading, stores everything in PostgreSQL (Supabase), and shows real-time status on a Vercel-hosted UI.

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
│   ├── market_agent.py      # Fetches & validates live market data
│   ├── analysis_agent.py    # SMA, RSI, ATR, regime detection
│   ├── strategy_agent.py    # Runs strategies, emits signals
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
│   └── symbols.py           # Tradeable symbols + pip values
├── database/
│   └── db.py                # PostgreSQL (psycopg2) — 6 tables
├── filters/
│   ├── data_validator.py    # Stuck quote / spike detection
│   └── news_filter.py       # Economic calendar blackout
├── models/
│   ├── trade.py             # Trade dataclass
│   ├── signal.py            # Signal + EntrySnapshot
│   └── market_data.py       # Candle, MarketData, MarketContext
├── state/
│   └── persistence.py       # DB + broker reconciliation
├── strategies/
│   ├── base_strategy.py     # Strategy ABC
│   └── sma_crossover.py     # SMA crossover w/ ATR stops
├── utils/
│   ├── helpers.py           # Session/day utilities
│   └── telegram_bot.py      # Telegram alerts + commands
├── tests/                   # 59 unit tests (pytest)
├── logs/                    # Runtime logs (auto-created)
│   ├── bot_YYYY-MM-DD.log   # Rotating daily log (DEBUG level)
│   └── trade_journal.csv    # Every trade open/close for analysis
├── web/                     # Next.js 14 dashboard
│   ├── src/app/             # Pages: login, dashboard, trades, learning
│   ├── src/components/      # BotStatusBar, AgentFeed, OpenTradesTable, etc.
│   ├── src/lib/             # auth.ts, db.ts
│   └── vercel.json          # Deployment config
├── main.py                  # Entry point — wires everything
├── .env.example             # Template for all env vars
└── requirements.txt         # Python dependencies
```

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

## Agent Pipeline

Each loop iteration (default 60s):

```
MarketAgent → AnalysisAgent → StrategyAgent → RiskAgent → ExecutionAgent
                                                              │
TradeManager ← monitors open trades (TP1/TP2/TP3, SL, trail) ┘
                    │
              LearningAgent ← scores closed trades, adjusts confidence
                    │
              LoggingAgent ← records everything to DB, CSV, Telegram
```

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
# 59 tests, 0 warnings
```

## Web Dashboard

Terminal/hacker aesthetic at `https://trade-bot-ki33.vercel.app`:

- **Dashboard** — bot status bar, live agent feed, open trades, command panel, equity curve
- **Trades** — full trade history with TP hits, PnL, timing
- **Learning** — strategy confidence bars, score history
- **Commands** — pause, resume, kill, close individual trades