# TradeBot Redesign Blueprint — Execution Playbook for Minimax 2.7

**Generated:** April 2026
**Scope:** Full-system audit, redesign, and step-by-step implementation guide
**Target:** Production-grade algorithmic trading system (ICT/SMC on MT5)

---

## 1. Executive Summary

### What Exists

A Python-based trading bot (~165 .py files, ~15k LOC core) that:

- Connects to MetaTrader 5 via the `MetaTrader5` Python package (Windows-only IPC)
- Runs an ICT/Smart Money Concepts strategy engine (12 modules: structure, liquidity, FVG, order blocks, displacement, sessions, bias, scoring, setups, fibonacci)
- Uses a multi-agent architecture: MarketAgent → AnalysisAgent → StrategyAgent → RiskAgent → ExecutionAgent → TradeManager → LearningAgent
- Stores state in Vercel Postgres (psycopg2 pool)
- Serves a Next.js dashboard (web/) with real-time WebSocket + REST polling
- Supports Telegram control (kill, pause, resume, status, graph)
- Has ML layers: LightGBM ensemble, GARCH regime detection, Kalman filtering
- Includes backtesting engine with walk-forward optimization
- Has a guard pipeline (11 guards), sniper entry gate (Fibonacci pullback), deferred entries

### Critical Problems

| # | Problem | Severity | Impact |
|---|---------|----------|--------|
| 1 | **`main.py` is 1,863 lines** — the entire orchestration loop, command processor, heartbeat, and iteration logic are in one file | HIGH | Untestable, unmaintainable, impossible to modify safely |
| 2 | **MT5 is single-threaded IPC** — the bot already forces serial scanning, but the architecture pretends concurrency exists | MEDIUM | Wasted complexity, random IPC failures cause cascading symbol disabling |
| 3 | **No process supervision** — if the bot crashes, nothing restarts it; PowerShell `start.ps1` is a manual launcher | HIGH | Unattended downtime = missed trades + unmanaged positions |
| 4 | **Database module is 2,181 lines** — `db.py` is a single god-class handling 60+ SQL operations with inline DDL | HIGH | Schema changes are dangerous, connection pool exhaustion is undetected |
| 5 | **Config is 855 lines of flat globals** — `settings.py` reads ~120 env vars with no validation, no grouping, no profiles that actually work | MEDIUM | Misconfiguration goes undetected until runtime crash |
| 6 | **Risk agent has hardcoded correlation table** — 40+ pairs manually mapped, no dynamic correlation | MEDIUM | False sense of safety; missing pairs = undetected exposure |
| 7 | **No position reconciliation on crash recovery** — `trade_manager.reconcile()` only syncs DB ↔ MT5 at startup, not mid-run | HIGH | Orphaned broker positions after crash |
| 8 | **LLM dependencies are dead code** — DeepSeek strategy, Council agent, OpenRouter gateway exist but are disabled; they add attack surface and confusion | LOW | Code archaeology wastes time |
| 9 | **No automated testing of the trading pipeline** — 40 test files exist but none test the actual `_run_iteration` flow end-to-end | MEDIUM | Regressions go unnoticed |
| 10 | **Secrets in .env with no rotation** — broker password, DB URL, API keys all plain text, no vault integration | MEDIUM | Single compromise = full account access |

### Priorities (Ordered)

1. **Extract `main.py` into an orchestrator module** — this unblocks everything else
2. **Add process supervision** (systemd or PM2 equivalent)
3. **Split `db.py` into repository pattern** — one class per domain
4. **Validate config at startup** with Pydantic
5. **Remove all disabled code** (DeepSeek, Council, SMA)
6. **Add end-to-end pipeline tests** with MockBroker
7. **Implement crash-safe reconciliation loop**

---

## 2. Target Architecture

### 2.1 Backend Module Map

