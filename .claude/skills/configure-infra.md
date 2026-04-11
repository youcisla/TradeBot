---
name: configure-infra
description: "Infra, API keys, deployment, broker config, .env variables, and DB setup for PulseTrade."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Infrastructure & Configuration

## .env File — Required Variables

```env
# ── Broker (MetaTrader 5 / PU Prime) ──────────────────────────────────────
BROKER_ACCOUNT=123456789
BROKER_PASSWORD=your_password
BROKER_SERVER=PUPrimeLtd-Demo   # or PUPrimeLtd-Live

# ── Database (PostgreSQL / Supabase) ──────────────────────────────────────
DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── Telegram Alerts ───────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=-1001234567890

# ── DeepSeek LLM ──────────────────────────────────────────────────────────
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat            # or deepseek-reasoner
DEEPSEEK_MIN_CONFIDENCE=0.65
DEEPSEEK_CACHE_MINUTES=30

# ── Trading Council ───────────────────────────────────────────────────────
COUNCIL_ENABLED=true
COUNCIL_MIN_CONFIDENCE=0.60   # WARNING: do NOT raise above 0.70

# ── Risk ──────────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE=0.02        # 2% of equity per trade
MAX_OPEN_TRADES=3
MAX_DAILY_LOSS=0.05            # 5% equity drawdown cap

# ── Crucix Intelligence ───────────────────────────────────────────────────
CRUCIX_URL=http://localhost:3117

# ── Misc ──────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
TIMEZONE=Europe/Paris
LOOP_INTERVAL_SECONDS=30
```

## All Settings Keys (config/settings.py)

| Key | Default | Notes |
|---|---|---|
| `BROKER_ACCOUNT` | "" | MT5 login number |
| `BROKER_PASSWORD` | "" | MT5 password |
| `BROKER_SERVER` | "" | MT5 server string |
| `DATABASE_URL` | "" | Postgres connection string |
| `TELEGRAM_BOT_TOKEN` | "" | |
| `TELEGRAM_CHAT_ID` | "" | Group/channel ID |
| `DEEPSEEK_API_KEY` | "" | |
| `DEEPSEEK_MODEL` | `deepseek-chat` | |
| `DEEPSEEK_MIN_CONFIDENCE` | 0.65 | min for deepseek signals |
| `DEEPSEEK_CACHE_MINUTES` | 30 | reuse window |
| `COUNCIL_ENABLED` | true | |
| `COUNCIL_MIN_CONFIDENCE` | 0.60 | **Do NOT raise above 0.70** |
| `MAX_RISK_PER_TRADE` | 0.02 | fraction of equity |
| `MAX_OPEN_TRADES` | 3 | |
| `MAX_DAILY_LOSS` | 0.05 | |
| `MAX_SPREAD_PIPS` | 3.0 | forex pairs |
| `MAX_SPREAD_PCT_CRYPTO` | 2.5 | % of price |
| `MAX_SPREAD_PIPS_COMMODITY` | 10.0 | XAU etc. |
| `MAX_SPREAD_PIPS_EXOTIC` | 15.0 | |
| `TP1_CLOSE_PERCENT` | 0.40 | |
| `TP2_CLOSE_PERCENT` | 0.30 | |
| `TP3_CLOSE_PERCENT` | 0.20 | |
| `TP4_CLOSE_PERCENT` | 0.10 | runner slice |
| `TRAILING_STOP_DISTANCE_PIPS` | 20 | after TP2 |
| `COMMISSION_PER_LOT` | 7.0 | PU Prime round-trip |
| `LIMIT_ENTRY_MAX_DISTANCE_ATR` | 0.5 | staleness gate (forex) |
| `LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO` | 2.0 | staleness gate (BTC/XAU) |
| `LOOP_INTERVAL_SECONDS` | 30 | |
| `CRUCIX_URL` | `http://localhost:3117` | |
| `TIMEZONE` | `Europe/Paris` | IANA name |
| `WEEKEND_SYMBOLS` | `BTCUSD` | comma-separated |
| `LOG_LEVEL` | `INFO` | |
| `DAILY_SUMMARY_HOUR` | 17 | local time, Europe/Paris |

## Database (PostgreSQL / Supabase)

The bot uses a single `Database` class in `database/db.py`. On first run it auto-creates all tables via `_init_tables()`.

### Tables
```
trades          — one row per trade lifecycle
agent_events    — live feed for dashboard AgentFeed
events          — legacy structured event log
learning_stats  — per-strategy confidence + win/loss counts
symbol_stats    — ATR cache, spread cache
model_metadata  — LSTM model version + accuracy per symbol
candle_cache    — optional; populated by backtesting module
```

### Common Ops
```python
db = Database(settings.DATABASE_URL)

# Trade management
db.upsert_trade(trade)
db.get_open_trades()           # → list[Trade]
db.get_closed_trades(limit=50)

# Learning
db.get_confidence("ict_smc:TREND_CONTINUATION_LONG")  # → float
db.update_confidence("ict_smc:...", wins=1, losses=0)
db.get_learning_report()

# Logging
db.log_event("INFO", "MAIN", "Bot started")
db.log_agent_event("risk", "warn", "Spread too wide", {"spread": 4.2})
```

## MT5 Broker Integration

The broker module lives in `broker/mt5_broker.py`. It wraps `MetaTrader5` directly.

### Connection
```python
import MetaTrader5 as mt5
mt5.initialize(
    path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",  # optional
    login=int(settings.BROKER_ACCOUNT),
    password=settings.BROKER_PASSWORD,
    server=settings.BROKER_SERVER,
)
```

### Symbol Mapping
PU Prime uses broker-prefixed symbols. The broker module normalises internally:
```
EURUSD → EURUSD   (no prefix on PU Prime)
BTCUSD → BTCUSD
XAUUSD → XAUUSD
```

### DEMO_MODE
`settings.DEMO_MODE = False` is hardcoded in Phase 1. In demo mode:
- Trades are logged but NOT sent to MT5
- All risk calculations still run normally

## Crucix Intelligence Server

Crucix is a local macroeconomic intelligence server running at `http://localhost:3117`.
- **No API key required** — it's a localhost HTTP server
- The bot fetches from `/api/world` every loop cycle
- If Crucix is unavailable the bot continues with a `CLEAR` macro context

### Start Crucix
```bash
cd crucix-server   # or wherever it lives
npm start          # listens on :3117
```

### Data It Provides
```json
{
  "meta": { "timestamp": "2026-03-28T..." },
  "markets": { "vix": { "value": 31.05 } },
  "gdelt": { "avgTone": -2.3 },
  "fred": [
    { "series_id": "GS10", "value": 4.52 },
    { "series_id": "GS2",  "value": 4.81 }
  ]
}
```

## Next.js Dashboard

```
cd web/
npm install
npm run dev        # dev server on :3000
npm run build && npm start  # production
```

### Auth
Uses NextAuth with credentials provider. Session validated at Edge via `middleware.ts`.
Set in `.env.local` (inside `web/`):
```env
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://...
```

### API Routes
All under `web/src/app/api/`:
```
/api/status       → bot running state, equity, open trades
/api/trades       → trade history
/api/learning     → strategy confidence table
/api/world        → Crucix macro context (proxied)
/api/analytics    → performance metrics
```

## Deployment Notes

- Bot runs as a Python process; keep MT5 terminal open on the same Windows machine
- Dashboard can run separately (Vercel, local server)
- Database is hosted on Supabase — no local Postgres needed
- Logs written to `logs/backend_YYYY-MM-DD.log` (rotating daily)
- `DEMO_MODE=False` in `settings.py` must be manually changed to go live — it is NOT an env var
