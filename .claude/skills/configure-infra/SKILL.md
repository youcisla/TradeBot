---
name: configure-infra
description: Set up the trading bot infrastructure. Covers free and paid stacks, market data APIs, broker connection options, database, VPS, and alerting. Use when configuring services, API keys, or deployment environment.
argument-hint: "free|paid"
---

# Configure Infrastructure: $ARGUMENTS

Set up the infrastructure for the trading bot.

## Free Stack ($0/month)

Use this for initial development and demo testing:

| Component | Service | Notes |
|---|---|---|
| Runtime | Local PC | Bot runs on your machine |
| Market Data | Alpha Vantage or Twelve Data | Free tier, rate limited |
| Paper Trading | Alpaca API (optional) | For testing without broker |
| Database | PostgreSQL via Supabase | Shared by bot + web dashboard |
| Alerts | Telegram Bot | Free, instant notifications |
| Code Hosting | GitHub | Private repo |
| Broker | PU Prime demo account | Free demo with virtual funds |

### Free API Setup

**Alpha Vantage:**
- Get free key at: `alphavantage.co`
- Limit: 25 requests/day (free tier)
- Add to `.env`: `ALPHA_VANTAGE_KEY=your_key`

**Twelve Data:**
- Get free key at: `twelvedata.com`
- Limit: 800 requests/day, 8 per minute
- Add to `.env`: `TWELVE_DATA_KEY=your_key`

**Telegram Bot (for alerts + remote control):**
- Create bot via BotFather on Telegram
- Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token` and `TELEGRAM_CHAT_ID=your_id`
- Must support **two-way commands** (not just outbound alerts):
  - `/kill` → emergency close all positions + stop loop
  - `/status` → current open positions, equity, daily P&L
  - `/pause` → stop opening new trades, keep managing existing ones
  - `/resume` → resume normal operation
- Uses `python-telegram-bot` package with webhook or polling

**Economic Calendar (for news blackout filter):**
- **Forex Factory scraper** — Free, but fragile (HTML scraping)
- **Finnhub calendar** — Free tier available, JSON API
- **Static weekly JSON** — Manually maintained fallback (download weekly from Forex Factory)
- Add to `.env`: `NEWS_CALENDAR_SOURCE=finnhub` (or `forexfactory` or `static`)
- The bot must block new trades within N minutes of high-impact events on relevant currencies

### Limitations of Free Stack
- Slow data (not real-time)
- Rate limits may delay the loop
- No uptime guarantee (PC must stay on)
- No redundancy

---

## Paid Stack ($50-$300/month)

Upgrade when moving toward live trading:

### Basic Reliable ($50-$100/month)

| Component | Service | Cost |
|---|---|---|
| Runtime | DigitalOcean Droplet | ~$12/month (2GB RAM) |
| Market Data | Twelve Data Pro | ~$30/month |
| Database | SQLite on VPS | $0 (included) |
| Alerts | Telegram Bot | $0 |
| News | Finnhub free tier | $0 |

### Advanced Professional ($200-$300/month)

| Component | Service | Cost |
|---|---|---|
| Runtime | AWS EC2 or DigitalOcean | ~$20-50/month |
| Market Data | Polygon.io | ~$80/month |
| Database | PostgreSQL (managed) | ~$15/month |
| Alerts | Telegram + SMS | ~$10/month |
| News API | Marketaux or Finnhub Pro | ~$50/month |
| Monitoring | Grafana Cloud (free tier) | $0 |

---

## Broker Connection Options

PU Prime automation routes (in order of preference):

### 1. Official API (Best)
- Check if PU Prime offers a REST/WebSocket API
- Most reliable, fastest execution
- Implementation: `broker/connector.py` wraps the API

### 2. MT5 Bridge
- PU Prime supports MetaTrader 5
- Use the `MetaTrader5` Python package
- Installation: `pip install MetaTrader5`
- Implementation: connect Python to MT5 terminal

```python
import MetaTrader5 as mt5

mt5.initialize()
mt5.login(account, password=password, server=server)
```

### 3. Browser Automation (Fallback)
- Selenium or Playwright to control the web platform
- **Last resort** — fragile and slow
- Only if no API or MT5 access

---

## Environment Variables Template (.env.example)

```env
# Broker
BROKER_ACCOUNT=
BROKER_PASSWORD=
BROKER_SERVER=
DEMO_MODE=true

# Market Data
ALPHA_VANTAGE_KEY=
TWELVE_DATA_KEY=

# Economic Calendar (news filter)
NEWS_CALENDAR_SOURCE=finnhub
FINNHUB_API_KEY=
NEWS_BLACKOUT_MINUTES=15

# Telegram (two-way: alerts + remote commands)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Risk
MAX_RISK_PER_TRADE=0.02
MAX_OPEN_TRADES=3
MAX_DAILY_LOSS=0.05
MAX_SPREAD=3.0
DRAWDOWN_COOLDOWN_HOURS=24

# Trade Execution
TP1_CLOSE_PERCENT=0.40
TP2_CLOSE_PERCENT=0.30
TP3_CLOSE_PERCENT=0.30
TRAILING_STOP_DISTANCE_PIPS=20
COMMISSION_PER_LOT=7.0
BREAKEVEN_SPREAD_OFFSET=true

# Bot
LOOP_INTERVAL_SECONDS=60
RECONCILE_EVERY_N_LOOPS=10
LOG_LEVEL=INFO
DAILY_SUMMARY_HOUR=17
```

## Configuration in config/settings.py

Load all values from `.env` using `python-dotenv`:

```python
from dotenv import load_dotenv
import os

load_dotenv()

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
BROKER_ACCOUNT = os.getenv("BROKER_ACCOUNT")
# ... etc
```

## Rules

1. Never hardcode API keys or credentials
2. Always start with the free stack
3. Upgrade to paid only after demo testing passes
4. Keep SQLite for V1 — PostgreSQL is a V2 upgrade
5. VPS is needed only for 24/7 operation