```
tradebot/
├── main.py                    # 30 lines max: parse args, call orchestrator.run()
├── orchestrator/
│   ├── __init__.py
│   ├── bot.py                 # TradingBot class: startup, shutdown, main loop
│   ├── iteration.py           # _run_iteration extracted, takes typed deps
│   ├── commands.py            # Command queue processor (extracted from main.py)
│   ├── heartbeat.py           # _update_heartbeat extracted
│   └── supervisor.py          # Watchdog: restarts on crash, health checks
├── broker/
│   ├── __init__.py
│   ├── connector.py           # ABC (unchanged)
│   ├── mt5_connector.py       # MT5 impl (unchanged but add reconnect backoff)
│   └── mock_connector.py      # For testing
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py       # ABC (unchanged)
│   ├── unified_strategy.py    # Fusion layer (unchanged)
│   ├── plugin_loader.py       # Dynamic loader (unchanged)
│   └── ict/                   # 12-module ICT engine (unchanged — it works)
│       ├── engine.py
│       ├── structure.py
│       ├── liquidity.py
│       ├── fvg.py
│       ├── orderblock.py
│       ├── displacement.py
│       ├── session.py
│       ├── bias.py
│       ├── scoring.py
│       ├── setups.py
│       └── fibonacci.py
├── agents/
│   ├── market_agent.py        # Fetches candles (unchanged)
│   ├── analysis_agent.py      # Runs analysis (unchanged)
│   ├── strategy_agent.py      # Runs strategies (unchanged)
│   ├── risk_agent.py          # Risk validation (refactor correlation)
│   ├── execution_agent.py     # Places orders (unchanged)
│   ├── trade_manager.py       # Monitors open trades (add continuous reconciliation)
│   ├── learning_agent.py      # Post-trade learning (unchanged)
│   ├── guards.py              # 11-guard pipeline (unchanged — it works)
│   ├── sniper_entry_guard.py  # Fib pullback gate (unchanged)
│   └── logging_agent.py       # Logging (unchanged)
├── database/
│   ├── __init__.py
│   ├── pool.py                # Connection pool management + health checks
│   ├── schema.py              # All DDL in one place, migration support
│   ├── trade_repo.py          # CRUD for trades table
│   ├── event_repo.py          # Agent events, bot_commands
│   ├── status_repo.py         # bot_status heartbeat
│   ├── learning_repo.py       # trade_scores, strategy_confidence
│   └── broker_repo.py         # broker_accounts
├── config/
│   ├── __init__.py
│   ├── settings.py            # Pydantic BaseSettings with validation
│   ├── symbols.py             # Symbol metadata (unchanged)
│   └── profiles.py            # dev/paper/live-safe/live-full presets
├── models/                    # Data classes (unchanged — they're clean)
│   ├── market_data.py
│   ├── signal.py
│   ├── trade.py
│   └── ict_models.py
├── utils/                     # Keep existing utils, they work
│   ├── telegram_bot.py
│   ├── spread_monitor.py
│   ├── dynamic_position_sizer.py
│   ├── correlation_gate.py
│   ├── adaptive_stop.py
│   └── ...
├── features/                  # ML features (unchanged)
├── filters/                   # Crucix, data validator (unchanged)
├── backtesting/               # Backtest engine (unchanged)
├── web/                       # Next.js dashboard (unchanged)
└── tests/
    ├── conftest.py
    ├── test_iteration_e2e.py  # NEW: full pipeline with MockBroker
    ├── test_risk_agent.py
    └── ...
```

### 2.2 Key Design Decision: What NOT to Change

The ICT engine (2,588 lines across 12 files) is well-structured and modular. **Do not refactor it.** Same for the guard pipeline (682 lines, 11 guards), the agent ABCs, and the existing model data classes. These work. Focus refactoring energy on the orchestration layer and database.

### 2.3 Data Flow

```
[MT5 Terminal] ←→ [MT5Connector (IPC, single-thread)]
                        │
                        ▼
              ┌─────────────────┐
              │   TradingBot    │  (orchestrator/bot.py)
              │                 │
              │  ┌───────────┐  │
              │  │ Iteration │  │  scan → rank → execute
              │  └───────────┘  │
              │       │         │
              │  Agents:        │
              │  Market → Analysis → Strategy → Risk → Execution
              │       │                                    │
              │  TradeManager ←────────────────────────────┘
              │       │
              │  LearningAgent (post-close)
              └───────┬─────────┘
                      │
              ┌───────▼─────────┐
              │  PostgreSQL DB   │  (Vercel Postgres)
              │  ┌─────────┐    │
              │  │ Repos   │    │  trade_repo, event_repo, etc.
              │  └─────────┘    │
              └───────┬─────────┘
                      │
              ┌───────▼─────────┐
              │  Next.js Dash   │  (web/)
              │  + WebSocket    │
              └─────────────────┘
                      │
              ┌───────▼─────────┐
              │  Telegram Bot   │  (utils/telegram_bot.py)
              └─────────────────┘
```

### 2.4 Deployment Strategy

The bot runs on **Windows** (MT5 requirement). Use this deployment stack:

1. **NSSM (Non-Sucking Service Manager)** to run `python main.py` as a Windows service with auto-restart
2. **Vercel** for the Next.js dashboard (already configured, keep it)
3. **Vercel Postgres** for the database (already configured, keep it)
4. **Telegram** for alerts and remote control (already configured, keep it)

Install command:
```powershell
nssm install TradeBot "C:\Python311\python.exe" "C:\TradeBot\main.py"
nssm set TradeBot AppDirectory "C:\TradeBot"
nssm set TradeBot AppStdout "C:\TradeBot\logs\service.log"
nssm set TradeBot AppStderr "C:\TradeBot\logs\service-error.log"
nssm set TradeBot AppRestartDelay 10000
nssm start TradeBot
```

---

## 3. Trading System Design

### 3.1 Strategy Logic (Current — Preserve)

The ICT engine is the sole signal source. It follows this pipeline:

