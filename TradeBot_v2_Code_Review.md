# TradeBot v2 — Brutal Code Review & Action Plan

**Date:** April 2026
**Scope:** Line-by-line audit of every file changed since v1, plus full system integrity check
**Verdict:** Good structural progress. 5 bugs that will crash or corrupt production. ~200 lines of dead code still shipping. Several blueprint items skipped.

---

## 1. Bugs That Will Break Production

These must be fixed before any other work. Each one will cause a real failure.

### BUG-1: Connection Pool Downgrades After First Reconnect (CRITICAL)

**File:** `database/pool.py` lines 21–32 vs 65–76

`_connect()` creates a `ThreadedConnectionPool(maxconn=20)`. `_reconnect()` creates a `SimpleConnectionPool(maxconn=5)`. After the first stale-connection event (which WILL happen — Vercel Postgres drops idle connections after 5 minutes), the pool silently downgrades to a non-thread-safe pool with 75% fewer connections. Any subsequent concurrent DB access will corrupt data or deadlock.

**Fix:**
```python
def _reconnect(self) -> None:
    logger.info("Rebuilding DB connection pool…")
    try:
        if self._pool:
            self._pool.closeall()
    except Exception:
        pass
    self._pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,                           # ← MATCH _connect()
        dsn=self._dsn,
        options="-c statement_timeout=15000",
    )
    logger.info("DB connection pool rebuilt")
```

Also: the type annotation `self._pool: psycopg2.pool.SimpleConnectionPool | None` on line 18 is wrong — it should be `ThreadedConnectionPool | None` (or just the base `AbstractConnectionPool`).

---

### BUG-2: Consecutive Failure Counter Never Resets (HIGH)

**File:** `orchestrator/bot.py` line 555

`_metrics["iter_consecutive_failures"]` is incremented on every exception but never set back to 0 on a successful iteration. After 3 total failures across the bot's entire lifetime (even if separated by thousands of successful loops), the CRITICAL log will fire on every subsequent failure forever.

**Fix — add one line after the `except` block, inside the `try:` success path (around line 549):**
```python
try:
    _weekend = is_weekend()
    run_iteration(...)
    _metrics["iter_consecutive_failures"] = 0      # ← ADD THIS
except (KeyboardInterrupt, SystemExit):
    raise
except Exception:
    _metrics["iter_consecutive_failures"] = ...
```

---

### BUG-3: Deleted Module Still Imported — Runtime Crash (HIGH)

**Files:** `agents/crucix_agent.py` line 46, `agents/logging_agent.py` line 105

Both files lazily import `from agents.memory_agent import MemoryAgent`. The file `agents/memory_agent.py` was deleted. When either agent's `_memory` property is first accessed (which happens during Crucix context logging and daily summary generation), the bot will crash with `ModuleNotFoundError`.

**Fix — two options:**

Option A (recommended): Remove the `_memory` property and all references from both files. These agents don't need MemoryAgent since the council/debate system was removed.

Option B: Re-create a minimal `agents/memory_agent.py` stub if the memory write functionality is still desired. But based on the code, it's only used to write "reflection" blocks that nobody reads.

**For Option A, in `agents/crucix_agent.py`:** delete lines 39–48 (the `_memory_instance` field and `_memory` property) and every line that calls `self._memory`. Same treatment for `agents/logging_agent.py` lines 94–107.

---

### BUG-4: Orphan Scan Runs Every Loop — Double MT5 IPC Load (MEDIUM)

**File:** `orchestrator/bot.py` lines 589–603

`self.state.scan_orphans()` calls `broker.get_open_positions()` + `db.get_open_trades()` every single loop iteration (every 10–30 seconds). The heartbeat (lines 611–617) ALSO calls `broker.get_open_positions()`. That's 2 MT5 IPC calls per loop for the same data, plus 2 DB queries. On MT5's single-threaded IPC, this wastes ~200ms per loop.

**Fix:** Move the orphan scan inside the periodic reconciliation block:
```python
# Line 619 — change this:
if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
    self.trade_manager.reconcile()
    self.log_agent.record("RECONCILE", ...)

# To this:
if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
    try:
        orphan_tickets = self.state.scan_orphans()
        if orphan_tickets:
            logger.warning("Orphan scan: %d — tickets: %s", len(orphan_tickets), orphan_tickets)
            telegram_bot.send_message(f"🚨 {len(orphan_tickets)} orphan position(s): {orphan_tickets}")
    except Exception:
        logger.warning("Orphan scan failed")
    self.trade_manager.reconcile()
    self.log_agent.record("RECONCILE", ...)
```

