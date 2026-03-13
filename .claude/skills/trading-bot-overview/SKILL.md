---
name: trading-bot-overview
description: Full architecture and design reference for the Python trading bot project. Use when discussing architecture, understanding the system, or making decisions about any module. Covers agents, loop flow, execution model, learning system, and infrastructure.
user-invocable: false
---

# Trading Bot — Architecture Overview

This project is a **modular Python trading bot** that connects to a **PU Prime trading account** (demo first). It is composed of independent agents that collaborate in a continuous loop.

## System Agents

Each agent answers ONE question only:

| Agent | Question | Responsibility |
|---|---|---|
| Market Agent | What is the market doing? | Reads live market data (price, candles, spread, volume) |
| Analysis Agent | What does it mean? | Interprets market conditions |
| Strategy Agent | Is there a trade? | Detects trading setups |
| Risk Agent | Is it safe? | Validates risk and position sizing |
| Execution Agent | Can we execute it? | Places trades with SL + 3 TPs |
| Trade Manager Agent | What do we do with the trade? | Manages open positions (partial closes, breakeven, stop movement) |
| Learning Agent | What did we learn? | Reviews results, adjusts confidence |
| Logging Agent | (Records everything) | Full event and trade logging |

## Core Loop

```python
import time

# On startup: reconcile bot state against broker positions
TradeManager.reconcile()

while True:
    loop_start = time.monotonic()

    market_data = MarketAgent.get_data()     # includes data sanity checks
    context = AnalysisAgent.analyze(market_data)
    signal = StrategyAgent.detect(context)
    if signal:
        approved = RiskAgent.validate(signal)  # includes duplicate & correlation guard
        if approved:
            trade = ExecutionAgent.open_trade(signal)
    TradeManager.monitor()                     # manages positions + persists state
    Logger.record()

    # Time-corrected sleep: subtract elapsed from interval to avoid drift
    elapsed = time.monotonic() - loop_start
    sleep_time = max(0, LOOP_INTERVAL_SECONDS - elapsed)
    time.sleep(sleep_time)
```

**Critical loop additions vs. original design:**
- **Startup reconciliation** — syncs bot state to real broker positions on every boot
- **Time-corrected sleep** — prevents timing drift when agents are slow (API latency, rate limits)
- **Drawdown circuit breaker** — checked inside `RiskAgent.validate()`, halts all trading if daily loss limit hit

## Safety Systems

| System | Purpose | Where |
|---|---|---|
| State persistence | Survive crashes without losing trade tracking | Trade Manager writes every state change to DB |
| Position reconciliation | Detect drift between bot and broker | Trade Manager on startup + periodic |
| Duplicate signal guard | Prevent opening the same trade twice | Risk Agent checks before every execution |
| News blackout filter | Avoid high-impact event windows | Risk Agent queries economic calendar |
| Spread spike detection | Reject signals during abnormal spreads | Risk Agent checks live spread at signal time |
| Drawdown circuit breaker | Hard-stop all trading if daily loss limit hit | Risk Agent monitors account equity |
| Data feed validation | Reject stale or corrupt market data | Market Agent runs sanity checks |
| Remote kill switch | Emergency close from Telegram `/kill` | Trade Manager + Telegram two-way bot |

## Trade Execution Model

Every trade has: **1 Stop Loss + 3 Take Profits**

Lifecycle:
1. Trade opens → SL + TP1 + TP2 + TP3 attached
2. TP1 hit → partial close
3. TP2 hit → partial close
4. TP3 hit → final close
5. OR Stop Loss hit → full close

## Learning System

After each trade, a reward/penalty score is assigned:

| Outcome | Score |
|---|---|
| Good trade (clean setup) | +3 |
| Profit but messy setup | +1 |
| Small loss | -2 |
| Bad loss | -5 |
| Rule violation | -10 |

Confidence adjustments:
- High score → allow strategy more
- Low score → reduce usage
- Very low score → disable strategy

Tracked dimensions: market conditions, sessions, symbols, spread conditions, setup quality, risk behavior.

## Broker Execution Path

```
PU PRIME
├── Official API (best case)
├── MT5 bridge
└── Browser automation (fallback)
```

## Minimum Viable Version (V1)

- 1 symbol
- 1 strategy
- Fixed risk
- 1 stop loss + 3 take profits
- Demo account only
- Full logging
- State persistence (survive crashes)
- Position reconciliation on startup
- Duplicate signal guard
- Spread check at signal time
- Drawdown circuit breaker
- Data feed sanity checks

## Development Phases

1. Core structure (project arch, main loop, logging, config, state persistence)
2. Broker connection (connect, read balance, test orders, reconciliation)
3. Market data (price feed, candles, spread, volume, data validation)
4. First strategy (single symbol, single timeframe, duplicate guard)
5. Risk engine (position sizing, SL, TP1/TP2/TP3, spread check, drawdown breaker)
6. Trade management (partial closes via MT5, breakeven with spread offset, trailing stops)
7. Learning system (trade review, objective scoring rules, confidence scoring)
8. Monitoring (alerts, Telegram two-way commands, daily summary, kill switch)
9. News filter (economic calendar integration, blackout windows)
10. Backtesting (CSV-based strategy validation before demo)