1. **HTF Bias** (H4/D1): Determine bullish/bearish via structure breaks (BOS/MSS), dealing range position, premium/discount zone
2. **Structure Analysis** (M15): Swing points → BOS/MSS detection → dealing range construction
3. **Liquidity Mapping**: Identify buy-side/sell-side liquidity pools, detect sweeps
4. **Displacement Detection**: Identify impulsive moves with high volume
5. **FVG/OB Detection**: Fair value gaps and order blocks as entry zones
6. **Setup Detection**: 6 setup models (OTE, Breaker, FVG retest, Sweep reversal, Displacement continuation, Turtle Soup)
7. **Scoring**: Multi-factor confidence scoring (structure alignment, HTF confluence, session, displacement, volume)
8. **Signal Output**: Direction + confidence + SL/TP levels

**Do not modify the ICT engine logic.** It is the core IP of this system.

### 3.2 Entry Flow (Current — Preserve with One Fix)

```
Signal generated (confidence 0.0-1.0)
    │
    ├─ conf >= SNIPER_CONF_THRESHOLD (0.45) → Instant execute
    │       │
    │       └─ RiskAgent.validate(mode="hard") → ExecutionAgent.open_trade()
    │               │
    │               └─ Post-entry: RiskAgent.validate(mode="full")
    │                       └─ If fail + FAST_LANE_CLOSE_ON_FULL_REJECT → close immediately
    │
    └─ conf < SNIPER_CONF_THRESHOLD → SniperEntryGuard watchlist
            │
            ├─ Price enters Fibonacci retracement zone → SNIPER_CONFIRMED → execute
            ├─ Timeout → EXPIRED → skip
            └─ Price past zone → SKIPPED → skip
```

### 3.3 Exit Logic (Current — Preserve)

Managed by `TradeManagerAgent.monitor()`:

- **3-TP ladder**: TP1 (partial close), TP2 (partial close), TP3 (full close) — lot splits defined per trade
- **Trailing stop**: After TP1 hit, SL moves to breakeven; after TP2, trails
- **Time-based exit**: Configurable max hold duration
- **Equity drawdown guard**: Emergency close if equity drops below peak × threshold

### 3.4 Risk Management (Current — One Required Fix)

**What works:**
- Drawdown circuit breaker (daily loss %, equity drawdown %)
- Max open trades cap
- Spread check per asset class
- Position sizing via `calculate_position_size` (risk-per-trade % of equity)
- Correlation guard (blocks overlapping directional exposure)
- 11-guard pipeline (MaxPositionSize, SymbolWhitelist, Cooldown, DailyDrawdown, EquityDrawdown, MarketHours, Volatility, FeedFreshness, Volume, ScalpExposure)

**Required fix — Dynamic Correlation:**

The hardcoded `_CORRELATED_PAIRS` dict in `risk_agent.py` (lines 38-95) is brittle. Replace it:

```python
# In utils/correlation_gate.py (already exists but unused in risk_agent)
# Wire it into RiskAgent.__init__:
from utils.correlation_gate import CorrelationGate

class RiskAgent:
    def __init__(self, broker, get_open_trades, crucix_agent, db=None):
        ...
        self._corr_gate = CorrelationGate(
            lookback_bars=100,
            threshold=0.75,  # block if |correlation| > 0.75
        )
```

Keep the hardcoded table as a **fallback** when CorrelationGate has insufficient data (< 50 bars). This is a 30-minute change.

### 3.5 Position Sizing

Current implementation in `RiskAgent.calculate_position_size()`:

```
risk_amount = equity × risk_per_trade_pct
sl_distance = |entry - stop_loss| in price
lot_size = risk_amount / (sl_distance × pip_value × contract_size)
lot_size = clamp(lot_size, min_lot, max_lot)
lot_size = round_to_lot_step(lot_size)
```

This is correct. **No changes needed.** The `FIXED_LOT_SIZE` override exists for testing.

### 3.6 Market Conditions Handling

| Condition | Detection | Response |
|-----------|-----------|----------|
| **Trending** | BOS chain in same direction (ICT structure) | Trade with trend; higher confidence |
| **Ranging** | No BOS/MSS, dealing range intact | Lower confidence; tighter TPs |
| **High Volatility** | GARCH σ > threshold, spread condition "high" | Reduce position size 50%, widen SL |
| **Weekend** | `is_weekend()` → crypto only (BTCUSD) | Switch to weekend_unified_strategy (3 ICT TFs) |
| **News Blackout** | `NEWS_BLACKOUT_MINUTES` before high-impact events | Guard blocks entry |
| **Session** | London/NY/Overlap/Asian detection | London+NY: shorter cooldown (more scans); Asian: longer cooldown |

### 3.7 Failure Scenarios and Protections

| Failure | Current Protection | Adequate? |
|---------|-------------------|-----------|
| MT5 IPC loss | Auto-reconnect + per-symbol disable after N failures | ✅ Yes |
| Broker disconnection | `broker.connect()` retry in main loop | ⚠️ Needs exponential backoff |
| DB connection loss | psycopg2 pool retry | ⚠️ No circuit breaker — add one |
| Bot crash | Nothing | ❌ Add NSSM service (Section 2.4) |
| Orphaned positions | Startup reconciliation only | ⚠️ Add continuous reconciliation every 5 min |
| Runaway losses | Daily drawdown guard + equity drawdown guard | ✅ Yes |
| Kill switch | Telegram `/kill` + Dashboard "kill" command | ✅ Yes |

