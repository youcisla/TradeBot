# TradeBot — Complete Implementation Plan

**Version:** 2.0
**Date:** April 30, 2026
**Status:** Ready to execute

---

## How to read this document

This is the consolidated plan covering the structural rebuild, credential system, scoring architecture, broker-as-source-of-truth pattern, and the five improvements derived from the trading methodology document. It supersedes all previous plans.

Read sections in order. The early sections set constraints that the implementation phases assume. Skipping ahead to the phase tables without reading the architecture sections will not work — the phases reference architectural decisions made earlier.

Estimated total elapsed time: **8.5 to 10.5 weeks**. Roughly 28-32 working days of focused effort, plus 1-2 weeks of paper-trading validation.

---

## Section 1 — Realistic expectations (constraint envelope)

The plan is designed for survival and slow compounding, not for moonshot returns. The numbers below are the envelope inside which all design decisions are made. If these targets feel disappointing, this plan is not for you and you should know that before we start.

### Target performance for a working version of the rebuilt bot

| Metric | Target |
|---|---|
| Monthly return (typical month) | 1-3% net |
| Monthly return (best 10% of months) | 5-8% |
| Monthly return (worst 25% of months) | -5% to 0% |
| Maximum drawdown | < 10% of account |
| Risk per trade | 1% of account (hard cap, no exceptions) |
| Daily loss limit | 5% of account (auto-shutdown) |
| Win rate (target) | 45-55% |
| Average R-multiple | 1.5-2.0R per winning trade |
| Trades per day across all symbols | 5-15 |

### Three-account month-one projection

| Account size | Best case (10%) | Median | Worst case (25%) |
|---|---|---|---|
| €100  | €115-€125 | €98-€110 | €70-€90 |
| €500  | €560-€600 | €495-€540 | €400-€470 |
| €1000 | €1100-€1180 | €995-€1070 | €850-€950 |

### What this plan does NOT promise

- No "2x in a month." Mathematically requires +2.34% per day compounded, which is ~35× Renaissance Medallion's average performance.
- No "trading 700 symbols simultaneously." Plan focuses on 8-15 carefully chosen instruments with deep liquidity.
- No "scalping." Plan is built around H1/H4 swing-style ICT trading.
- No guaranteed profitability. The first month tells you "is the bot broken." 6-12 months of data are needed to assess edge with statistical confidence.

---

## Section 2 — Locked architectural decisions

The following decisions are made and not revisited during implementation unless explicitly opened.

| Decision | Choice |
|---|---|
| Credential storage | **Option B** — encrypted at rest with Argon2id-derived key, AES-256-GCM ciphertext |
| ML stack | **Delete all** — LightGBM, XGBoost, SHAP, GARCH, HMM, distillation pipeline |
| Replacement for ML | Multi-scorer post-hoc confidence aggregation + nightly ICT calibration loop |
| Symbol universe | 8-15 high-liquidity instruments (no exotic crosses, no low-volume futures) |
| Trading timeframes | H1 entry, H4 structure, D1 bias |
| Risk per trade | 1% of account, hard floor and ceiling |
| Minimum R:R | 1.8:1 (configurable, but no signal accepted below) |
| Target R:R | 2.5:1 |
| Session filter | Killzone-based (London open + NY open + London close), no Asian session for FX |
| Volume Profile | Used as scorer (HVN/LVN alignment), not signal generator |
| Twitter sentiment | Implemented as veto-only, defaulted off until calibrated |
| LLM features | All deleted (claude_agent, briefing_agent, hypothesis_agent, reflector) |
| Mock data | Removed — bot connects to broker or refuses to start |
| Source of truth for live state | Broker (not DB) — DB is the write-ahead log |
| Concurrency model | Threading for I/O (MT5 IPC, telegram, candle server), main loop synchronous |
| Frontend framework | Next.js (kept), but components consolidated and 3D libs removed |

---

## Section 3 — New project structure

### Target tree

