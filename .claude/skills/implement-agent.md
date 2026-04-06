---
name: implement-agent
description: "How to build or modify any agent in the NeuralFX pipeline — patterns, DB integration, logging, event emission."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Implementing or Modifying an Agent

## Agent Anatomy

Every agent follows this pattern:

```python
class XxxAgent:
    def __init__(self, db: Database, broker=None, ...) -> None:
        self._db = db
        self._broker = broker  # only if needed

    def run(self, context: MarketContext) -> SomeResult:
        try:
            return self._run_inner(context)
        except Exception:
            logger.exception("XxxAgent.run failed")
            return safe_default()

    def _run_inner(self, context: MarketContext) -> SomeResult:
        # actual logic here
        self._emit("info", "message", {"key": "value"})
        return result

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("xxx_agent_key", level, msg, data)
```

## Agent Event Keys
These keys appear in the dashboard AgentFeed. Use the correct key for your agent:
`crucix`, `market`, `analysis`, `strategy`, `neural`, `council`, `risk`, `execution`, `trade_manager`, `learning`, `model_manager`, `logging`, `debate`, `exposure`, `memory`

## Logging Pattern
```python
import logging
logger = logging.getLogger(__name__)

# Python logger (goes to file + ERROR console)
logger.info("Starting %s analysis for %s", self.__class__.__name__, symbol)
logger.warning("Spread too wide: %.1f pips", spread)
logger.error("Failed to fetch candles", exc_info=True)

# DB + dashboard (use self._emit)
self._emit("info", f"Processing {symbol}: found {n} setups")
self._emit("warn", f"Rejected {symbol}: spread {spread:.1f} > limit")
self._emit("error", f"Broker unavailable: {exc}")
```

## Adding a New Agent to the Pipeline

1. **Create** `agents/my_agent.py` following the anatomy above
2. **Import** in `main.py`:
   ```python
   from agents.my_agent import MyAgent
   my_agent = MyAgent(db=db, broker=broker)
   ```
3. **Call** inside `_run_iteration()` in the correct pipeline position
4. **Add DB migration** if new columns/tables needed (see `database/db.py`)
5. **Add to AgentFeed** in dashboard: add key to `PIPELINE_AGENTS` in `web/src/app/dashboard/page.tsx` (or `AgentFeed.tsx`)

## DB Integration Patterns

```python
# Log an event to both tables
self._db.log_event(level="INFO", source="MY_AGENT", message="something happened")
self._db.log_agent_event("my_agent", "info", "something happened", {"extra": "data"})

# Read confidence
conf = self._db.get_confidence("ict_smc:TREND_CONTINUATION_LONG")

# Update confidence
self._db.update_confidence("ict_smc:TREND_CONTINUATION_LONG", wins=1, losses=0)

# Upsert a trade
self._db.upsert_trade(trade)

# Get open trades
trades = self._db.get_open_trades()
```

## Modifying Existing Agents

1. **Read the file first** — never assume you remember it
2. **Check what calls it** — grep for the class name in `main.py`
3. **Check what it returns** — look at how callers use the return value
4. **Don't change the public interface** unless updating all callers
5. **Add new optional parameters** with defaults to avoid breaking callers

## Pipeline Contracts

| Agent | Input | Output |
|---|---|---|
| CrucixAgent | — | MacroContext |
| MarketAgent | symbol, timeframe | MarketContext |
| AnalysisAgent | MarketContext | MarketContext (enriched) |
| StrategyAgent | MarketContext | Signal \| None |
| CouncilAgent | Signal, MarketContext | CouncilVerdict |
| RiskAgent | Signal, CouncilVerdict | approved: bool, lot_size: float |
| ExecutionAgent | Signal, lot_size | Trade |
| TradeManager | open trades, prices | (manages in place) |

## Error Handling Rules
- All public methods must catch exceptions and return safe defaults
- Never let an agent crash the main loop
- Log with `logger.exception()` (includes stack trace)
- Emit to DB with `self._emit("error", ...)` for dashboard visibility