---

## 4. Implementation Plan for Minimax 2.7

### Phase 1: Extract Orchestrator (Priority: CRITICAL, ~4 hours)

**Step 1.1:** Create `orchestrator/` directory with `__init__.py`.

**Step 1.2:** Extract `_run_iteration` from `main.py` → `orchestrator/iteration.py`.
- Keep the exact same function signature
- Move the function body verbatim
- Add `from orchestrator.iteration import run_iteration` in bot.py
- The function already takes all dependencies as keyword arguments, so this is a clean cut

**Step 1.3:** Extract `_process_commands` → `orchestrator/commands.py`.
- Same approach: move verbatim, update imports

**Step 1.4:** Extract `_update_heartbeat` → `orchestrator/heartbeat.py`.
- Move the function + the global `_hb_equity` / `_hb_balance` state into a `HeartbeatManager` class

**Step 1.5:** Create `orchestrator/bot.py` with a `TradingBot` class:
```python
class TradingBot:
    def __init__(self):
        self.db = None
        self.broker = None
        self.shutdown_requested = False
        # ... all the agent instances

    def startup(self) -> None:
        """Everything currently in main() before the while loop."""
        ...

    def run(self) -> None:
        """The while loop."""
        self.startup()
        while not self.shutdown_requested:
            self._tick()
        self.shutdown()

    def _tick(self) -> None:
        """One iteration of the main loop."""
        run_iteration(...)  # from orchestrator/iteration.py

    def shutdown(self) -> None:
        """Everything currently after the while loop."""
        ...
```

**Step 1.6:** Reduce `main.py` to:
```python
from orchestrator.bot import TradingBot

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
```

**Verification:** Run the bot. The behavior must be identical. No logic changes — pure extraction.

### Phase 2: Split Database (Priority: HIGH, ~3 hours)

**Step 2.1:** Create `database/pool.py`:
```python
import psycopg2.pool
from config import settings

_pool = None

def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2, maxconn=10,
            dsn=settings.DATABASE_URL,
        )
    return _pool

def get_conn():
    return get_pool().getconn()

def put_conn(conn):
    get_pool().putconn(conn)
```

**Step 2.2:** Create `database/trade_repo.py` — extract all trade-related methods from `db.py`:
- `save_trade()`, `update_trade()`, `get_trade()`, `get_open_trades()`, `get_closed_trades()`, `close_trade()`

**Step 2.3:** Create `database/event_repo.py` — extract:
- `log_agent_event()`, `get_pending_commands()`, `claim_pending_commands()`, `update_command()`

**Step 2.4:** Create `database/status_repo.py` — extract:
- `update_bot_status()`, `set_bot_uptime_start()`, `set_bot_stopped()`, `start_session()`, `end_session()`

**Step 2.5:** Create `database/learning_repo.py` — extract:
- `save_trade_score()`, `get_strategy_confidence()`, `update_strategy_confidence()`, snapshot methods

**Step 2.6:** Create `database/broker_repo.py` — extract:
- `get_active_broker_account()`, `mark_broker_connected()`, `save_symbol_fault()`, `load_symbol_faults()`

**Step 2.7:** Create `database/schema.py` — move all `_CREATE_*` DDL strings and the `_ensure_tables()` method.

**Step 2.8:** Create a facade `Database` class that delegates to repos:
```python
class Database:
    def __init__(self):
        self.trades = TradeRepo()
        self.events = EventRepo()
        self.status = StatusRepo()
        self.learning = LearningRepo()
        self.broker = BrokerRepo()
        ensure_schema()

    # Keep backward-compatible methods that delegate:
    def save_trade(self, trade):
        return self.trades.save(trade)
    ...
```

This way, **existing code doesn't break** — all existing `db.save_trade()` calls still work. But new code uses `db.trades.save()`.

**Verification:** Run all existing tests. Run the bot for 10 minutes.

### Phase 3: Config Validation (Priority: MEDIUM, ~2 hours)

**Step 3.1:** Install pydantic: `pip install pydantic pydantic-settings`

**Step 3.2:** Rewrite `config/settings.py`:
```python
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class BrokerSettings(BaseSettings):
    account: str = Field("", alias="BROKER_ACCOUNT")
    password: str = Field("", alias="BROKER_PASSWORD")
    server: str = Field("", alias="BROKER_SERVER")

class RiskSettings(BaseSettings):
    max_risk_per_trade: float = Field(0.02, alias="MAX_RISK_PER_TRADE")
    max_open_trades: int = Field(5, alias="MAX_OPEN_TRADES")
    max_daily_loss_pct: float = Field(0.05, alias="GUARD_MAX_DAILY_LOSS_PCT")

    @field_validator("max_risk_per_trade")
    @classmethod
    def risk_bounds(cls, v):
        if not 0.001 <= v <= 0.10:
            raise ValueError(f"max_risk_per_trade={v} is outside safe range [0.1%, 10%]")
        return v

class TradingSettings(BaseSettings):
    loop_interval_seconds: int = Field(30, alias="LOOP_INTERVAL_SECONDS")
    scan_cooldown_seconds_london_ny: float = Field(60, alias="SCAN_COOLDOWN_SECONDS_LONDON_NY")
    # ... all other settings grouped logically

class Settings(BaseSettings):
    broker: BrokerSettings = BrokerSettings()
    risk: RiskSettings = RiskSettings()
    trading: TradingSettings = TradingSettings()
    # ...

    model_config = {"env_file": ".env", "env_nested_delimiter": "__"}

settings = Settings()
```

