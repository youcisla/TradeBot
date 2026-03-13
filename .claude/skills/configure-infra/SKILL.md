---
name: configure-infra
description: Set up the trading bot infrastructure. Covers free and paid stacks, market data APIs, broker connection options, database, VPS, and alerting. Use when configuring services, API keys, or deployment environment.
argument-hint: [free|paid]
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
| Database | SQLite | Local file, no server needed |
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

**Telegram Bot (for alerts):**
- Create bot via BotFather on Telegram
- Add to `.env`: `TELEGRAM_BOT_TOKEN=your_token` and `TELEGRAM_CHAT_ID=your_id`

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

# Telegram Alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Risk
MAX_RISK_PER_TRADE=0.02
MAX_OPEN_TRADES=3
MAX_DAILY_LOSS=0.05

# Bot
LOOP_INTERVAL_SECONDS=60
LOG_LEVEL=INFO
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