```
tradebot/
│
├── main.py                           (~15 lines — entry only)
├── pyproject.toml                    (replaces requirements.txt + pytest.ini)
├── .env.example                      (documented env vars)
│
├── core/                             ← PURE LOGIC — no I/O, no DB, no broker
│   ├── domain/
│   │   ├── signal.py
│   │   ├── trade.py
│   │   ├── market_context.py
│   │   ├── confidence.py             (typed Confidence + ScorerResult)
│   │   └── execution_state.py        (typed FillResult, ExecutionDegraded)
│   │
│   ├── ict/
│   │   ├── detector.py               (was strategies/ict/setups.py)
│   │   ├── geometry.py               (order blocks, FVG, liquidity sweeps)
│   │   ├── htf_context.py            (HTF bias + alignment scoring)
│   │   └── confidence_calc.py        (ICT-specific initial confidence)
│   │
│   ├── risk/
│   │   ├── geometry_check.py         (entry/SL/TP geometry + RR floor)
│   │   ├── spread_check.py
│   │   ├── circuit_breakers.py       (drawdown, daily/monthly loss, consec failures)
│   │   ├── correlation.py
│   │   ├── session_filter.py         (NEW — killzone enforcement)
│   │   └── validator.py              (orchestrates the above)
│   │
│   ├── sizing/
│   │   ├── position_size.py          (with slippage buffer, hard risk-cap reject)
│   │   └── modes.py                  (balance_pct, fixed_lot, fixed_risk_amount)
│   │
│   ├── execution/
│   │   └── policy.py                 (post-fill validation, immediate-close on degraded)
│   │
│   └── scoring/
│       ├── scorer.py                 (parallel scorer dispatcher, < 200ms budget)
│       ├── volume_profile_scorer.py  (NEW — HVN/LVN alignment)
│       ├── crucix_scorer.py          (macro tier delta)
│       ├── twitter_scorer.py         (veto-only, opt-in)
│       ├── ict_calibration.py        (applies persisted weights)
│       └── outcome_recorder.py       (records realized R for nightly loop)
│
├── adapters/                         ← I/O — one folder per external system
│   │
│   ├── mt5/
│   │   ├── connector.py
│   │   ├── reconnect.py              (NEW — explicit liveness + reconnect)
│   │   ├── symbol_resolver.py
│   │   └── order_executor.py
│   │
│   ├── db/
│   │   ├── pool.py
│   │   ├── schema.py
│   │   ├── migrations/
│   │   ├── trades.py
│   │   ├── events.py
│   │   ├── learning.py
│   │   ├── credentials.py            (NEW — encrypted credential storage)
│   │   └── status.py
│   │
│   ├── crucix/
│   │   └── client.py
│   │
│   ├── twitter/                      ← NEW
│   │   ├── client.py                 (X API v2)
│   │   ├── filter.py                 (calendar + spike rules)
│   │   └── relevance.py
│   │
│   └── telegram/
│       ├── sender.py                 (queue + send, lazy matplotlib)
│       ├── commands.py
│       └── auth.py
│
├── orchestration/
│   ├── lifecycle.py                  (startup, shutdown, run — ~150 lines)
│   ├── wiring.py                     (DI: builds components, passes deps explicitly)
│   ├── pipeline.py                   (was iteration.py — scan→rank→execute)
│   ├── phases/
│   │   ├── scan.py
│   │   ├── rank.py
│   │   └── execute.py
│   ├── trade_monitor.py              (was trade_manager.py — monitoring only)
│   ├── reconciliation.py             (NEW — broker-vs-DB sync every 5min)
│   └── loop.py                       (the actual while-loop, time-corrected)
│
├── api/                              ← NEW — bot's HTTP API for the dashboard
│   ├── server.py                     (FastAPI app, replaces utils/candle_server.py)
│   ├── routes/
│   │   ├── auth.py                   (login, profile CRUD, switch, unlock)
│   │   ├── live_state.py             (broker passthrough)
│   │   ├── trades.py                 (history hybrid: broker + DB merge)
│   │   ├── candles.py
│   │   └── system.py                 (heartbeat, settings, agent_events)
│   └── websocket.py                  (replaces ws-server.js)
│
├── learning/
│   ├── ict_calibration_loop.py       (nightly background job)
│   └── ict_weight_store.py           (persisted weights, EWMA-smoothed)
│
├── config/
│   ├── settings.py                   (~300 lines, native Pydantic)
│   └── symbols.py
│
├── tests/
│   ├── core/                         (unit tests — no I/O)
│   ├── adapters/                     (integration tests with fakes)
│   ├── e2e/                          (recorded MT5 session replay)
│   └── conftest.py
│
└── web/                              (frontend, separate refactor)
    └── ...
```

### Hard layer rules (enforced by import-linter in CI)

1. `core/` cannot import from `adapters/`, `orchestration/`, `api/`, or `learning/`.
2. `adapters/` can only import from `core/domain` (the dataclasses) — never from `core/ict`, `core/risk`, etc.
3. `orchestration/` is the only place that knows about both `core/` and `adapters/`.
4. `api/` depends on `orchestration/` (for the running bot reference) and `core/domain`.
5. `learning/` depends on `core/domain` and `adapters/db` only.
6. **No file over 400 lines, including tests.**
7. No more "Agent" suffix in class names. Things are: detectors, validators, scorers, executors, repositories, clients.

### What gets deleted entirely

**Directories:**
- `nodes/` — confirmed dead (502 lines, no callers)
- `distillation/` — LightGBM/XGBoost training pipeline
- `regime/` — HMM regime detection

**Files:**
- `models/lgbm_ensemble.py`, `models/lgbm_price_model.py`, `models/lgbm_train_state.py`, `models/lgbm_train_state.json`, `models/garch_regime.py`
- `agents/learning_agent.py`, `agents/reflector.py`
- `agents/claude_agent.py`, `agents/briefing_agent.py`, `agents/hypothesis_agent.py`
- `agents/sniper_entry_guard.py`, `agents/ssrt_agent.py`, `agents/exposure_agent.py`, `agents/guards.py`
- `agents/hku_client.py`, `agents/hku_copy_trader.py`, `agents/hku_signal_adapter.py`
- `scripts/train_lgbm.py`, `scripts/train_lgbm_price.py`
- `utils/concept_drift_detector.py`, `utils/walk_forward_optimizer.py`, `utils/kalman_filter.py`, `utils/dynamic_position_sizer.py`, `utils/orchestration_profiler.py`, `utils/skill_manager.py`, `utils/tool_system.py`, `utils/mesh_bus.py`, `utils/symbol_event_tracker.py`, `utils/opportunity_lifecycle.py`, `utils/spread_monitor.py`, `utils/hedge_stripper.py`, `utils/memory.py`
- `tools/mcp_server.py`
- `web/ws-server.js` (folded into `api/websocket.py`)
- `backtesting/mock_broker.py` (no mocks)

**Net result:** ~16,000 LOC deleted. Backend goes from 41,333 → ~22-25k LOC.

### Dependencies (pyproject.toml)

**Removed:** `lightgbm`, `xgboost`, `shap`, `arch`, `hmmlearn`, `joblib`, `aiokafka`, `fastmcp`, `rank_bm25`, `openai`, `fredapi`, `yfinance`, `websocket-client`

**Kept:** `psycopg2-binary`, `cryptography`, `MetaTrader5`, `python-dotenv`, `tzdata`, `rich`, `bcrypt`, `pytest`, `numpy`, `pandas`, `sentry-sdk`, `matplotlib` (lazy-imported only)

**New:** `fastapi`, `uvicorn`, `httpx`, `websockets`, `argon2-cffi`, `import-linter` (dev only)

**Frontend removed:** `three`, `@react-three/drei`, `@react-three/fiber`, `@types/three`

---

## Section 4 — Credential architecture (Option B)

### Threat model

| Threat | Protected? | How |
|---|---|---|
| DB dump leaked alone | ✅ Yes | Encrypted password column requires user's dashboard password to decrypt |
| Bot machine stolen (powered off) | ✅ Yes | Same — encryption key not stored anywhere |
| Bot machine compromised at runtime (root access) | ❌ No | Decrypted password is in memory; no defense possible |
| User forgets dashboard password | ⚠️ Re-entry required | MT5 credentials become unrecoverable; user must re-enter |