**Step 3.3:** For backward compatibility, re-export flat names:
```python
# At module level in config/__init__.py
BROKER_ACCOUNT = settings.broker.account
MAX_RISK_PER_TRADE = settings.risk.max_risk_per_trade
# ... etc
```

This allows gradual migration — existing code keeps working, new code uses `settings.risk.max_risk_per_trade`.

**Verification:** Bot starts without errors. Invalid config (e.g., `MAX_RISK_PER_TRADE=0.5`) is caught at startup.

### Phase 4: Dead Code Removal (Priority: MEDIUM, ~1 hour)

Delete these files entirely:
- `agents/deepseek_strategy.py` (42K, completely disabled)
- `agents/council_agent.py` (33K, completely disabled)
- `agents/debate_agent.py` (12K, only used by council)
- `agents/exposure_coach.py` (5.5K, unused)
- `agents/memory_agent.py` (8K, unused — memories are JSON files)
- `strategies/sma_crossover.py` (4.5K, disabled)
- `strategies/scalp_m5.py` (16K, disabled)
- `llm/openrouter_gateway.py` (4.5K, unused since council disabled)
- `models/agent_mesh.py` (1K, unused)

Remove all references to these in `main.py` (the commented-out imports and instantiations).

**Total removed:** ~125K of dead code.

**Verification:** `grep -r "deepseek_strategy\|council_agent\|debate_agent\|sma_crossover\|scalp_m5\|openrouter_gateway" --include="*.py" .` returns only test files (which should also be pruned).

### Phase 5: End-to-End Pipeline Test (Priority: MEDIUM, ~3 hours)

**Step 5.1:** Create `tests/test_iteration_e2e.py`:
```python
"""End-to-end test: scan → rank → execute using MockBroker."""
import pytest
from broker.mock_connector import MockBrokerConnector
from orchestrator.iteration import run_iteration
from database.db import Database  # or use a test DB
from agents.market_agent import MarketAgent
from agents.analysis_agent import AnalysisAgent
# ... import all agents

@pytest.fixture
def trading_env():
    """Set up a complete trading environment with mock broker."""
    broker = MockBrokerConnector()
    broker.set_candles("EURUSD", generate_trending_candles(direction="up", count=300))
    broker.set_equity(10000.0)
    broker.set_balance(10000.0)
    # ... instantiate all agents with mock broker
    return {
        "broker": broker,
        "market_agent": MarketAgent(broker),
        # ... all other agents
    }

def test_bullish_signal_opens_trade(trading_env):
    """Given bullish candles on EURUSD, a BUY trade should be opened."""
    metrics = {"loops": 0, "scanned_symbols": 0, ...}
    run_iteration(
        loop_count=1,
        db=trading_env["db"],
        broker=trading_env["broker"],
        # ... all params
        metrics=metrics,
    )
    assert metrics["raw_signals"] >= 1
    assert len(trading_env["trade_manager"].get_open_trades()) >= 1

def test_risk_agent_blocks_when_max_trades():
    """When max_open_trades is reached, new signals are rejected."""
    ...

def test_drawdown_guard_kills_trading():
    """When daily loss exceeds threshold, all signals are blocked."""
    ...
```

**Step 5.2:** Create `tests/helpers.py` with candle generation utilities:
```python
def generate_trending_candles(direction="up", count=300, start_price=1.1000):
    """Generate synthetic candles with clear ICT structure (BOS, FVG, OB)."""
    ...
```

This is the hardest test to write because ICT needs specific candle patterns. Start with the simpler tests (risk rejection, guard blocking) and build up.

### Phase 6: Continuous Reconciliation (Priority: HIGH, ~1 hour)

In `orchestrator/bot.py`, inside the main loop, add:

```python
# Every 5 minutes (30 loops at 10s interval):
if loop_count % self.RECONCILE_INTERVAL == 0:
    mt5_positions = self.broker.get_open_positions()
    db_trades = self.trade_manager.get_open_trades()

    mt5_tickets = {p.ticket for p in mt5_positions}
    db_tickets = {t.broker_ticket for t in db_trades}

    # Orphaned MT5 positions (not in DB)
    orphaned = mt5_tickets - db_tickets
    if orphaned:
        logger.critical("ORPHANED MT5 POSITIONS: %s — manual intervention required", orphaned)
        telegram_bot.send_message(f"🚨 ORPHANED POSITIONS: {orphaned}")

    # Ghost DB trades (not on MT5)
    ghosts = db_tickets - mt5_tickets
    for ticket in ghosts:
        trade = next((t for t in db_trades if t.broker_ticket == ticket), None)
        if trade:
            logger.warning("Ghost trade %s (ticket %d) — marking as closed", trade.id, ticket)
            self.trade_manager.close_trade(trade.id, "RECONCILE_GHOST")
```

