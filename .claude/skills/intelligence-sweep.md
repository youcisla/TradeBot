# Skill: intelligence-sweep

Covers the async macro intelligence layer and its consumers.

---

## Files

| File | Purpose |
|---|---|
| `filters/intelligence_sweep.py` | Async multi-source macro aggregator |
| `features/macro_features.py` | Converts `MacroSnapshot` → z-scored ML vector |
| `state/event_log.py` | NDJSON event logger consumed by the sweep |
| `state/heartbeat.py` | Daemon heartbeat writer |

---

## MacroSnapshot Fields

| Field | Source | Meaning |
|---|---|---|
| `dgs10` / `dgs2` | FRED | US Treasury yields 10yr / 2yr |
| `t10y2y` | FRED | Yield spread (10Y minus 2Y) |
| `vixcls` | FRED | CBOE VIX index |
| `dtwexbgs` | FRED | Broad USD trade-weighted index |
| `dcoilwtico` | FRED | WTI crude spot price |
| `fedfunds` | FRED | Effective Fed Funds Rate |
| `m2sl` | FRED | M2 money supply |
| `unrate` | FRED | US unemployment rate |
| `cpiaucsl` | FRED | US CPI |
| `spy_prev_close` | yfinance | SPY previous day close |
| `gld_prev_close` | yfinance | GLD previous day close |
| `dxy_prev_close` | yfinance | UUP (DXY proxy) previous close |
| `crude_inventory_change_mbbl` | EIA | Weekly crude inventory draw/build |
| `gdelt_risk_tone` | GDELT | Global news risk tone index |
| `risk_tier` | Derived | "low"/"normal"/"elevated"/"crisis" from VIX |
| `yield_curve_inverted` | Derived | True if T10Y2Y < 0 |
| `usd_strength` | Derived | "strong"/"neutral"/"weak" from DTWEXBGS |

---

## Starting the Sweep

```python
import asyncio
from filters.intelligence_sweep import IntelligenceSweep

sweep = IntelligenceSweep()
asyncio.run(sweep.start())   # runs indefinitely; call stop() to halt

snap = sweep.get_latest()    # thread-safe; returns None if not yet run
```

Interval is controlled by `INTELLIGENCE_SWEEP_INTERVAL_MINUTES` (default 60).

---

## Required Environment Variables

```env
FRED_API_KEY=your_fred_api_key     # https://fred.stlouisfed.org/docs/api/api_key.html
YFINANCE_ENABLED=true              # set false to skip yfinance sources
```

EIA and GDELT are public APIs — no key required.

---

## Fail-Safe Design

Each of the 4 sources (FRED, yfinance, EIA, GDELT) fails independently.
Partial snapshots are always returned. `snap.sources_failed` lists any
sources that errored. The bot never blocks on intelligence-sweep failures.

---

## Heartbeat

```python
from state.heartbeat import Heartbeat
hb = Heartbeat()
hb.start()        # starts daemon thread
hb.ping(last_sweep="2025-01-01T00:00:00Z")   # add custom fields
# reads from state/heartbeat.json
```

---

## EventLog

```python
from state.event_log import EventLog
log = EventLog()
log.emit("macro_sweep", {"vix": 18.5, "risk_tier": "normal"})
recent = log.tail(50)
count  = log.count_today("macro_sweep")
```

Events written to `logs/events_YYYY-MM-DD.ndjson` with daily rotation.