### Design flow

```
User logs into dashboard with email + dashboard password
  ↓
Dashboard password is bcrypt-hashed for auth (existing)
                  → ALSO used to derive an encryption key via Argon2id
                  → derived key NEVER stored on disk — recomputed each login
  ↓
First-time setup: user enters MT5 account/password/server in UI
  ↓
Encrypted with derived key, stored in `broker_accounts` table:
  - id
  - user_id (FK)
  - account_number       (plaintext — non-sensitive identifier)
  - server               (plaintext — non-sensitive)
  - encrypted_password   (AES-256-GCM ciphertext + nonce + tag)
  - profile_label        (user-chosen: "Demo", "Live", "Test")
  - is_active            (which one the bot is currently using)
  - created_at, last_used_at
  ↓
On bot startup:
  - Bot reads broker_accounts where is_active=true
  - Bot CANNOT decrypt without the user's dashboard password
  - Bot enters WAITING_FOR_AUTH state, exposes /api/auth/unlock endpoint
  - User opens dashboard, dashboard sends derived key over HTTPS
  - Bot decrypts MT5 password in memory ONLY, calls mt5.login()
  - Decrypted password is held in memory for session, never written to disk
  ↓
On profile switch:
  - User selects different profile in UI
  - Dashboard POSTs to /api/auth/switch-profile with new profile id + dashboard pw
  - Bot disconnects current MT5 session, decrypts new credentials, mt5.login()
  - Old in-memory password is zeroed (best-effort in Python)
```

### API surface for the dashboard

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| POST | `/api/auth/login` | `{email, password}` | session cookie |
| POST | `/api/auth/logout` | — | 204 |
| GET | `/api/auth/profiles` | — | `[{id, label, account, server, is_active}, ...]` |
| POST | `/api/auth/profiles` | `{label, account, server, broker_password, dashboard_password}` | `{id}` |
| POST | `/api/auth/profiles/{id}/activate` | `{dashboard_password}` | 204 (decrypts, calls `mt5.login`) |
| POST | `/api/auth/profiles/{id}/delete` | `{dashboard_password}` | 204 |
| DELETE | `/api/auth/session` | — | kills bot's in-memory key |
| GET | `/api/auth/status` | — | `{connected: bool, profile: {...} \| null, state: "WAITING_FOR_AUTH"\|"CONNECTED"\|"DEGRADED"}` |

### Implementation skeleton

```python
# adapters/db/credentials.py

@dataclass(frozen=True)
class BrokerCredentials:
    account: str
    server: str
    password: str  # plaintext, in-memory only

class CredentialStore:
    def __init__(self, db: Database): ...

    def derive_key(self, dashboard_password: str, salt: bytes) -> bytes:
        """Argon2id KDF. Salt is per-user, stored alongside the bcrypt hash."""

    def store(
        self, user_id: int, label: str,
        account: str, server: str, password: str,
        derived_key: bytes,
    ) -> int:
        """Encrypt password with AES-256-GCM, persist."""

    def load(self, user_id: int, profile_id: int, derived_key: bytes) -> BrokerCredentials:
        """Fetch, decrypt, return. Caller must not log or persist the result."""

    def list_profiles(self, user_id: int) -> list[ProfileSummary]:
        """Returns labels + account numbers for UI display. NEVER returns passwords."""

    def set_active(self, user_id: int, profile_id: int) -> None: ...
```

### UI changes (frontend)

- New page: `/dashboard/profiles` — list/add/edit/delete/switch profiles
- Login page: detect "no profile active" state and prompt to create one after login
- Header indicator: shows current active profile + connection state, click to switch
- Settings page: warning banner — "If you forget your password, broker credentials become unrecoverable"

---

## Section 5 — Scoring system

### Architecture overview

```
ICT detector finds a setup
  ↓
ICT outputs initial confidence in [0, 100]
  (based on geometry quality: order block clarity, FVG fill ratio,
   HTF alignment, session timing)
  ↓
Pre-trade scoring round (synchronous, fast — total budget < 200ms):
  - Volume Profile scorer:    delta in [-15, +15]   (HVN/LVN alignment)
  - Crucix scorer:            delta in [-30, +30]   (macro tier)
  - Twitter scorer (opt-in):  veto boolean          (calendar + spike rules)
  - Risk validator:           hard checks (geometry, spread, RR, gates) — bool
  - Correlation gate:         lot multiplier in [0.0, 1.0]
  ↓
Combined confidence = ICT_initial + Σ(scorer_deltas), clamped to [0, 100]
If Twitter blocks         → trade rejected with reason
If risk gates fail        → trade rejected with reason
If combined < threshold   → trade rejected
  ↓
Trade executes. Lot size from sizing module (respects combined confidence).
Slippage buffer applied. Post-fill geometry check.
  ↓
Trade is now LIVE. Recorded:
  - Pre-trade context (all individual scores, market state)
  - signal_id linking back to original ICT detection
  ↓
Post-trade scoring round (async, background, NEVER blocks pipeline):
  - Each iteration, scorers MAY update score for active trades
  - If score deviates significantly from pre-trade,
    bot can (configurable, default OFF):
      • tighten SL
      • take partial profit
      • close trade
  - Default behavior: record only, do not act
  ↓
Trade closes (SL hit, TP hit, manual, etc.).
  ↓
Outcome feedback (daily background job, NOT in hot path):
  - Compare final R-multiple against pre-trade combined confidence
  - For each ICT setup type, accumulate (predicted_confidence, realized_R) pairs
  - Once per day, recompute calibration: which setup types are over/under-confident?
  - Adjust ICT_initial confidence weights with EWMA smoothing (30-day half-life)
  ↓
Updated weights reloaded by live bot at end-of-day rollover
```

### Honest caveats baked into the design