This already partially exists in `trade_manager.reconcile()` — extract and strengthen it.

### Phase 7: Broker Reconnect Backoff (Priority: LOW, ~30 min)

In `broker/mt5_connector.py`, add exponential backoff to `connect()`:

```python
def connect(self) -> bool:
    for attempt in range(5):
        delay = min(2 ** attempt, 60)  # 1, 2, 4, 8, 16 seconds (cap 60)
        if self._try_connect():
            self._reconnect_attempts = 0
            return True
        time.sleep(delay)
    return False
```

---

## 5. Code Structure & Standards

### 5.1 Folder Structure

See Section 2.1 for the complete target structure. Key rules:
- **One class per file** for agents and repos
- **`__init__.py`** files export nothing — use explicit imports
- **Tests mirror source**: `agents/risk_agent.py` → `tests/test_risk_agent.py`

### 5.2 Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `risk_agent.py` |
| Classes | `PascalCase` | `RiskAgent` |
| Functions | `snake_case` | `calculate_position_size` |
| Constants | `UPPER_SNAKE` | `MAX_OPEN_TRADES` |
| Private | `_prefix` | `_correlated_pairs` |
| Config | `UPPER_SNAKE` env var | `GUARD_MAX_DAILY_LOSS_PCT` |

### 5.3 Modularity Rules

1. **Agents never import each other.** They communicate via the orchestrator passing results between them.
2. **Database repos never import agents.** Data flows one direction: agent → repo.
3. **Config is read-only at import time.** No module writes to settings.
4. **The broker connector ABC is the only interface agents touch.** No `import MetaTrader5` in agent code.
5. **All timeouts are configurable via settings.** No hardcoded `time.sleep(10)`.

### 5.4 Logging Standards

Current logging is already good. Preserve these patterns:
- Each module: `logger = logging.getLogger(__name__)`
- Agent events go to both Python logger AND `db.log_agent_event()`
- Structured data as dict in the `data` parameter of `log_agent_event`
- Log levels: DEBUG for per-symbol scan details, INFO for signals/trades, WARNING for rejections, ERROR for failures, CRITICAL for system-level issues

**Add one thing:** Structured JSON log file alongside console output:
```python
# In LoggingAgent.__init__:
json_handler = logging.FileHandler("logs/bot.jsonl")
json_handler.setFormatter(JsonFormatter())  # outputs {"ts": ..., "level": ..., "msg": ..., "data": ...}
logging.getLogger().addHandler(json_handler)
```

### 5.5 Error Handling Rules

1. **Never swallow exceptions silently.** Always `logger.exception()` or `logger.warning()`.
2. **The main loop MUST NOT crash.** Wrap `_run_iteration` in try/except (already done — keep it).
3. **Individual symbol failures don't block other symbols.** Already implemented via per-symbol error handling.
4. **DB failures degrade gracefully.** If `log_agent_event` fails, log to console and continue.
5. **Broker failures trigger reconnect.** Already implemented.

---

## 6. Automation & Reliability

### 6.1 Scheduling

| Task | Trigger | Implementation |
|------|---------|---------------|
| Main loop | Continuous (10-30s interval) | `while not shutdown: _tick(); sleep(remaining)` |
| Reconciliation | Every N loops (configurable) | `loop_count % RECONCILE_EVERY_N_LOOPS == 0` |
| MT5→DB sync | Every 300s (configurable) | Monotonic timer comparison |
| Daily summary | At `DAILY_SUMMARY_HOUR` | Date comparison in main loop |
| Weekly WFO check | Sunday (in daily summary block) | `now.weekday() == 6` |
| Model retraining | Monthly (1st of month) | `now.day == 1` in daily summary block |
| Heartbeat | Every loop iteration | Called unconditionally |

All scheduling is already in the main loop. No external cron needed. **Keep this design** — it's simpler and more reliable than multi-process coordination.

### 6.2 Retry Logic

| Operation | Current Retry | Recommended Change |
|-----------|--------------|-------------------|
| MT5 IPC | 0 retries, symbol disabled after N failures | ✅ Keep as-is |
| MT5 reconnect | 1 attempt per loop | Add exponential backoff (Phase 7) |
| DB queries | psycopg2 pool auto-reconnect | Add 3-retry wrapper with 1s delay |
| Telegram sends | Fire-and-forget | ✅ Keep as-is (non-critical) |
| Order placement | 0 retries (intentional — avoid double fills) | ✅ Keep as-is |

**DB retry wrapper** (add to `database/pool.py`):
```python
import functools, time

def with_retry(max_retries=3, delay=1.0):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except psycopg2.OperationalError as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exc
        return wrapper
    return decorator
```

### 6.3 Fault Tolerance

The current fault tolerance is actually quite good:

