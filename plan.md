# Fix Plan: Comprehensive Bot Optimization (Backend · Frontend · API)

## Context

Two scopes merged into this plan:

**Scope A — Emergency bugs (from Apr 13–16 log analysis):** The bot was generating **zero signals for 3+ days**, couldn't close a zombie TAN trade (56h open, −4.04 PnL), was logging an error every 5s (DummySignal guard crash), and cascade-disabled all 43 equity symbols from stuck-quote errors.

**Scope B — User request:** "we have a lot of issues in the backend and frontend and api, fix every issue you can for optimal trading performance and experience." Three parallel audits surfaced ~40 additional issues.

The plan is organized into 4 tiers. Tier 0 restores trading. Tiers 1–3 improve performance, resilience, and UX.

Origin state verified:
- `agents/guards.py` DummySignal.metadata fix — **APPLIED** (line 565).
- `broker/mt5_connector.py` `for_close` param — **MISSING** (prior worktree was deleted).
- `orchestrator/bot.py` stale fault cleanup — **MISSING**.
- `config/settings.py` threshold raise — **MISSING**.

---

## Tier 0 — Restore Trading (EMERGENCY, re-apply to origin)

### T0.1 — DummySignal missing `metadata` — already in origin
File: `agents/guards.py:565` — verified present.

### T0.2 — FIXED_LOT_SIZE applied to close operations (CRITICAL)
**Root cause:** `_normalize_volume()` applies `FIXED_LOT_SIZE` to every volume including closes. For TAN (ETF) where `volume_min > 0.01`, returns 0.0 → close rejected → zombie trade.

**Fix:** `broker/mt5_connector.py`
- Line 693 — signature: `def _normalize_volume(symbol: str, requested: float, for_close: bool = False) -> float:`
- Guard the FIXED_LOT_SIZE block: `if not for_close:` before the fixed-lot enforcement
- Line 566 (inside `close_partial`): `normalized_volume = self._normalize_volume(broker_sym, requested_volume, for_close=True)`

### T0.3 — Stuck-quote cascade: raise threshold + clear stale faults on restart
**Fix A:** `config/settings.py`
- Line 268: `symbol_max_fail_count: int = Field(default=20, ge=1)` (was 12)
- Line 269: `symbol_disable_seconds: int = Field(default=1800, ge=0)` (was 3600)
- Lines 792–793: update env-int defaults from 12/3600 → 20/1800

**Fix B:** `orchestrator/bot.py` lines 619–625 — when loading faults at startup, clear `fail_count` for symbols whose `disabled_until` is in the past:
```python
for _sym, _fault in self.db.load_symbol_faults().items():
    if _fault["disabled_until"] is not None:
        _remaining = (_fault["disabled_until"] - _now_utc).total_seconds()
        if _remaining > 0:
            _symbol_fail_count[_sym] = _fault["fail_count"]
            _symbol_disabled_until[_sym] = _now_mono + _remaining
        # else: cooldown expired → do NOT carry forward fail_count
    else:
        _symbol_fail_count[_sym] = _fault["fail_count"]
```

### T0.4 — Crucix 503 (external)
No code change. Restart the Crucix service. Bot already degrades gracefully.

---

## Tier 1 — Backend Resilience & Performance

### T1.1 — Broad exception swallowing in `agents/exposure_agent.py`
9 bare `except Exception:` blocks silently pass. Replace with targeted catches and log at `warning` (keep fail-open semantics).

### T1.2 — `close_partial` volume assignment race (broker/mt5_connector.py)
Volume captured before the market request can drift. Re-fetch position volume inside the retry loop; abort if the position is already closed (ticket gone).

### T1.3 — `execution_agent` confirmation loop lacks backoff
Current: fixed sleep retry on broker confirmation. Change to exponential backoff (250ms → 500ms → 1s, cap 4 attempts) to avoid hammering MT5 during transient errors.

### T1.4 — Slow scan phase (277ms avg per symbol)
Profile `orchestrator/bot.py::scan_agent` with `cProfile` for one cycle. Likely culprits: sequential MT5 symbol_info calls, un-batched DB writes. Add batched `symbol_info` prefetch and `executemany` for fault updates.