| Concern | Mitigation in design |
|---|---|
| Daily calibration on small samples is noisy | EWMA with 30-day half-life; weights move slowly |
| Post-hoc score-driven trade closes can lock in temporary losses | Default behavior: record only, do not act on post-hoc score changes |
| Twitter sentiment is mostly noise | Veto-only, behind opt-in flag, restricted to calendar events + extreme spikes |
| Multi-scorer = hand-crafted ML in disguise | Acknowledged. Each scorer's weight is calibrated empirically, not assumed |
| Failure of any scorer should not block trading | Scorers wrapped in `try/except`; failure → return neutral delta of 0, log warning |

### Realistic improvement claim

Calibration improves confidence *calibration* over time, not raw return. After 6 months of data:
- Slightly higher win rate on high-confidence setups (fewer false positives)
- Slightly tighter SL placement (better-calibrated stops)
- Better symbol/setup type rejection of consistently underperforming combinations

Estimated effect: 5-15% improvement in risk-adjusted return after 6 months. Not "10x".

---

## Section 6 — Broker as source of truth

### Three layers, each with a clear owner

| Data | Source of truth | Why |
|---|---|---|
| Account balance, equity, margin | **Broker** | Real-time. DB always lags. |
| Currently open positions | **Broker** | Includes manual trades user placed in MT5 directly. |
| Closed trades, last 30 days | **Broker for fills + DB for metadata** | Broker has authoritative fill prices; DB has signal_id, confidence, reason. |
| Closed trades, older than 30 days | **DB** | Broker history APIs typically limited to ~30-90 days. |
| Bot decisions, rejections, agent events | **DB** | Broker doesn't know about these. |
| Strategy state, ICT weights, calibration | **DB** | Internal state. |
| Pending signals, scoring scratchpad | **In-memory only** | Ephemeral. |

### Dashboard request flow

**Old (broken):**
```
Dashboard → /api/trades   → DB query   → returns possibly-stale data
Dashboard → /api/status   → DB query   → returns possibly-stale balance
```

**New:**
```
Dashboard → /api/live-state → Bot's API → broker.get_account_info()
                                        → broker.get_open_positions()
                                        → returns fresh data + freshness_ms timestamp

Dashboard → /api/trades?include=closed
              → for last 30 days: broker.get_history()
                                  LEFT JOIN db.trades on (broker_ticket = bot_ticket)
                                  for metadata
              → for older: pure DB query
              → returns hybrid result with `source: "broker"|"db"|"merged"` per row
```

### Reconciliation job (every 5 minutes)

```python
async def reconcile_open_positions(broker, db):
    broker_open = {p.ticket for p in broker.get_open_positions()}
    db_open     = {t.broker_ticket for t in db.get_open_trades()}

    only_in_broker = broker_open - db_open
    only_in_db     = db_open - broker_open

    if only_in_broker:
        # User opened a manual trade in MT5, OR our DB missed an open event
        for ticket in only_in_broker:
            log_warning(f"Position {ticket} in broker but not in DB — adopting as untracked")
            db.insert_untracked_trade(ticket)  # tracked but no signal_id, no confidence

    if only_in_db:
        # DB thinks trade is open but broker says closed — we missed a close event
        for ticket in only_in_db:
            log_critical(f"Position {ticket} in DB but not in broker — querying history to close")
            broker_history = broker.get_history_for_ticket(ticket)
            if broker_history:
                db.mark_trade_closed(ticket, broker_history)
            else:
                db.mark_trade_orphan(ticket)  # never resolved
```

### Frontend treatment of stale data

- Dashboard always shows live broker state when reachable
- During broker disconnection: show last known state with red "DISCONNECTED" banner + age of data
- Never silently show stale data without indicator
- "Last sync: 12s ago" display next to balance/equity values

---

## Section 7 — Document-derived improvements

These five additions came from the trading methodology document review. Each is bounded in scope and folds into existing phases.

### 7.1 Volume Profile scorer

**File:** `core/scoring/volume_profile_scorer.py`

**Logic:**
- Computes session Volume Profile from M15 candles already pulled by ICT detector (no new data feed)
- Identifies HVN (high-volume nodes), LVN (low-volume gaps), POC (point of control) for the trading session
- Returns delta in [-15, +15] based on entry zone alignment:
  - BUY at HVN support → +10
  - BUY at LVN gap → -10 (price tends to move through gaps quickly, not bounce)
  - SELL at HVN resistance → +10
  - SELL near POC → +5
  - No clear structure within ±0.5% of entry → 0

**Cost:** Negligible. Histogram bin computation in numpy, < 5ms per signal.

**Phase:** 5

**Effort:** 1 day

---

### 7.2 Hard R:R floor and target

**File:** `core/risk/geometry_check.py`

**Settings:**
- `MIN_RR_RATIO`: default 1.8 (hard reject below this)
- `TARGET_RR_RATIO`: default 2.5 (confidence penalty -10 if below)

**Logic:**
```python
def check_rr(signal: Signal) -> tuple[bool, float, str | None]:
    """Returns (passes_floor, rr_value, reject_reason)."""
    if signal.direction == "BUY":
        risk = signal.entry_price - signal.stop_loss
        reward = signal.take_profit_1 - signal.entry_price
    else:
        risk = signal.stop_loss - signal.entry_price
        reward = signal.entry_price - signal.take_profit_1

    if risk <= 0:
        return False, 0.0, "INVALID_RISK"

    rr = reward / risk
    if rr < settings.MIN_RR_RATIO:
        return False, rr, f"RR_BELOW_FLOOR: {rr:.2f} < {settings.MIN_RR_RATIO}"
    return True, rr, None
```

If `rr < TARGET_RR_RATIO` but passes floor → confidence penalty applied in scorer combiner (-10).

**Phase:** 4

**Effort:** 2 hours

---

### 7.3 HTF alignment as quantified hard gate

**File:** `core/ict/htf_context.py`

**Score components (0-100 total):**

| Component | Weight |
|---|---|
| HTF bias direction matches signal direction (D1 + H4 agree) | 60 |
| HTF structure (BoS/ChoCH on H4) supports direction | 25 |
| HTF candle context (last H4 candle confluent with entry zone) | 15 |

