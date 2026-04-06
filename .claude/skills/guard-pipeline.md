# Skill: guard-pipeline

Covers the GuardPipeline and all pre-execution safety checks.

---

## Files

| File | Purpose |
|---|---|
| `agents/guards.py` | 7 guards + `GuardPipeline` orchestrator |
| `agents/exposure_coach.py` | Portfolio concentration / correlation advisor |
| `agents/execution_agent.py` | Consumes both at the top of `_open_inner()` |

---

## Guards (agents/guards.py)

| Guard | What it checks | Blocks on |
|---|---|---|
| `MaxPositionSizeGuard` | `signal.lot_size_override` exceeds hard cap (2.0 lots) — skipped when no override is set | Explicitly oversized orders |
| `SymbolWhitelistGuard` | `symbol in WHITELISTED_SYMBOLS` | Unknown instruments |
| `CooldownGuard` | Time since last trade on same symbol | Rapid re-entries within `GUARD_COOLDOWN_SECONDS` |
| `DailyDrawdownGuard` | Today's realised loss > `GUARD_MAX_DAILY_LOSS_PCT`% | Blown daily draw limit |
| `MarketHoursGuard` | Is current UTC time inside trading session? | Off-hours (weekend / session gap) |
| `VolatilityGuard` | VIX > `GUARD_MAX_VIX` | Extreme panic conditions |
| `FeedFreshnessGuard` | Age of last price tick < `GUARD_FEED_STALENESS_SECONDS` | Stale market data |

All guards **fail-open** (pass the trade) on internal exceptions — never block on crashes.

---

## GuardPipeline

```python
from agents.guards import GuardPipeline

pipeline = GuardPipeline(broker=broker, db=db)
passed, reason = pipeline.check(signal, open_trades=live_positions)

if not passed:
    logger.warning("Trade blocked: %s", reason)
```

`GUARD_PIPELINE_ENABLED` env/setting disables the entire pipeline (default: True).

---

## ExposureCoach (agents/exposure_coach.py)

Advisory layer — returns sizing recommendations, does NOT block on its own.

```python
from agents.exposure_coach import ExposureCoach

coach = ExposureCoach()
advice = coach.evaluate(open_trades, signal, requested_lots=0.05)

if advice.is_overexposed:
    logger.warning(advice.reason)
    lot_size = advice.suggested_lots   # possibly 0.0 (do not open)
else:
    lot_size = requested_lots
```

**Thresholds** (tuneable in `exposure_coach.py`):

| Constant | Default | Meaning |
|---|---|---|
| `_MAX_TOTAL_EXPOSURE_LOTS` | 0.50 | Max lots across all open positions |
| `_MAX_SAME_SYMBOL_LOTS` | 0.10 | Max lots on a single instrument |
| `_MAX_CORR_EXPOSURE_LOTS` | 0.20 | Max lots in one correlation group |

---

## Integration in ExecutionAgent

The ExecutionAgent runs **both** the GuardPipeline and (optionally) the
ExposureCoach at the top of `_open_inner()` before the autotrading-block check:

```
signal → GuardPipeline.check() → blocked? → return None (log "warn")
       → ExposureCoach.evaluate() → adjust lot_size
       → autotrading block check
       → duplicate guard
       → broker.place_order()
```

---

## Adding a New Guard

1. Subclass `Guard` (abstract base) in `agents/guards.py`
2. Implement `check(self, signal, open_trades, broker) -> tuple[bool, str]`
3. Add an instance to the `self._guards` list in `GuardPipeline.__init__`
4. Guard auto-participates in `GuardPipeline.check()` immediately

## Important: MaxPositionSizeGuard Behaviour
`MaxPositionSizeGuard` only enforces the cap when `signal.lot_size_override` is explicitly set.
It does NOT compare `settings.MAX_LOT_SIZE` against the cap — that was a bug (fixed 2026-04-06).
`settings.MAX_LOT_SIZE` is a user-facing ceiling (can be 50+); the guard cap (2.0) is independent.

---

## Key Settings

```env
GUARD_PIPELINE_ENABLED=true
GUARD_COOLDOWN_SECONDS=300
GUARD_MAX_DAILY_LOSS_PCT=2.0
GUARD_MAX_VIX=40
GUARD_FEED_STALENESS_SECONDS=120
```
