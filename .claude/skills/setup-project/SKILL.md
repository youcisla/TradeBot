---
name: setup-project
description: Scaffold the trading bot project structure. Creates the folder layout, config system, main loop skeleton, and logging foundation. Use when starting the project or resetting the structure. Phase 1 of development.
disable-model-invocation: true
---

# Setup Trading Bot Project

Scaffold the complete project structure for the Python trading bot.

## Required Directory Structure

```
TradingBot/
├── config/
│   ├── __init__.py
│   ├── settings.py          # All configurable parameters
│   └── symbols.py           # Tradeable symbols config
├── agents/
│   ├── __init__.py
│   ├── market_agent.py      # Fetches live market data
│   ├── analysis_agent.py    # Interprets market conditions
│   ├── strategy_agent.py    # Detects trading setups
│   ├── risk_agent.py        # Validates risk and position size
│   ├── execution_agent.py   # Places trades (SL + 3 TPs)
│   ├── trade_manager.py     # Manages open positions
│   ├── learning_agent.py    # Reviews results, adjusts confidence
│   └── logging_agent.py     # Records everything
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py     # Abstract base class for strategies
│   ├── sma_crossover.py     # SMA crossover strategy (fallback)
│   ├── ict_strategy.py      # ICT/SMC strategy (primary)
│   └── ict/                 # ICT/SMC engine — 10 modules
│       ├── __init__.py
│       ├── engine.py        # Unified orchestrator
│       ├── structure.py     # Swing points, BOS/MSS, dealing ranges
│       ├── liquidity.py     # BSL/SSL mapping, sweep detection
│       ├── displacement.py  # Impulsive candle detection
│       ├── fvg.py           # Fair Value Gap detection
│       ├── orderblock.py    # Order Block detection
│       ├── session.py       # Killzones, macros, PDH/PDL/PWH/PWL
│       ├── bias.py          # HTF bias, regime, premium/discount
│       ├── scoring.py       # 0-100 confidence scoring
│       └── setups.py        # 6 setup model detectors
├── broker/
│   ├── __init__.py
│   └── connector.py         # Broker connection interface
├── models/
│   ├── __init__.py
│   ├── trade.py             # Trade data model
│   ├── signal.py            # Signal data model
│   ├── market_data.py       # Market data model
│   └── ict_models.py        # ICT/SMC data structures (30+ dataclasses)
├── database/
│   ├── __init__.py
│   ├── db.py                # PostgreSQL database handler (psycopg2)
│   └── cleanup_mock_data.sql # SQL to purge mock/demo data
├── filters/
│   ├── __init__.py
│   ├── news_filter.py       # Economic calendar blackout windows
│   └── data_validator.py    # Market data sanity checks
├── state/
│   ├── __init__.py
│   └── persistence.py       # Trade state persistence & reconciliation
├── backtesting/
│   ├── __init__.py
│   └── engine.py            # CSV-based strategy backtester
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Shared utilities
├── logs/                    # Log files directory
├── main.py                  # Entry point with scan-rank-execute loop
├── start.ps1                # Windows launcher script
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## Main Loop Skeleton (main.py)

The entry point must implement the scan-rank-execute pipeline with time-corrected sleep and startup reconciliation:

```python
import time
from config.settings import LOOP_INTERVAL_SECONDS

# STARTUP: reconcile bot state against broker positions
trade_manager.reconcile()

while True:
    loop_start = time.monotonic()
    
    trade_manager.monitor()  # monitor existing trades first

    # PHASE 1: SCAN — collect ALL signals from ALL symbols
    all_signals = []
    for symbol in active_symbols:  # 30 symbols across 5 asset classes
        if not is_market_open(symbol):
            continue
        data = market_agent.get_data(symbol)
        context = analysis_agent.analyze(data)
        signals = strategy_agent.detect_all(context)  # ALL strategies
        all_signals.extend(signals)
    
    # PHASE 2: RANK — sort by confidence, deduplicate per (symbol, direction)
    all_signals.sort(key=lambda s: s.confidence, reverse=True)
    ranked = deduplicate_by_symbol_direction(all_signals)
    
    # PHASE 3: EXECUTE — best signals first, until MAX_OPEN_TRADES reached
    for signal in ranked:
        if risk_agent.validate(signal):  # 7-step gate, includes max trades
            trade = execution_agent.open_trade(signal)

    # Time-corrected sleep to prevent drift
    elapsed = time.monotonic() - loop_start
    sleep_time = max(0, LOOP_INTERVAL_SECONDS - elapsed)
    time.sleep(sleep_time)
```

**Why scan-rank-execute?** The old sequential per-symbol loop would execute a weak signal on EURUSD before discovering a strong signal on GBPUSD. The new approach scans everything first, then picks the best.

## Config System (config/settings.py)

Must include at minimum:
- `DEMO_MODE = True` (always start with demo)
- Broker credentials (loaded from .env)
- Risk parameters (max risk per trade, max open trades, max daily loss)
- Symbol list
- Timeframes
- Logging level
- Sleep interval between loop iterations
- `MAX_SPREAD` threshold (in pips, checked live at signal time)
- News blackout window (minutes before/after high-impact events)
- Breakeven spread offset (pips to add to entry when moving SL to breakeven)

## Logging Foundation

Use Python's `logging` module. The logging agent wraps it and also writes trade events to the database.

## State Persistence (state/persistence.py)

The bot must survive crashes and restarts:
- Every open trade is written to the PostgreSQL `trades` table on create/update
- On startup, `reconcile()` compares the DB table against broker's actual open positions
- Mismatches trigger an alert (Telegram) and are logged — the bot adopts the broker's state as truth
- Periodic reconciliation also runs every N loop iterations (configurable)

## Data Validation (filters/data_validator.py)

- Reject stuck quotes (same price for N consecutive ticks)
- Reject price spikes (move > X% in one tick)
- Reject gapped candle data (missing timestamps)
- Log all rejected data for review

## Rules

- Every agent module must have a class with a clear single responsibility
- Use abstract base classes where appropriate
- All secrets in `.env` (never hardcoded)
- Add `.env` to `.gitignore`
- PostgreSQL via Supabase as the database (7 tables)
- Python 3.10+ required
- Every trade state change must be persisted to DB (not just memory)
- The main loop must use time-corrected sleep, never bare `time.sleep(interval)`
- The signal pipeline must use scan-rank-execute (never sequential per-symbol)
