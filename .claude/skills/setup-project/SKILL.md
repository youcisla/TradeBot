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
│   └── base_strategy.py     # Abstract base class for strategies
├── broker/
│   ├── __init__.py
│   └── connector.py         # Broker connection interface
├── models/
│   ├── __init__.py
│   ├── trade.py             # Trade data model
│   ├── signal.py            # Signal data model
│   └── market_data.py       # Market data model
├── database/
│   ├── __init__.py
│   └── db.py                # SQLite database handler
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Shared utilities
├── logs/                    # Log files directory
├── main.py                  # Entry point with main loop
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## Main Loop Skeleton (main.py)

The entry point must implement the continuous bot loop:

```python
while True:
    market_data = market_agent.get_data()
    context = analysis_agent.analyze(market_data)
    signal = strategy_agent.detect(context)
    if signal:
        approved = risk_agent.validate(signal)
        if approved:
            trade = execution_agent.open_trade(signal)
    trade_manager.monitor()
    logging_agent.record()
```

## Config System (config/settings.py)

Must include at minimum:
- `DEMO_MODE = True` (always start with demo)
- Broker credentials (loaded from .env)
- Risk parameters (max risk per trade, max open trades)
- Symbol list
- Timeframes
- Logging level
- Sleep interval between loop iterations

## Logging Foundation

Use Python's `logging` module. The logging agent wraps it and also writes trade events to the database.

## Rules

- Every agent module must have a class with a clear single responsibility
- Use abstract base classes where appropriate
- All secrets in `.env` (never hardcoded)
- Add `.env` to `.gitignore`
- SQLite as the database (no external DB required for V1)
- Python 3.10+ required