Delete the standalone orphan scan block at lines 589–603.

---

### BUG-5: Startup Crash Leaves Broker Connected (MEDIUM)

**File:** `main.py` lines 17–19

```python
bot = TradingBot()
bot.startup()    # ← If this fails after broker.connect() but before completion,
bot.run()        #    broker stays connected, DB stays open, Telegram keeps polling
```

If `startup()` crashes midway (e.g., line 178 — StrategyAgent fails to initialize), the broker connection, DB pool, candle server, and Telegram poller are all left running as zombies.

**Fix:**
```python
if __name__ == "__main__":
    bot = TradingBot()
    try:
        bot.startup()
        bot.run()
    except Exception:
        logging.exception("Fatal error")
        bot.shutdown()
        sys.exit(1)
```

---

## 2. Dead Code Still Shipping

Every line of dead code is a line that can confuse you, confuse Minimax, and create phantom bugs during refactoring. This must be cleaned.

### 2A. Config: ~200 Lines of Dead Settings + Re-exports

**File:** `config/settings.py`

| Dead Settings Class | Lines | Why Dead |
|---|---|---|
| `CouncilSettings` | 154–171 | Council agent deleted |
| `DebateSettings` | 173–179 | Debate agent deleted |
| `DeepSeekSettings` | 467–492 | DeepSeek strategy deleted |
| `ScalpSettings` | 458–464 | Scalp strategy deleted |

Plus ~50 flat re-export lines at the bottom (lines 1430–1464): `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `COUNCIL_DEEPSEEK_*_WEIGHT`, `SCALP_*`, etc.

Plus 4 lines using raw `_get_env()` instead of Pydantic at the very end (lines 1458–1461): `COUNCIL_DEEPSEEK_*_WEIGHT` — these bypass all validation.

**Action:** Delete all four Settings classes, their instantiation in `_Settings`, their `_build_settings` blocks, and all flat re-exports that reference them.

### 2B. Agent Code Referencing Deleted Strategies

| File | Line(s) | Dead Reference |
|---|---|---|
| `agents/risk_agent.py` | 306 | `if signal.strategy == "scalp_m5":` |
| `agents/guards.py` | 545, 553, 668 | `ScalpExposureGuard` + `scalp_m5` checks |
| `agents/trade_manager.py` | 690, 693 | `scalp_m5` close notification |
| `utils/mesh_bus.py` | 53–54 | Maps `sma_crossover`, `deepseek_strategy` |

**Action:** Remove each dead reference. For `ScalpExposureGuard` in `guards.py`: delete the entire class (lines 535–680) and remove it from the `GuardPipeline` list.

### 2C. Empty Packages and Dead Files

| Item | Action |
|---|---|
| `llm/` directory (only `__init__.py` with one docstring) | Delete entire directory |
| `models/agent_mesh.py` (unused dataclass) | Delete file |
| `models/memories/` directory (4 JSON files, no reader) | Delete directory |
| `agents/signal_postmortem.py` | Verify if imported anywhere; if not, delete |

```bash
# Verify signal_postmortem usage:
grep -rn "signal_postmortem\|SignalPostmortem" --include="*.py" . | grep -v __pycache__
```

### 2D. Test Files Referencing Deleted Modules

These tests will fail or test phantom code:

| File | Issue |
|---|---|
| `tests/conftest.py` | May reference deleted agents |
| `tests/test_tool_system.py` | References `scalp_m5` |
| `tests/test_learning_agent.py` | References `scalp_m5` |
| `tests/test_unified_strategy.py` | References `sma_crossover` |
| `tests/test_risk_agent.py` | References `scalp_m5` |
| `tests/test_backtest_reporting_schema.py` | References deleted strategies |

**Action:** Run `pytest --collect-only` and fix every import error. Then run full suite and fix failures.

---

## 3. Architecture Problems

### 3A. `broker_repo.py` Is a Junk Drawer (759 Lines, ~15 Unrelated Domains)

This file handles: broker accounts, symbol faults, ICT setups, trade theses, dashboard users, signals, agent reputation, leaderboards, subscriptions, macro snapshots, and memory blocks. None of these are "broker" operations.

**Action:** Split into at minimum:
- `broker_repo.py` — broker accounts, symbol faults, mark_connected (keep name, reduce to ~200 lines)
- `user_repo.py` — dashboard users (get_user_by_*, create_user, update_password)
- `signal_repo.py` — signals, ICT setups, trade theses
- `social_repo.py` — subscriptions, leaderboards, agent reputation
- `macro_repo.py` — macro snapshots, memory blocks

Update `Database` facade to wire new repos. This is a mechanical split — no logic changes.

### 3B. `db.py` Facade Is 463 Lines of Pure Pass-Through

The Database class has 60+ methods that each do nothing but `return self.repo.method(...)`. The facade was the right idea for backward compatibility, but now it needs to slim down.

**Action (later — not urgent):** Over time, migrate callers to use `db.trades.upsert_trade()` directly. Add a deprecation comment at the top of each facade method. Don't delete them yet — they serve as the migration bridge.

### 3C. Config `_build_settings()` Defeats Pydantic

The `_build_settings()` function (lines 548–1104) manually calls `os.getenv()` for every single setting and passes them to Pydantic constructors. This is ~550 lines that completely bypass Pydantic's built-in env var parsing. Pydantic `BaseSettings` already reads environment variables automatically — that's its entire purpose.

**Why this matters:** If someone sets `MAX_RISK_PER_TRADE=abc` in `.env`, the current code will crash at `float("abc")` in `_build_settings` line ~640 with a raw `ValueError`, NOT a clean Pydantic validation error. You get the worst of both worlds: manual parsing AND Pydantic overhead.

**Action (phased):** This is the biggest refactor remaining. The correct approach:

1. Rename env vars to match Pydantic nesting: `RISK__MAX_RISK_PER_TRADE=0.02` (using `__` as separator per `SettingsConfigDict(env_nested_delimiter="__")`)
2. Delete all of `_build_settings()` — let Pydantic auto-parse
3. Keep `_apply_profile_overrides()` for profile presets
4. Keep the flat re-export block for backward compatibility

This is ~550 lines deleted. But it requires renaming env vars in `.env` and all deployment configs. **Do it in a dedicated PR with no other changes.**

### 3D. Correlation Gate Never Wired

**File:** `agents/risk_agent.py`

The hardcoded `_CORRELATED_PAIRS` dict (lines 45–95) is still the only correlation source. `utils/correlation_gate.py` exists (8.5K) but is never imported or used in `RiskAgent`. The blueprint specifically called this out.

**Action:**
```python
# In RiskAgent.__init__ (around line 140):
from utils.correlation_gate import CorrelationGate
self._corr_gate = CorrelationGate(lookback_bars=100, threshold=0.75)

