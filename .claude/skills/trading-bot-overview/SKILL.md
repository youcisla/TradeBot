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
while True:
    market_data = MarketAgent.get_data()
    context = AnalysisAgent.analyze(market_data)
    signal = StrategyAgent.detect(context)
    if signal:
        approved = RiskAgent.validate(signal)
        if approved:
            trade = ExecutionAgent.open_trade(signal)
    TradeManager.monitor()
    Logger.record()
```

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

## Development Phases

1. Core structure (project arch, main loop, logging, config)
2. Broker connection (connect, read balance, test orders)
3. Market data (price feed, candles, spread, volume)
4. First strategy (single symbol, single timeframe)
5. Risk engine (position sizing, SL, TP1/TP2/TP3)
6. Trade management (partial closes, breakeven, stop movement)
7. Learning system (trade review, reward system, confidence scoring)
8. Monitoring (alerts, dashboard, kill switch)
