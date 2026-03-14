---
name: trading-bot-overview
description: Full architecture and design reference for the Python trading bot project. Use when discussing architecture, understanding the system, or making decisions about any module. Covers agents, loop flow, execution model, learning system, infrastructure, ICT/SMC engine, and scan-rank-execute pipeline.
user-invocable: false
---

# Trading Bot — Architecture Overview

This project is a **modular Python trading bot** that connects to a **PU Prime trading account** via MetaTrader 5. It is composed of independent agents that collaborate in a continuous loop. Features an **ICT/SMC strategy engine** (10 analysis modules), a **scan-all → rank → execute-best** pipeline across **30 symbols** in 5 asset classes, and a **Next.js web dashboard** deployed on Vercel.

## System Agents

Each agent answers ONE question only:

| Agent | Question | Responsibility |
|---|---|---|
| Market Agent | What is the market doing? | Reads live market data (250 H1 candles, spread, volume) |
| Analysis Agent | What does it mean? | SMA, RSI, ATR, regime detection, session detection |
| Strategy Agent | Is there a trade? | Runs ALL strategies, collects ALL signals via `detect_all()` |
| Risk Agent | Is it safe? | 7-step risk validation gate |
| Execution Agent | Can we execute it? | Places trades with SL + 3 TPs |
| Trade Manager Agent | What do we do with the trade? | Manages open positions (partial closes, breakeven, trailing) |
| Learning Agent | What did we learn? | Reviews results, adjusts confidence |
| Logging Agent | (Records everything) | DB + CSV + Telegram logging |

## Strategies

### ICT/SMC Strategy (Primary)
Full Inner Circle Trader engine in `strategies/ict/` with 10 modules:
- **structure.py** — Swing points, BOS/MSS, dealing ranges
- **liquidity.py** — BSL/SSL mapping, sweep detection
- **displacement.py** — Impulsive candle detection
- **fvg.py** — Fair Value Gap detection + fill tracking
- **orderblock.py** — Order Block detection + validation
- **session.py** — Killzones, macros, PDH/PDL/PWH/PWL
- **bias.py** — HTF bias, regime, premium/discount
- **scoring.py** — 0–100 weighted confidence (10 components)
- **setups.py** — 6 setup models (OB Retracement, FVG Fill, Liquidity Sweep, BOS Continuation, MSS Reversal, Macro Scalp)
- **engine.py** — Unified orchestrator

Wrapped by `strategies/ict_strategy.py` (inherits `BaseStrategy`). Uses 200 H4 candles for HTF analysis. Minimum confidence: 55/100.

### SMA Crossover (Fallback)
Simple moving average crossover with ATR-based stops in `strategies/sma_crossover.py`.

## Core Loop — Scan-Rank-Execute Pipeline

The bot no longer processes symbols sequentially. Instead, it uses a **scan-all → rank → execute-best** approach:

```python
import time

TradeManager.reconcile()  # Startup reconciliation

while True:
    loop_start = time.monotonic()
    
    TradeManager.monitor()  # Monitor existing trades first
    
    # PHASE 1: SCAN — collect ALL signals from ALL symbols
    all_signals = []
    for symbol in active_symbols:  # 30 symbols across 5 asset classes
        if not is_market_open(symbol):  # crypto 24/7, forex skip weekends
            continue
        data = MarketAgent.get_data(symbol)
        context = AnalysisAgent.analyze(data)
        signals = StrategyAgent.detect_all(context)  # ALL strategies, ALL signals
        all_signals.extend(signals)
    
    # PHASE 2: RANK — sort by confidence, deduplicate per (symbol, direction)
    all_signals.sort(key=lambda s: s.confidence, reverse=True)
    ranked = deduplicate_by_symbol_direction(all_signals)
    
    # PHASE 3: EXECUTE — best signals first, until MAX_OPEN_TRADES reached
    for signal in ranked:
        if RiskAgent.validate(signal):  # includes max trades check
            trade = ExecutionAgent.open_trade(signal)
    
    # Time-corrected sleep
    elapsed = time.monotonic() - loop_start
    time.sleep(max(0, LOOP_INTERVAL_SECONDS - elapsed))
```

**Key pipeline features:**
- **No first-come-first-served** — a 95-confidence GBPUSD beats a 56-confidence EURUSD regardless of list order
- **Startup reconciliation** — syncs bot state to real broker positions on every boot
- **Time-corrected sleep** — prevents timing drift when agents are slow
- **Market hours awareness** — crypto 24/7, forex/commodities skip Fri 22:00–Sun 22:00 UTC
- **Drawdown circuit breaker** — checked inside `RiskAgent.validate()`

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

## Symbols

30 symbols across 5 asset classes (configured in `config/symbols.py`):
- **Forex Majors** (6): EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
- **Forex Crosses** (12): EURGBP, EURJPY, GBPJPY, AUDJPY, NZDUSD, EURAUD, GBPAUD, EURCHF, GBPCHF, AUDNZD, CADJPY, CHFJPY
- **Commodities** (4): XAUUSD, XAGUSD, USOIL, UKOIL
- **Crypto** (5): BTCUSD, ETHUSD, LTCUSD, XRPUSD, SOLUSD
- **Exotics** (2): USDZAR, USDMXN

## Infrastructure

- **Database**: PostgreSQL via Supabase (7 tables: trades, trade_scores, strategy_confidence, agent_events, bot_commands, bot_status, ict_setups)
- **Broker**: MetaTrader 5 (PU Prime), with MockConnector for testing
- **Dashboard**: Next.js on Vercel (terminal/hacker aesthetic)
- **Alerts**: Telegram bot (two-way: `/kill`, `/status`, `/pause`, `/resume`)
- **Launcher**: `start.ps1` (Windows) or `python main.py`

## Current State

All agents implemented and tested. ICT/SMC engine complete (10 modules). Multi-strategy scan-rank-execute pipeline active. Web dashboard with 6 pages (dashboard, trades, analytics, ICT, strategy, learning). 30 symbols configured. Market hours auto-detection. Backtesting engine ready.

## Development Phases

1. ~~Core structure (project arch, main loop, logging, config, state persistence)~~ ✅
2. ~~Broker connection (connect, read balance, test orders, reconciliation)~~ ✅
3. ~~Market data (price feed, candles, spread, volume, data validation)~~ ✅
4. ~~First strategy (SMA crossover, multi-symbol, duplicate guard)~~ ✅
5. ~~Risk engine (position sizing, SL, TP1/TP2/TP3, spread check, drawdown breaker)~~ ✅
6. ~~Trade management (partial closes via MT5, breakeven with spread offset, trailing stops)~~ ✅
7. ~~Learning system (trade review, objective scoring rules, confidence scoring)~~ ✅
8. ~~Monitoring (alerts, Telegram two-way commands, daily summary, kill switch)~~ ✅
9. ~~News filter (economic calendar integration, blackout windows)~~ ✅
10. ~~Backtesting (CSV-based strategy validation before demo)~~ ✅
11. ~~ICT/SMC strategy engine (10 analysis modules, 6 setup models)~~ ✅
12. ~~Multi-asset expansion (30 symbols, 5 asset classes, market hours)~~ ✅
13. ~~Scan-rank-execute pipeline (no missed opportunities)~~ ✅
14. ~~Web dashboard (Next.js, Vercel, analytics, ICT page, strategy page)~~ ✅