**Settings:**
- `HTF_ALIGNMENT_MIN_SCORE`: default 70 (signals below this rejected)

**Effect:** Will reject a substantial portion of current signals. This is intentional — ICT discipline requires waiting for full alignment.

**Phase:** 4

**Effort:** 4 hours

---

### 7.4 Killzone-based session filter

**File:** `core/risk/session_filter.py`

**Default windows (UTC):**

| Killzone | Hours UTC | Applies to |
|---|---|---|
| London Open | 07:00 – 10:00 | FX majors, gold, EU indices |
| New York Open | 13:00 – 16:00 | FX majors, US indices, oil |
| London Close (NY overlap) | 15:00 – 16:00 | FX majors, gold |
| Crypto (24/7) | always | BTC/ETH only |

**Settings:**
- `KILLZONE_FILTER_ENABLED`: default true
- `KILLZONE_WINDOWS_FX`: default `["07:00-10:00", "13:00-16:00", "15:00-16:00"]`
- `KILLZONE_WINDOWS_INDICES`: default `["13:00-16:00"]` (NY only)
- `KILLZONE_WINDOWS_CRYPTO`: default `["00:00-23:59"]`

**Outside killzone:** signal rejected at risk validation step with reason `OUTSIDE_KILLZONE`. Logged but not noisy.

**Phase:** 4

**Effort:** 3 hours

---

### 7.5 Slippage-aware execution + post-fill geometry recheck

**This solves the "trades opened and closed at the same time losing money" bug.**

**Settings:**
- `EXPECTED_EXECUTION_LATENCY_MS`: default 100
- `SLIPPAGE_BUFFER_PIPS_FX`: default 2
- `SLIPPAGE_BUFFER_PIPS_CRYPTO`: default 5
- `SLIPPAGE_BUFFER_PIPS_EXOTIC`: default 10
- `MAX_ENTRY_SLIPPAGE_PIPS`: default 5 (close immediately if exceeded)

**Sizing change:**
```python
# core/sizing/position_size.py
def compute_position_size(signal, broker, account):
    slippage_pips = get_slippage_buffer(signal.symbol)
    pip_size = broker.get_pip_size(signal.symbol)
    
    # Use a worst-case entry price for sizing math
    if signal.direction == "BUY":
        worst_entry = signal.entry_price + (slippage_pips * pip_size)
    else:
        worst_entry = signal.entry_price - (slippage_pips * pip_size)
    
    # Risk-per-lot uses worst-case entry, not signal entry
    sl_distance = abs(worst_entry - signal.stop_loss)
    # ... rest of sizing math
```

**Post-fill check:**
```python
# core/execution/policy.py
def validate_post_fill(signal, fill_result, broker) -> ExecutionState:
    actual_entry = fill_result.fill_price
    expected_entry = signal.entry_price
    pip_size = broker.get_pip_size(signal.symbol)
    slippage_pips = abs(actual_entry - expected_entry) / pip_size
    
    if slippage_pips > settings.MAX_ENTRY_SLIPPAGE_PIPS:
        return ExecutionState.degraded(
            reason=f"SLIPPAGE_EXCEEDED: {slippage_pips:.1f} > {settings.MAX_ENTRY_SLIPPAGE_PIPS}",
            action="CLOSE_IMMEDIATELY",
        )
    
    # Recompute RR with actual fill
    new_rr = compute_rr(actual_entry, signal.stop_loss, signal.take_profit_1, signal.direction)
    if new_rr < settings.MIN_RR_RATIO:
        return ExecutionState.degraded(
            reason=f"POST_FILL_RR_DEGRADED: {new_rr:.2f} < {settings.MIN_RR_RATIO}",
            action="CLOSE_IMMEDIATELY",
        )
    
    return ExecutionState.ok()
```

**Phase:** 0 (P0 bug fix) + 4 (proper integration)

**Effort:** 1 day

---

## Section 8 — Implementation phases (consolidated)

### Phase 0 — Stop the bleeding (do FIRST, before any restructure work)

These are the bugs from the original roast plus the slippage fix. Fix these before touching architecture, because the bot is losing money on these right now.

| # | Action | File | Effort |
|---|---|---|---|
| 0.1 | Fix `_write_symbols_manifest` agent-leak (240-line block accidentally inside manifest writer; agents re-initialized on tool-system callback, telegram polling thread duplicated, candle server port-bind crash) | `orchestrator/bot.py` | 2h |
| 0.2 | Add MT5 `reconnect()` + liveness probe; wire into IPC backoff path | `broker/mt5_connector.py` | 4h |
| 0.3 | Fix `NEXT_PUBLIC_WS_URL` access (currently `window.NEXT_PUBLIC_WS_URL` which is never set; should be `process.env.NEXT_PUBLIC_WS_URL`) | `web/src/components/app/AppShellProvider.tsx` | 1h |
| 0.4 | Position-size floor + hard risk cap (currently `round(lot, 2)` can silently exceed `MAX_RISK_PER_TRADE`); reject signal if floored size violates risk caps | `agents/risk_agent.py` | 3h |
| 0.5 | Daily/drawdown gate fixes (60s cache window, denominator using current vs start-of-day equity, persist `_day_start_equity` across restarts) | `agents/risk_agent.py` | 4h |
| 0.6 | **Slippage-aware execution + post-fill recheck** (solves "opened and closed immediately" bug) | `agents/execution_agent.py` + `agents/risk_agent.py` | 1d |

**Phase 0 total: ~3 days.**

---

### Phase 1 — Foundations for the new structure

| # | Action | Effort |
|---|---|---|
| 1.1 | Create empty new directory tree (`core/`, `adapters/`, `orchestration/`, `api/`, `learning/`) | 30min |
| 1.2 | Write `pyproject.toml`, replace `requirements.txt` + `pytest.ini`. Remove all deleted deps. Add `fastapi`, `uvicorn`, `httpx`, `websockets`, `argon2-cffi`, `import-linter`. | 1h |
| 1.3 | Add CI import-linter config to enforce layer rules | 1h |
| 1.4 | Move `models/signal.py`, `trade.py` → `core/domain/`. Add `market_context.py`, `confidence.py`, `execution_state.py`. Add shim for old import paths. | 2h |
| 1.5 | Native Pydantic settings rewrite (`config/settings.py`: 1413 → ~300 lines, no `_build_settings`, use `env_nested_delimiter="__"`) | 1d |