- **Symbol fault tracking** with auto-disable and auto-re-enable (in `_run_iteration`)
- **Graceful degradation** when scan error rate exceeds threshold (skips rank+execute)
- **Consecutive failure counter** triggers CRITICAL log + Telegram alert after 3 failures
- **Market hours awareness** — sleeps longer when markets closed
- **Pause/resume** via Telegram and dashboard

**One addition needed:** DB connection pool health check:
```python
# In database/pool.py, call every heartbeat:
def check_pool_health():
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        put_conn(conn)
        return True
    except Exception:
        logger.error("DB pool health check failed")
        return False
```

### 6.4 State Management

Current state lives in three places:
1. **PostgreSQL** — trades, events, bot_status, commands (persistent, authoritative)
2. **In-memory** — TradeManager's open trade list, metrics dict, per-symbol cooldown timers (volatile)
3. **MT5 Terminal** — actual broker positions (authoritative for positions)

This is correct. The key invariant is: **MT5 is the source of truth for positions, DB is the source of truth for trade metadata.** The `reconcile()` function synchronizes them.

**State persistence across restarts** is already handled by:
- `StatePersistence.sync_mt5_to_db()` at startup
- `trade_manager.load_open_trades()` from DB at startup
- Symbol fault state persisted to DB (`save_symbol_fault` / `load_symbol_faults`)

---

## 7. Security & Risk Controls

### 7.1 API Key Handling

**Current:** Plain text in `.env`, loaded via `python-dotenv`.

**Required improvements:**

1. **Never log secrets.** Audit all `logger.info` calls in `main.py` and broker initialization — ensure account numbers are logged but passwords are not. Current code logs `acct_num` and `acct_srv` but not `acct_pwd` — this is correct. Verify no regression.

2. **Encrypt broker credentials in DB.** The `utils/crypto.py` module already exists with `encrypt()`/`decrypt()` using Fernet. The `database/db.py` already uses it for `broker_accounts` table. This is adequate.

3. **File permissions on `.env`:**
   ```powershell
   icacls .env /inheritance:r /grant:r "%USERNAME%:R"
   ```

4. **Do NOT add vault integration.** It's overkill for a single-machine bot. The current `.env` + DB encryption is sufficient.

### 7.2 Trade Safety Limits

These are already implemented across multiple layers. Document them in one place:

| Safety Limit | Location | Default Value |
|---|---|---|
| Max position size | `MaxPositionSizeGuard` | 2.0 lots |
| Max open trades | `RiskAgent.validate()` | 5 |
| Max daily loss % | `DailyDrawdownGuard` | 5% |
| Max equity drawdown % | `EquityDrawdownGuard` | 8% |
| Max risk per trade | `RiskAgent.calculate_position_size()` | 2% |
| Spread threshold | `RiskAgent.validate()` (per asset class) | 3 pips forex, 50 pips indices |
| Cooldown between trades | `CooldownGuard` | 300s same symbol |
| Max VIX | `GUARD_MAX_VIX` | 40.0 |
| Correlation block | `RiskAgent._check_correlation()` | Same-direction correlated pair |
| Market hours | `MarketHoursGuard` | No forex entries outside sessions |
| Volume filter | `VolumeFilterGuard` | Min volume threshold |
| Feed freshness | `FeedFreshnessGuard` | Stale data > 120s blocks trades |

### 7.3 Kill Switches

Three independent kill mechanisms:
1. **Telegram `/kill`** — closes all positions, shuts down bot
2. **Dashboard "kill" command** — same effect via DB command queue
3. **OS signal** (SIGINT/SIGTERM) — graceful shutdown

**Add a fourth:** Hardware kill switch via file sentinel:
```python
# In orchestrator/bot.py, check every loop:
KILL_FILE = Path("KILL")
if KILL_FILE.exists():
    logger.critical("KILL file detected — emergency shutdown")
    KILL_FILE.unlink()
    trade_manager.close_all("KILL_FILE")
    self.shutdown_requested = True
```

This allows emergency stop even if Telegram and the dashboard are both down — just create an empty file named `KILL` in the bot directory.

---

## 8. Scaling & Optimization

### 8.1 Performance Improvements

| Area | Current Bottleneck | Fix |
|------|-------------------|-----|
| Symbol scanning | Serial MT5 IPC (~200ms/symbol × 30 symbols = 6s) | Cannot parallelize (MT5 IPC limitation). Reduce via cooldowns — already done. |
| ICT engine | ~50-100ms per symbol (12-module pipeline) | Already fast enough. No change needed. |
| DB writes | ~5ms per `log_agent_event` call, ~50 calls per loop | Batch writes: collect events in memory, flush every 5s in a background thread |
| Heartbeat | Reads equity/balance/positions from MT5 every loop | Already cached with fallback. No change needed. |

**Batch DB writes** (biggest win):
```python
# In database/event_repo.py:
class EventRepo:
    def __init__(self):
        self._buffer = []
        self._lock = threading.Lock()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def log(self, agent, level, msg, data=None):
        with self._lock:
            self._buffer.append((agent, level, msg, data, datetime.now(UTC)))

    def _flush_loop(self):
        while True:
            time.sleep(5)
            self._flush()

    def _flush(self):
        with self._lock:
            batch = self._buffer[:]
            self._buffer.clear()
        if not batch:
            return
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, INSERT_EVENT_SQL, batch)
            conn.commit()
        finally:
            put_conn(conn)
```