# In _check_correlation (around line 1220):
# Try dynamic first, fall back to static
if self._corr_gate.has_data(signal.symbol):
    if self._corr_gate.is_correlated(signal.symbol, open_symbol, signal.direction):
        return False, "dynamic_correlation"
else:
    # Fall back to static table
    correlated = _CORRELATED_PAIRS.get(signal.symbol, frozenset())
    ...
```

---

## 4. Missing Blueprint Items

| Blueprint Item | Status | Priority |
|---|---|---|
| Extract orchestrator/ | ✅ Done | — |
| Split database repos | ✅ Done (but broker_repo is a junk drawer) | — |
| Pydantic config | ⚠️ Partially done (manual parsing defeats purpose) | MEDIUM |
| Dead code removal | ⚠️ Partially done (~200 lines remain) | HIGH |
| E2E pipeline tests | ⚠️ 3 tests exist, none test failure paths | MEDIUM |
| Continuous reconciliation | ✅ Done (scan_orphans + periodic reconcile) | — |
| Broker reconnect backoff | ✅ Done | — |
| DB retry wrapper | ❌ Not implemented | MEDIUM |
| Event write batching | ❌ Not implemented | LOW |
| KILL file sentinel | ❌ Not implemented | LOW |
| NSSM service setup | ❌ Not implemented (docs/scripts) | MEDIUM |
| TP percent cross-validation | ❌ Not implemented | LOW |

---

## 5. Implementation Plan (Ordered)

### Phase 1: Fix the 5 Bugs (2 hours)

Do these in a single commit. Test each one:

1. **BUG-1:** Fix `pool.py` `_reconnect()` to use `ThreadedConnectionPool(maxconn=20)`
2. **BUG-2:** Add `_metrics["iter_consecutive_failures"] = 0` after successful `run_iteration()`
3. **BUG-3:** Remove `_memory` property + imports from `crucix_agent.py` and `logging_agent.py`
4. **BUG-4:** Move `scan_orphans()` inside `RECONCILE_EVERY_N_LOOPS` block
5. **BUG-5:** Wrap `startup()` + `run()` in try/finally in `main.py`

**Verification:** Bot starts, runs 100 loops, and shuts down cleanly. Force a DB reconnect by killing the Postgres connection — verify pool recovers. Force a `run_iteration` exception — verify counter resets to 0 on next success.

### Phase 2: Purge Dead Code (1.5 hours)

1. Delete `CouncilSettings`, `DebateSettings`, `DeepSeekSettings`, `ScalpSettings` from `config/settings.py` and all their re-exports (~200 lines)
2. Delete `ScalpExposureGuard` from `agents/guards.py` and all `scalp_m5` references in `risk_agent.py`, `trade_manager.py`
3. Delete `sma_crossover` and `deepseek_strategy` from `utils/mesh_bus.py`
4. Delete `llm/` directory, `models/agent_mesh.py`, `models/memories/`
5. Remove `_memory` property from `crucix_agent.py` and `logging_agent.py` (if not done in Phase 1)
6. Fix test files — remove references to deleted modules, run `pytest --collect-only`

**Verification:** `grep -rn "scalp_m5\|sma_crossover\|deepseek_strategy\|council_agent\|debate_agent\|memory_agent\|agent_mesh" --include="*.py" .` returns zero results (excluding this blueprint file). `pytest` collects and passes.

### Phase 3: Split broker_repo.py (1.5 hours)

1. Create `database/user_repo.py` — move `get_user_by_*`, `create_user`, `update_user_password`, `get_all_users`, `user_count`
2. Create `database/signal_repo.py` — move `save_signal`, `get_signals`, `mark_signal_points_awarded`, `save_ict_setup`, `save_trade_thesis`, `get_trade_thesis`, `update_trade_outcome`
3. Create `database/social_repo.py` — move `get_agent_reputation`, `bump_agent_reputation`, `get_leaderboard`, `save_subscription`, `get_subscriptions`, `delete_subscription`, `get_followers`
4. Create `database/macro_repo.py` — move `save_macro_snapshot`, `get_macro_snapshots`, `prune_macro_snapshots`, `write_memory_block`, `read_memory_block`
5. Reduce `broker_repo.py` to: broker accounts + symbol faults + `mark_broker_connected`
6. Wire new repos into `Database.__init__` and add facade methods

**Verification:** All existing tests pass. Bot starts and dashboard works.

### Phase 4: DB Retry Wrapper (30 minutes)

**File:** `database/pool.py` — add at the bottom:

```python
import functools
import time as _time