### T1.5 — Signal famine investigation
Even after T0 fixes, confirm signals flow: add DEBUG log in `strategy_agent.run()` when `raw_signals == 0` — dump the reason (no candles? regime filter? confidence floor?). Short-term instrumentation, not a behavior change.

---

## Tier 2 — Frontend Critical & High

### T2.1 — React key instability (CRITICAL)
- `web/src/components/ui/data-display/EventFeed.tsx:93` — composite key `${ev.id ?? i}-${ts}` collapses to index on missing id. Use a stable hash: `${ev.id ?? ev.ts}-${ev.agent}-${ev.event_type}`.
- `web/src/components/backtest/backtest-panel.tsx:70` — replace `key={i}` with `key={row.timestamp + row.symbol}`.

### T2.2 — Backtest panel has no user-visible error feedback
`web/src/components/backtest/backtest-panel.tsx:105–118` — errors are logged only. Surface via `toast` + inline error banner. Reset `jobId` on completion/failure.

### T2.3 — TradingChart stale-fetch races
`web/src/components/TradingChart.tsx:205–272` — fetch resolves after symbol switch → old data paints over new. Wrap in `AbortController`, abort in the effect cleanup.

### T2.4 — WebSocket missing `onerror` handler
`web/src/components/app/AppShellProvider.tsx:42–75` — only `onopen`/`onmessage`/`onclose`. Add `onerror` to log and trigger reconnect.

### T2.5 — Expensive render in LearningPage
`web/src/components/LearningPage.tsx:119–250` — `ConfBar` re-renders on every parent tick. Wrap in `React.memo` and memoize row computations with `useMemo`.

### T2.6 — Missing error/loading boundaries
`web/src/app/dashboard/` has no `error.tsx` or `loading.tsx`. Add minimal skeleton + error boundary at the dashboard root to avoid white screens.

---

## Tier 3 — API Layer (Next.js routes)

### T3.1 — Error response shape violations (CRITICAL, many routes)
All error responses must match `{ error: { code, message } }` per `.claude/rules/api-conventions.md`. Currently violated in ≥ 10 routes:
- `/api/broker/accounts` (20–21, 54)
- `/api/broker/trades` (21)
- `/api/trades` (37)
- `/api/signals` (20–21, 54)
- `/api/status` (15)
- `/api/events` (17)
- `/api/learning` (16)
- `/api/subscriptions` (16, 27, 38, 56)

Create a shared helper `web/src/lib/api-errors.ts`:
```ts
export const apiError = (code: string, message: string, status: number) =>
  NextResponse.json({ error: { code, message } }, { status });
```
Replace all ad-hoc error returns.

### T3.2 — Missing auth on protected routes (CRITICAL)
`/api/broker/accounts` hard-codes `userId = undefined`. Require session via NextAuth helper before read/write. Audit the other 29 routes the same way.

### T3.3 — Stack / internal error leaks
`/api/broker/trades:21` and `/api/candles:42` return raw upstream body. Log server-side, return the shared `apiError("UPSTREAM_ERROR", "Broker service unavailable", 502)`.

### T3.4 — Missing input validation (HIGH)
Install/verify Zod, add schemas for POST/PUT routes:
- `/api/broker/accounts` (POST body)
- `/api/signals` (POST body, including enum `direction`)
- `/api/subscriptions` (POST/DELETE)
- `/api/backtest/run` (POST params)

Return 400 with `apiError("VALIDATION_ERROR", ...)` on schema failure.

### T3.5 — Performance
- `/api/analytics:29–35` — loads ALL closed trades, filters in-process. Add `limit` + cursor pagination to DB helper.
- `/api/candles` — add `Cache-Control: public, s-maxage=5, stale-while-revalidate=30`.
- `/api/backtest/run`, `/api/macro/snapshots`, `/api/signals` (POST) — add per-IP rate limiting (10 req/min is a safe default for the single-user dashboard).

### T3.6 — Status code corrections
- `/api/world:71` — 200 on Crucix failure → return 503.
- `/api/broker/accounts:54` — generic 500 → 503 when DB unreachable.

### T3.7 — Versioning (LOW, defer)
`/api/v1/` migration is a breaking change for the dashboard. Track as follow-up; do NOT migrate in this pass. Document the convention for new routes only.

### T3.8 — `dynamic = "force-dynamic"` missing
`/api/config:3` — add the directive to prevent stale cached responses.

---

## Critical Files