This reduces DB round-trips from ~50/loop to ~1/5s.

### 8.2 Parallelization Opportunities

**Limited by MT5.** The MetaTrader5 Python package uses Windows IPC (named pipes) that is not thread-safe. The bot already correctly forces serial scanning for MT5. There is nothing to parallelize on the data-fetching side.

**What CAN run in parallel:**
- DB event logging (background thread flush — see above)
- Telegram message sending (already fire-and-forget in a thread)
- WebSocket notifications (already async)
- LGBM inference (already fast, not worth parallelizing)

### 8.3 Future Enhancements (In Priority Order)

1. **Multi-account support** — the DB already has a `broker_accounts` table. Add a second MT5 instance on a different Windows machine, connect both to the same Postgres DB, partition symbols between them. The orchestrator reads its assigned symbols from DB.

2. **Dockerized backtesting** — run `scripts/backtest.py` in a Linux container with MT5 mocked out. This decouples backtesting from the live Windows machine.

3. **Feature store** — persist computed features (ATR, GARCH σ, LGBM scores) to a `features` table so the dashboard can display them and the learning agent can use them for post-trade analysis.

4. **Strategy hot-reload** — the `plugin_loader.py` already supports dynamic strategy loading. Extend it to watch a directory and reload strategies without restarting the bot.

5. **Multi-broker support** — add a REST-based broker connector (e.g., for cTrader or Interactive Brokers) alongside MT5. The `BrokerConnector` ABC makes this a clean addition.

---

## Appendix A: File-by-File Action Items

| File | Action | Phase |
|------|--------|-------|
| `main.py` (1863L) | Extract into orchestrator/ | Phase 1 |
| `database/db.py` (2181L) | Split into 6 repos + pool | Phase 2 |
| `config/settings.py` (855L) | Rewrite with Pydantic | Phase 3 |
| `agents/deepseek_strategy.py` (42K) | DELETE | Phase 4 |
| `agents/council_agent.py` (33K) | DELETE | Phase 4 |
| `agents/debate_agent.py` (12K) | DELETE | Phase 4 |
| `agents/exposure_coach.py` (5.5K) | DELETE | Phase 4 |
| `agents/memory_agent.py` (8K) | DELETE | Phase 4 |
| `strategies/sma_crossover.py` (4.5K) | DELETE | Phase 4 |
| `strategies/scalp_m5.py` (16K) | DELETE | Phase 4 |
| `llm/openrouter_gateway.py` (4.5K) | DELETE | Phase 4 |
| `models/agent_mesh.py` (1K) | DELETE | Phase 4 |
| `agents/risk_agent.py` | Wire CorrelationGate as primary, keep hardcoded as fallback | Phase 1 |
| `broker/mt5_connector.py` | Add exponential backoff to connect() | Phase 7 |
| `tests/` | Add test_iteration_e2e.py | Phase 5 |

## Appendix B: Environment Variables (Complete Reference)

All settings with their types, defaults, and safe ranges. Minimax 2.7 should preserve these when rewriting `config/settings.py`:

```
# Critical (must be set)
BROKER_ACCOUNT          str     ""          MT5 account number
BROKER_PASSWORD         str     ""          MT5 password
BROKER_SERVER           str     ""          MT5 server name
DATABASE_URL            str     ""          Postgres connection string

# Risk (validate ranges)
MAX_RISK_PER_TRADE      float   0.02        [0.001, 0.10]
MAX_OPEN_TRADES         int     5           [1, 20]
GUARD_MAX_DAILY_LOSS_PCT float  0.05        [0.01, 0.20]
GUARD_MAX_VIX           float   40.0        [15.0, 80.0]
FIXED_LOT_SIZE          float   0.01        [0.01, 2.0]

# Orchestration (validate ranges)
LOOP_INTERVAL_SECONDS                int     30      [5, 300]
SCAN_COOLDOWN_SECONDS_LONDON_NY      float   60      [10, 600]
SCAN_COOLDOWN_SECONDS_ASIA           float   120     [30, 600]
SNIPER_CONF_THRESHOLD                float   0.45    [0.20, 0.90]
ORCHESTRATION_MAX_SCAN_MS            int     90000   [5000, 300000]
ORCHESTRATION_MAX_ITERATION_MS       int     120000  [10000, 600000]

# Features (boolean toggles)
LGBM_ENSEMBLE_ENABLED   bool    true
KALMAN_ENABLED           bool    true
GARCH_ENABLED            bool    true
GUARD_PIPELINE_ENABLED   bool    true
SNIPER_ENTRY_ENABLED     bool    true
FAST_LANE_ENABLED        bool    true
DEFERRED_ENTRY_ENABLED   bool    true
```

---

**End of Blueprint.** Execute phases 1-7 in order. Each phase is independently verifiable. Do not skip phases or reorder. The bot must remain operational after each phase.