**Phase 1 total: ~12h.**

---

### Phase 2 — Auth and credential architecture

| # | Action | Effort |
|---|---|---|
| 2.1 | Schema migration: `broker_accounts` table with encrypted password, profile labels, is_active flag, salt | 2h |
| 2.2 | `adapters/db/credentials.py` with Argon2id KDF + AES-256-GCM (replaces `utils/crypto.py`'s AES-CBC + HMAC) | 4h |
| 2.3 | `api/server.py` with FastAPI scaffolding | 3h |
| 2.4 | `api/routes/auth.py` — login, profile CRUD, profile switch, unlock | 6h |
| 2.5 | Bot startup mode `WAITING_FOR_AUTH` until first unlock | 3h |
| 2.6 | Frontend: account profiles page, login flow, profile switcher in shell, "forgot password = re-enter MT5 creds" warning | 1.5d |
| 2.7 | Migration script: existing hardcoded credentials → encrypted profile (one-time, requires user to log in once and re-enter) | 3h |

**Phase 2 total: ~3-4 days.**

---

### Phase 3 — Adapter extraction

| # | Action | Effort |
|---|---|---|
| 3.1 | Move `broker/mt5_connector.py` → `adapters/mt5/{connector,reconnect,symbol_resolver,order_executor}.py`. Each <400 lines. | 1d |
| 3.2 | Move `database/*.py` → `adapters/db/*.py`, slim repos, fix per-call `SELECT 1` validation overhead (validate only on stale, or drop validation and rely on `_put_conn` close-on-error) | 1d |
| 3.3 | Move `filters/crucix_client.py` + `agents/crucix_agent.py` → `adapters/crucix/client.py`. Pure scoring interface returning [-30, +30] delta. | 4h |
| 3.4 | Move `utils/telegram_bot.py` (1,122 lines!) → `adapters/telegram/{sender,commands,auth}.py`. Extract embedded LLM agents (delete). Lazy-import matplotlib. | 1d |
| 3.5 | Replace `utils/candle_server.py` with `api/server.py` + `api/routes/candles.py`. Single HTTP server, FastAPI-based. | 1d |
| 3.6 | Move `web/ws-server.js` logic into `api/websocket.py`. Bot owns its WebSocket. Frontend connects to `ws://localhost:8000/ws/events`. | 4h |

**Phase 3 total: ~5 days.**

---

### Phase 4 — Core (the pure logic)

| # | Action | Effort |
|---|---|---|
| 4.1 | Decompose `agents/risk_agent.py` (1394 lines) → `core/risk/{geometry_check,spread_check,circuit_breakers,correlation,session_filter,validator}.py`. Each <300 lines. **Includes `MIN_RR_RATIO` enforcement (item 7.2).** **Includes `session_filter.py` killzone (item 7.4).** | 1.5d |
| 4.2 | Decompose `agents/execution_agent.py` → `adapters/mt5/order_executor.py` (pure I/O) + `core/execution/policy.py` (decision logic, **post-fill validation from item 7.5**) | 1d |
| 4.3 | Move ICT logic: `strategies/ict/`, `strategies/ict_strategy.py`, `models/ict_models.py` → `core/ict/{detector,geometry,htf_context,confidence_calc}.py`. **Includes HTF alignment hard gate (item 7.3).** | 1.5d |
| 4.4 | Sizing: extract from risk_agent → `core/sizing/{position_size,modes}.py`. **Includes slippage buffer (item 7.5).** Remove Kelly mode (insufficient sample size). | 4h |
| 4.5 | Delete `models/lgbm_*.py`, `models/garch_regime.py`, `regime/hmm_regime.py`, `distillation/`, `nodes/`, all related tests, removed dependencies | 2h |

**Phase 4 total: ~5 days.**

---

### Phase 5 — Scoring system

| # | Action | Effort |
|---|---|---|
| 5.1 | Define `core/domain/confidence.py`: typed `Confidence`, `ScorerResult`, `ScoringContext` | 2h |
| 5.2 | `core/scoring/scorer.py`: synchronous combiner with parallel scorer dispatch, < 200ms total budget. Failure of any scorer = neutral 0 delta + log. | 1d |
| 5.3 | Adapt Crucix as a `Scorer`: returns delta in [-30, +30] based on macro tier | 4h |
| 5.4 | **Volume Profile scorer (item 7.1)**: `core/scoring/volume_profile_scorer.py` | 1d |
| 5.5 | `adapters/twitter/{client,filter,relevance}.py`: X API v2 client, calendar+spike-only veto rules. `TWITTER_ENABLED=false` default — opt-in. | 2d |
| 5.6 | `core/scoring/outcome_recorder.py`: at trade close, record (pre_trade_context, realized_R) tuples to DB | 4h |
| 5.7 | `learning/ict_calibration_loop.py`: nightly job, EWMA smoothing (30-day half-life), persists weights | 1d |
| 5.8 | `learning/ict_weight_store.py`: load weights at startup, fall back to defaults on missing/corrupt | 4h |
| 5.9 | `core/ict/confidence_calc.py`: applies weights to detector features → ICT_initial confidence | 4h |
| 5.10 | Wire post-hoc scoring into iteration pipeline (record-only mode by default) | 4h |

**Phase 5 total: ~6 days.** Twitter is the bulk; defer to later if needed and save 2 days.

---

### Phase 6 — Live state passthrough and reconciliation

| # | Action | Effort |
|---|---|---|
| 6.1 | `api/routes/live_state.py`: equity, positions, balance from broker | 4h |
| 6.2 | `api/routes/trades.py`: hybrid broker+DB merge for history (last 30 days from broker, older from DB) | 4h |
| 6.3 | `orchestration/reconciliation.py`: every 5min job, detect drift, log/adopt/orphan | 4h |
| 6.4 | Frontend: replace DB-backed status calls with live-state calls; add freshness indicator + disconnected banner | 1d |

**Phase 6 total: ~2 days.**

---

### Phase 7 — Cleanup and frontend

| # | Action | Effort |
|---|---|---|
| 7.1 | Make `matplotlib` lazy in `adapters/telegram/sender.py` (move import inside function) | 30min |
| 7.2 | Remove `three`, `@react-three/drei`, `@react-three/fiber`, `@types/three` from `web/package.json` | 1h |
| 7.3 | Frontend: SWR centralization completion (database, settings pages routed through `lib/swr.ts`) | 4h |
| 7.4 | Frontend: audit `web/src/lib/db.ts` (30K), move client-component DB queries into API routes | 1d |
| 7.5 | Add `MEM_DEBUG` mode that logs RSS per iteration; run for one paper-trading day; validate structural changes hit RAM goal | 4h |
| 7.6 | Decompose remaining oversized files: `orchestrator/iteration_phases.py` → `orchestration/phases/{scan,rank,execute}.py`; final pass to enforce <400 lines/file rule | 1d |

**Phase 7 total: ~3 days.**

---

### Phase 8 — Validation before live money

| # | Action | Effort |
|---|---|---|
| 8.1 | End-to-end test against recorded MT5 session — confirm scoring pipeline, calibration loop, reconciliation all work | 2d |
| 8.2 | 1-2 weeks paper trading on demo account with real broker connection | 1-2 weeks elapsed |
| 8.3 | Compare paper-trading PnL against backtested PnL for the same period; if diverge >30%, find execution gap | 1d |
| 8.4 | Decide go/no-go on small live size (€100-€500 max) | — |

**Phase 8 total: ~1-2 weeks elapsed time, ~3-4 days of focused work.**

---

### Total summary

| Phase | Working days | Calendar |
|---|---|---|
| 0 — Bug fixes | 3 | Week 1 |
| 1 — Foundations | 1.5 | Week 1-2 |
| 2 — Auth | 3-4 | Week 2-3 |
| 3 — Adapters | 5 | Week 3-4 |
| 4 — Core logic | 5 | Week 4-6 |
| 5 — Scoring | 6 | Week 6-7 |
| 6 — Live state | 2 | Week 7-8 |
| 7 — Cleanup | 3 | Week 8 |
| 8 — Validation | 3-4 + 1-2wk paper | Week 8-10 |
| **Total** | **~32 working days** | **~8.5-10.5 weeks** |

This is part-time-friendly pacing. Full-time it compresses to 5-6 weeks. Either way, plan for ~10 weeks calendar before live trading at any meaningful size.

---

## Section 9 — Settings catalog (new and changed)

| Setting | Default | Notes |
|---|---|---|
| `MIN_RR_RATIO` | 1.8 | Hard reject below |
| `TARGET_RR_RATIO` | 2.5 | Confidence penalty if below |
| `HTF_ALIGNMENT_MIN_SCORE` | 70 | Hard gate |
| `KILLZONE_FILTER_ENABLED` | true | Set false to disable session filtering |
| `KILLZONE_WINDOWS_FX` | `"07:00-10:00,13:00-16:00,15:00-16:00"` | UTC |
| `KILLZONE_WINDOWS_INDICES` | `"13:00-16:00"` | UTC, NY only |
| `KILLZONE_WINDOWS_CRYPTO` | `"00:00-23:59"` | 24/7 |
| `EXPECTED_EXECUTION_LATENCY_MS` | 100 | Documented assumption |
| `SLIPPAGE_BUFFER_PIPS_FX` | 2 | Used in sizing |
| `SLIPPAGE_BUFFER_PIPS_CRYPTO` | 5 | Used in sizing |
| `SLIPPAGE_BUFFER_PIPS_EXOTIC` | 10 | Used in sizing |
| `MAX_ENTRY_SLIPPAGE_PIPS` | 5 | Close-immediately threshold |
| `MAX_RISK_PER_TRADE` | 0.01 | Hard cap, no exception |
| `MAX_DAILY_LOSS` | 0.05 | Auto-shutdown trigger |
| `MAX_OPEN_TRADES` | 5 | Concurrent across all symbols |
| `VOLUME_PROFILE_ENABLED` | true | Item 7.1 scorer |
| `TWITTER_ENABLED` | false | Opt-in only |
| `MEM_DEBUG` | false | Diagnostic mode |
| `LGBM_ENSEMBLE_ENABLED` | DELETED | Setting removed with ML stack |
| `KALMAN_ENABLED` | DELETED | Setting removed |
| `GARCH_ENABLED` | DELETED | Setting removed |

---

## Section 10 — Hard rules going forward

These are non-negotiable and enforced via CI.

1. **No file over 400 lines.** Including tests. CI fails the build.
2. **`core/` cannot import I/O.** Enforced by import-linter.
3. **No mock data.** No `mock_broker.py`, no fake feeds. Bot connects to a real broker or refuses to start.
4. **No hardcoded credentials.** Anywhere. Found in code review = blocker.
5. **No `Agent` suffix in class names.** Use: `Detector`, `Validator`, `Scorer`, `Executor`, `Repository`, `Client`.
6. **All external calls in `adapters/`.** Period. No `requests.get()` in `core/`.
7. **Position size never exceeds risk caps.** Even on rounding. Even in fixed_lot mode. Reject with reason instead.
8. **Scorers cannot block the pipeline.** Failure → neutral delta + log. Total scoring budget < 200ms enforced.
9. **Live state from broker, history from DB.** Never the inverse.
10. **Every signal rejection has a logged reason.** No silent `return False`.

---

## Section 11 — File move map (selective)

Full mapping created during Phase 3 implementation. Selected key migrations:

| Old | New |
|---|---|
| `main.py` | `main.py` (kept, slimmer) |
| `orchestrator/bot.py` | `orchestration/{lifecycle,wiring,loop}.py` |
| `orchestrator/iteration.py` | `orchestration/pipeline.py` |
| `orchestrator/iteration_phases.py` | `orchestration/phases/{scan,rank,execute}.py` |
| `agents/risk_agent.py` | `core/risk/{geometry_check,spread_check,circuit_breakers,correlation,session_filter,validator}.py` |
| `agents/execution_agent.py` | `adapters/mt5/order_executor.py` + `core/execution/policy.py` |
| `agents/strategy_agent.py` | `core/ict/detector.py` + `core/scoring/scorer.py` |
| `agents/market_agent.py` | DELETED (folded into pipeline phases) |
| `agents/analysis_agent.py` | DELETED (folded into ICT detector) |
| `agents/trade_manager.py` | `orchestration/trade_monitor.py` |
| `agents/learning_agent.py` | `learning/ict_calibration_loop.py` + `core/scoring/outcome_recorder.py` |
| `agents/crucix_agent.py` | `adapters/crucix/client.py` + `core/scoring/crucix_scorer.py` |
| `broker/mt5_connector.py` | `adapters/mt5/{connector,reconnect,symbol_resolver}.py` |
| `database/db.py` | `adapters/db/{pool,schema}.py` |
| `database/*_repo.py` | `adapters/db/*.py` |
| `utils/telegram_bot.py` | `adapters/telegram/{sender,commands,auth}.py` |
| `utils/candle_server.py` | `api/server.py` + `api/routes/candles.py` |
| `web/ws-server.js` | `api/websocket.py` (folded into Python) |
| `strategies/ict/*` | `core/ict/{detector,geometry,htf_context,confidence_calc}.py` |
| `models/signal.py`, `trade.py` | `core/domain/{signal,trade}.py` |
| `config/settings.py` | `config/settings.py` (rewritten, ~300 lines) |
| `config/symbols.py` | `config/symbols.py` (kept) |

---

## Section 12 — Validation checklist (Phase 8)

Before any live money beyond €500, all must be true:

- [ ] All Phase 0 bug fixes verified by reproduction tests
- [ ] Bot runs for 7 consecutive days on demo without crashes, restarts, or memory growth >100MB
- [ ] Reconciliation job runs every 5min for 7 days; zero unresolved drift incidents
- [ ] Credential unlock flow tested end-to-end: cold start → user logs in → MT5 connects → trades execute
- [ ] Profile switch tested: switch from Demo to Test profile mid-session, no leaked positions
- [ ] Killzone filter rejects 100% of signals outside windows (verified with manipulated time)
- [ ] R:R floor rejects 100% of synthetic signals with rr < MIN_RR_RATIO (test fixtures)
- [ ] Slippage post-fill check closes synthetic trades when fill_price > entry + buffer (test fixtures)
- [ ] Position size never exceeds 1.05× MAX_RISK_PER_TRADE × balance (1000 random signal fuzz test)
- [ ] Daily loss circuit breaker triggers within 5s of crossing threshold (no cache delay)
- [ ] Bot restart mid-losing-day does NOT reset `_day_start_equity` (persistence test)
- [ ] WebSocket connects on dashboard load (no 3-second retry loop visible in console)
- [ ] Live state endpoint returns broker data with `freshness_ms < 1000` under normal conditions
- [ ] Disconnect indicator shows within 10s of broker disconnection
- [ ] All scorers return neutral 0 delta when their backing service is unavailable (no pipeline blocks)
- [ ] Memory profile per-iteration: RSS stable within ±50MB over 24-hour run
- [ ] No `'use client'` component fetches DB directly (all go through API routes)
- [ ] Frontend bundle size: `next build` reports total < 500KB gzipped (after three.js removal)
- [ ] Paper trading P&L within 30% of backtest P&L for same period
- [ ] No file in repo exceeds 400 lines (CI check passes)
- [ ] `import-linter` CI check passes (no `core/` importing `adapters/`)

---

## Section 13 — Risk acknowledgments

**The following risks remain even after the rebuild:**

1. **The strategy may not have edge.** ICT/SMC has a structured framework but no academic proof of edge. The first 6 months of live data will tell us. If edge isn't there, no amount of architecture rescues it.

2. **Variance is variance.** Even with everything correct, a single losing month is normal. Three losing months in a row is also normal. Twelve losing months in a row would tell us the strategy lacks edge.

3. **Broker risk.** PuPrime is an offshore broker. There is non-trivial counterparty risk. Consider keeping no more than 2-3x your monthly trading need in the account at any time.

4. **Black swan events.** No bot survives a 2008-style flash crash with leveraged positions. Daily-loss circuit breaker provides partial protection but not complete.

5. **Self-update risk.** The ICT calibration loop will adjust weights over time. If a temporary regime shift causes weights to over-fit recent noise, the next regime shift will hurt. Mitigation: EWMA half-life of 30 days dampens this. Monitoring: alert if weight changes exceed ±15% in a single update.

6. **Operational risk.** A bug in the scoring pipeline could systematically reject good trades or accept bad ones. Mitigation: every rejection logged with reason; periodic sanity check that rejection rate stays in expected range (60-80% of generated signals).

---

## Section 14 — What's NOT in this plan (and why)

**Things explicitly out of scope:**

- High-frequency / millisecond-latency trading (retail can't compete; documented in methodology survey)
- Trading universe expansion beyond 8-15 symbols (correlation traps + signal quality decline)
- Pure scalping on M1/M5 (transaction cost destroys edge at retail spreads)
- LLM-based trade decisions (latency, non-determinism, cost — covered in earlier discussions)
- Social copy trading / signal services
- Mobile app (web dashboard is responsive, mobile app is a separate project)
- Multi-broker simultaneous trading (one MT5 session at a time per profile)
- Backtest engine improvements (existing engine is "good enough" for now; revisit only if needed for validation)
- HKU marketplace integration (not in your future flow per discussions)
- MCP server (`tools/mcp_server.py` — deleted)

If you want any of these added later, they slot in as Phase 9+ after the core bot is proven stable.

---

## Document version control

- **v2.0 (April 30, 2026):** Initial consolidated plan. Replaces all prior partial plans.

When changes are made, increment version and add a dated entry. Do not rewrite history.