| File | Tier | Change |
|------|------|--------|
| `agents/guards.py:565` | T0.1 | Already applied — verify only |
| `broker/mt5_connector.py:566,693` | T0.2 | `for_close` param |
| `config/settings.py:268-269,792-793` | T0.3 | Defaults 20/1800 |
| `orchestrator/bot.py:619-625` | T0.3 | Clear stale fault counters |
| `agents/exposure_agent.py` | T1.1 | Narrow exception handlers |
| `broker/mt5_connector.py::close_partial` | T1.2 | Re-fetch volume in retry |
| `agents/execution_agent.py` | T1.3 | Exponential backoff |
| `orchestrator/bot.py::scan_agent` | T1.4 | Profile + batch |
| `agents/strategy_agent.py` | T1.5 | DEBUG instrumentation |
| `web/src/components/ui/data-display/EventFeed.tsx:93` | T2.1 | Stable key |
| `web/src/components/backtest/backtest-panel.tsx:70,105-118` | T2.1, T2.2 | Key + error UI |
| `web/src/components/TradingChart.tsx:205-272` | T2.3 | AbortController |
| `web/src/components/app/AppShellProvider.tsx:42-75` | T2.4 | onerror handler |
| `web/src/components/LearningPage.tsx:119-250` | T2.5 | Memoization |
| `web/src/app/dashboard/error.tsx`, `loading.tsx` | T2.6 | Create (new files) |
| `web/src/lib/api-errors.ts` | T3.1 | Create (new shared helper) |
| `web/src/app/api/**` (10+ routes) | T3.1–T3.8 | Error shape, auth, Zod, rate limit, cache |

---

## Existing Utilities to Reuse

- `utils/helpers.py::local_now`, `is_weekend`, `current_session` — already used for time logic
- `utils/telegram_bot.py::send_message` — surface critical failures to operator
- `database/db.py::load_symbol_faults` — already supports the needed read; only caller logic changes
- `web/src/hooks/use-data-table.ts` — reuse for any new table views
- SWR polling pattern — keep for all new data-fetching (no ad-hoc useEffect+fetch)

---

## Verification

### Tier 0
1. Restart bot → grep logs for `'DummySignal' object has no attribute 'metadata'` → 0 matches.
2. Manually open a test trade on TAN (or any symbol where `volume_min > FIXED_LOT_SIZE`), trigger force-close → confirm fill receipt, position gone from MT5.
3. Truncate `symbol_fault` rows where `disabled_until < now()` manually, restart, confirm bot does NOT auto-disable on first scan.
4. Watch first 3 scan cycles in logs: `raw_signals > 0` for at least one symbol.

### Tier 1
5. Run `pytest tests/agents/test_exposure_agent.py -q` after exception narrowing.
6. Simulate a broker 500 during `execution_agent` confirm → log shows 250 / 500 / 1000 ms spacing.
7. Attach `cProfile` for one scan → `scan_ms` p50 drops below 200ms.

### Tier 2
8. Open dashboard → Events tab → scroll rapidly, confirm no React "duplicate key" warnings in console.
9. Trigger a failing backtest (bad params) → toast appears, UI resets.
10. Switch symbol on chart 3x rapidly → only the latest symbol's candles render.
11. Disconnect network briefly → WS onerror fires, reconnect attempts visible in Network tab.
12. Profile LearningPage with React DevTools Profiler → ConfBar renders drop ≥ 80%.
13. Throw an error inside a dashboard route deliberately → `error.tsx` renders instead of white screen.

### Tier 3
14. `curl -i /api/broker/trades` with bad token → `{"error":{"code":"UNAUTHORIZED","message":"..."}}`, status 401.
15. POST `/api/signals` with invalid body → 400 `VALIDATION_ERROR` with field-level detail.
16. Hit `/api/backtest/run` 11 times in a minute → 11th returns 429 `RATE_LIMITED`.
17. `curl -I /api/candles?symbol=EURUSD` → header `Cache-Control: public, s-maxage=5, stale-while-revalidate=30`.
18. Stop DB, hit `/api/broker/accounts` → 503 with the canonical error shape.

---

## Out of Scope (explicit)

- `/api/v1/` migration (T3.7) — documented as a follow-up
- Supabase schema changes
- New strategies / ML retraining
- Telegram bot command additions