def with_retry(max_retries: int = 3, base_delay: float = 0.5):
    """Decorator for repo methods — retries on OperationalError."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        _time.sleep(base_delay * (2 ** attempt))
                        logger.warning("DB retry %d/%d for %s: %s",
                                       attempt + 1, max_retries, fn.__name__, e)
            raise last_exc
        return wrapper
    return decorator
```

Apply to critical repo methods: `TradeRepo.upsert_trade`, `TradeRepo.get_open_trades`, `EventRepo.log_agent_event`, `StatusRepo.update_bot_status`.

### Phase 5: Wire Correlation Gate (30 minutes)

See Section 3D above. Three changes in `risk_agent.py`:
1. Import `CorrelationGate` in `__init__`
2. Instantiate in constructor
3. Add dynamic check before static fallback in `_check_correlation`

### Phase 6: Add Failure-Path E2E Tests (2 hours)

Add to `tests/test_iteration_e2e.py`:

```python
def test_risk_rejection_blocks_trade(mock_broker, fake_db, monkeypatch):
    """When risk_agent.validate returns False, no trade opens."""
    ...

def test_drawdown_guard_blocks_all_signals(mock_broker, fake_db, monkeypatch):
    """After max daily loss exceeded, every signal is rejected."""
    ...

def test_paused_bot_skips_signal_detection(mock_broker, fake_db, monkeypatch):
    """When telegram_bot.is_paused() is True, no signals are generated."""
    ...

def test_ipc_failure_triggers_reconnect(mock_broker, fake_db, monkeypatch):
    """When all symbols fail IPC, broker.connect() is called."""
    ...

def test_degraded_mode_skips_execution(mock_broker, fake_db, monkeypatch):
    """When scan error rate exceeds threshold, rank+execute are skipped."""
    ...

def test_deferred_entry_promoted_next_loop(mock_broker, fake_db, monkeypatch):
    """A soft-rejected signal with high confidence is deferred and re-evaluated."""
    ...
```

### Phase 7: KILL File Sentinel (15 minutes)

**File:** `orchestrator/bot.py` — add at the top of the while loop:

```python
_KILL_FILE = Path(__file__).resolve().parent.parent / "KILL"

# Inside while loop, before anything else:
if _KILL_FILE.exists():
    logger.critical("KILL file detected — emergency shutdown")
    try:
        _KILL_FILE.unlink()
    except Exception:
        pass
    self.trade_manager.close_all("KILL_FILE")
    telegram_bot.send_message("🚨 KILL file — all positions closed, shutting down.")
    self._request_shutdown()
    continue
```

### Phase 8: TP Cross-Validation (15 minutes)

**File:** `config/settings.py` — add to `ExecutionSettings`:

```python
from pydantic import model_validator

class ExecutionSettings(BaseModel):
    ...
    @model_validator(mode="after")
    def _tp_sum_check(self) -> "ExecutionSettings":
        total = (self.tp1_close_percent + self.tp2_close_percent
                 + self.tp3_close_percent + self.tp4_close_percent)
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"TP close percents must sum to 1.0, got {total:.2f}"
            )
        return self
```

---

## 6. What Was Done Well

Credit where due — the v1→v2 refactor got the hard parts right:

1. **Orchestrator extraction is clean.** `main.py` is 15 lines. `bot.py`, `iteration.py`, `commands.py`, `heartbeat.py` are correct decompositions. The function signatures are preserved, imports are minimal, no logic was changed.

2. **HeartbeatManager is properly encapsulated.** The global `_hb_equity`/`_hb_balance` state moved into instance variables. MT5 thread-safety warning is preserved in the docstring.

3. **Database repo pattern is the right architecture.** The facade preserves backward compatibility perfectly. Every existing `db.save_trade()` call still works. New code can use `db.trades.upsert_trade()`. This is textbook migration.

4. **MT5 connector has real exponential backoff.** 3 retries with 5s/10s delays on `connect()`, plus per-symbol IPC backoff with doubling (30s → 60s → ... → 300s max). This is production-quality.

5. **Pydantic settings structure is correct.** 30+ typed sub-models with range validators (`ge`, `le`), field-level validation. The structure is right even though the wiring is wrong (manual `_build_settings`).

6. **E2E test framework exists.** `_FakeDB`, mock broker setup, and 3 working tests is a good foundation. The fixture pattern is correct and extensible.

7. **`scan_orphans()` is the right idea.** Lightweight read-only check separated from the heavier reconciliation. Just needs to move into the periodic block.

---

## 7. Summary of All Actions

| # | Action | Phase | Time | Severity |
|---|--------|-------|------|----------|
| 1 | Fix pool `_reconnect()` type mismatch | 1 | 5 min | CRITICAL |
| 2 | Reset `iter_consecutive_failures` on success | 1 | 2 min | HIGH |
| 3 | Remove dead `MemoryAgent` imports from 2 agents | 1 | 10 min | HIGH |
| 4 | Move `scan_orphans()` into periodic reconcile block | 1 | 10 min | MEDIUM |
| 5 | Wrap `startup()`/`run()` in try/finally | 1 | 5 min | MEDIUM |
| 6 | Delete 4 dead Settings classes + re-exports | 2 | 30 min | HIGH |
| 7 | Delete `ScalpExposureGuard` + all `scalp_m5` refs | 2 | 20 min | HIGH |
| 8 | Delete dead dirs/files (llm/, agent_mesh, memories/) | 2 | 10 min | MEDIUM |
| 9 | Fix test files referencing deleted modules | 2 | 30 min | MEDIUM |
| 10 | Split `broker_repo.py` into 4 focused repos | 3 | 90 min | MEDIUM |
| 11 | Add DB retry decorator to critical methods | 4 | 30 min | MEDIUM |
| 12 | Wire `CorrelationGate` into `RiskAgent` | 5 | 30 min | MEDIUM |
| 13 | Add 6 failure-path E2E tests | 6 | 120 min | MEDIUM |
| 14 | Add KILL file sentinel | 7 | 15 min | LOW |
| 15 | Add TP cross-validation | 8 | 15 min | LOW |
| 16 | Rewrite `_build_settings()` to use native Pydantic env parsing | Later | 4 hrs | LOW |

**Total estimated time: ~9 hours across 8 phases.**

Execute phases 1 and 2 first — they fix every production risk. The rest can be done incrementally while the bot is running.
