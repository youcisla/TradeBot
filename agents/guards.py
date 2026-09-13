"""GuardPipeline — pre-execution safety layer.

Seven independent guards that must ALL pass before a trade is sent to the
broker.  Each guard has a reason string for logging / audit.

Usage::

    from agents.guards import GuardPipeline
    pipeline = GuardPipeline(broker=broker, db=db)
    ok, reason = pipeline.check(signal, open_trades)
    if not ok:
        logger.warning("Trade blocked by guard: %s", reason)
        return None

Guards run in order; first failure short-circuits the rest.
"""

from __future__ import annotations

import logging
import pathlib
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Sequence

from config import settings
from utils.helpers import current_session, is_weekend

# Project root — one level up from the agents/ directory
_ROOT = pathlib.Path(__file__).resolve().parent.parent

if TYPE_CHECKING:
    from broker.connector import BrokerConnector
    from adapters.db.db import Database
    from models.signal import Signal
    from models.trade import Trade

logger = logging.getLogger(__name__)


# ── Abstract base ─────────────────────────────────────────────────────────────

class Guard(ABC):
    """Base class for a single guard check."""

    @abstractmethod
    def check(
        self,
        signal: "Signal",
        open_trades: list["Trade"],
        broker: "BrokerConnector",
    ) -> tuple[bool, str]:
        """Return (passed, reason).  reason is empty string on pass."""


# ── Individual Guards ─────────────────────────────────────────────────────────

class MaxPositionSizeGuard(Guard):
    """Block orders where lot_size exceeds a hard cap."""

    def __init__(self, max_lots: float = 2.0) -> None:
        self._max = max_lots

    def check(self, signal, open_trades, broker):
        lot = getattr(signal, "lot_size_override", None)
        # Only enforce the cap when the signal carries an explicit lot override.
        # The final lot is computed by calculate_position_size *after* guard
        # checks run, so we cannot validate it here.  settings.MAX_LOT_SIZE is a
        # user-configured ceiling (e.g. 50 for large accounts) — comparing it
        # against this guard's hard cap is incorrect and would always block.
        if lot is not None and lot > self._max:
            return False, (
                f"MaxPositionSizeGuard: signal.lot_size_override={lot} "
                f"exceeds hard cap {self._max}"
            )
        return True, ""


class SymbolWhitelistGuard(Guard):
    """Block trading on any symbol not in the whitelist."""

    _DEFAULT_WHITELIST = {
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
        "NZDUSD", "USDCHF", "XAUUSD", "GBPJPY", "EURJPY",
        "AUDJPY", "EURAUD", "GBPAUD", "EURGBP", "USOIL",
        "US500", "US30", "USTEC", "GER40",
        # Crypto
        "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
        "ADAUSD", "DOTUSD", "LTCUSD", "EOSUSD", "XLMUSD",
        "TRXUSD",
        # Exotic USD pairs
        "USDHKD", "USDSGD", "USDCNH",
        # Additional approved symbols (also in PRIORITY_SYMBOLS scan list)
        "GAUUSD", "XAGUSD",
    }

    # Broker-specific suffixes, most specific first.  PU Prime (this broker)
    # appends ".p" (EURUSD.p) and ".crp" (XAUUSD.crp) — verified against the
    # account; other feeds use ".s", "m", ".r" or "_r" for renamed contracts.
    _SUFFIXES: tuple[str, ...] = (".crp", ".p", ".s", ".r", "_r", "m")

    def __init__(self, allowed: set[str] | None = None) -> None:
        self._allowed = allowed or self._DEFAULT_WHITELIST

    @classmethod
    def _strip_suffix(cls, sym: str) -> str:
        """Return *sym* without its broker suffix, or unchanged if none match.

        ``str.rstrip`` cannot be used here: it takes a *character set*, so it
        strips any trailing run of those characters and silently fails on
        suffixes whose letters are outside the set — which is why suffixed
        symbols were never recognised and got blocked by the whitelist.
        """
        s = sym.upper()
        for suffix in cls._SUFFIXES:
            if s.endswith(suffix.upper()) and len(s) > len(suffix):
                return s[: -len(suffix)]
        return s

    def check(self, signal, open_trades, broker):
        sym = signal.symbol.upper()
        base = self._strip_suffix(sym)
        if sym not in self._allowed and base not in self._allowed:
            return False, f"SymbolWhitelistGuard: '{sym}' not in whitelist"
        return True, ""


class CooldownGuard(Guard):
    """Enforce a minimum gap between consecutive trades (any direction)."""

    def __init__(self, min_seconds_between_trades: float = 300) -> None:
        self._min_s = min_seconds_between_trades

    def check(self, signal, open_trades, broker):
        if not open_trades:
            return True, ""
        now = datetime.now(UTC)
        for trade in open_trades:
            opened = getattr(trade, "opened_at", None) or getattr(trade, "open_time", None)
            if opened is None:
                continue
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=UTC)
            age = (now - opened).total_seconds()
            if age < self._min_s:
                return False, (
                    f"CooldownGuard: last trade opened {age:.0f}s ago "
                    f"(min {self._min_s}s)"
                )
        return True, ""


class DailyDrawdownGuard(Guard):
    """Block new trades when daily loss exceeds a configurable cap.

    Supports two calculation modes:
    - "equity" (default, backwards-compatible): measures open drawdown as
      (daily_starting_balance + realised_pnl - equity) / daily_starting_balance.
      The starting balance and cumulative realised P&L are persisted to disk
      so the cap correctly tracks closed trades, not just open positions.
    - "ratios": legacy mode — measures (balance - equity) / balance without
      considering realised P&L (excluded from this guard's scope).
    """

    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,
        calculation_mode: str = "equity",
    ) -> None:
        self._max_pct = max_daily_loss_pct
        self._mode = calculation_mode
        self._state_file = str(_ROOT / "data" / "daily_drawdown_state.json")

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        import json, pathlib
        path = pathlib.Path(self._state_file)
        if not path.exists():
            return {"date": "", "starting_balance": 0.0, "realised_pnl": 0.0}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {"date": "", "starting_balance": 0.0, "realised_pnl": 0.0}

    def _save_state(self, date_str: str, starting_balance: float, realised_pnl: float) -> None:
        import json, pathlib
        path = pathlib.Path(self._state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump(
                    {"date": date_str, "starting_balance": starting_balance, "realised_pnl": realised_pnl},
                    f,
                )
        except Exception:
            pass

    def _ensure_today_state(self, broker) -> tuple[float, float]:
        """Return (starting_balance, realised_pnl) for today, initialising if needed."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        state = self._load_state()
        if state.get("date") != today:
            # New day — reset; use current balance as the starting point
            try:
                starting = broker.get_balance()
            except Exception:
                starting = 0.0
            self._save_state(today, starting, 0.0)
            return starting, 0.0
        return state.get("starting_balance", 0.0), state.get("realised_pnl", 0.0)

    def record_closed_trade_pnl(self, pnl: float) -> None:
        """Call this from trade_manager when any trade closes (non-scalp or scalp)."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        state = self._load_state()
        if state.get("date") != today:
            return  # Will be re-initialised on next check
        current = state.get("realised_pnl", 0.0)
        self._save_state(today, state.get("starting_balance", 0.0), current + pnl)

    # ── Guard.check ───────────────────────────────────────────────────────────

    def check(self, signal, open_trades, broker):
        if self._mode == "ratios":
            # Legacy ratios-based check
            try:
                balance = broker.get_balance()
                equity = broker.get_equity()
                if balance <= 0:
                    return True, ""
                drawdown = (balance - equity) / balance
                if drawdown >= self._max_pct:
                    return False, (
                        f"DailyDrawdownGuard[ratios]: drawdown {drawdown:.1%} "
                        f">= limit {self._max_pct:.1%}"
                    )
            except Exception as exc:
                logger.warning("DailyDrawdownGuard: broker call failed (%s) — skipping", exc)
            return True, ""

        # "equity" mode — closed-trade P&L aware
        try:
            equity = broker.get_equity()
            starting_balance, realised_pnl = self._ensure_today_state(broker)
            if starting_balance <= 0:
                return True, ""
            # Equity already reflects realised P&L: the balance moves when a
            # trade closes, and equity = balance + floating.  So the day's loss
            # is simply the drop from the day's starting balance.  Adding
            # realised_pnl back (as this used to) cancelled the term and left
            # only floating loss, so a day of closed losses reported ~0.
            equity_loss = starting_balance - equity
            # Tracked realised P&L is an independent floor in case the broker
            # balance is stale; take whichever measure is worse.
            net_loss = max(equity_loss, -realised_pnl)
            loss_pct = net_loss / starting_balance
            if loss_pct >= self._max_pct:
                return False, (
                    f"DailyDrawdownGuard[equity]: net loss {loss_pct:.1%} "
                    f"(balance={starting_balance:.2f}, realised={realised_pnl:.2f}, "
                    f"equity={equity:.2f}) >= limit {self._max_pct:.1%}"
                )
        except Exception as exc:
            logger.warning("DailyDrawdownGuard[equity]: broker call failed (%s) — skipping", exc)
        return True, ""


class EquityDrawdownGuard(Guard):
    """Block or reduce sizing when equity drawdown from peak exceeds thresholds.

    Tracks the running peak equity.  When current equity falls below peak by more
    than a threshold, the guard returns a graduated response:

    - "reduce"  : current drawdown >= reduce_threshold  → lot size halved
    - "block"   : current drawdown >= block_threshold   → trade rejected

    This protects against equity-curve degradation without hard-stopping on every
    drawdown spike — partial sizing continues until the situation worsens.

    Parameters
    ----------
    reduce_threshold : float
        Drawdown fraction (e.g. 0.10 = 10%) at which to return "reduce" action.
    block_threshold : float
        Drawdown fraction at which to return "block" action.
    """

    def __init__(
        self,
        reduce_threshold: float = 0.10,
        block_threshold: float = 0.20,
    ) -> None:
        self._reduce = reduce_threshold
        self._block = block_threshold
        self._peak_file = str(_ROOT / "data" / "equity_peak.json")

    # ── Peak equity persistence ───────────────────────────────────────────────

    def _load_peak(self) -> float:
        import json
        path = pathlib.Path(self._peak_file)
        if not path.exists():
            return 0.0
        try:
            with open(path) as f:
                return json.load(f).get("peak", 0.0)
        except Exception:
            return 0.0

    def _save_peak(self, peak: float) -> None:
        import json
        path = pathlib.Path(self._peak_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump({"peak": peak}, f)
        except Exception:
            pass

    def record_closed_trade_pnl(self, pnl: float) -> None:
        """Called when a trade closes — no action needed for peak tracking.

        Peak equity is updated from broker.get_equity() on each guard check
        so this method is a no-op to satisfy the interface.
        """

    # ── Guard.check ────────────────────────────────────────────────────────────

    def check(self, signal, open_trades, broker):
        try:
            equity = broker.get_equity()
            if equity <= 0:
                return True, ""

            peak = self._load_peak()
            if equity > peak:
                self._save_peak(equity)
                peak = equity

            drawdown = (peak - equity) / peak if peak > 0 else 0.0

            if drawdown >= self._block:
                return False, (
                    f"EquityDrawdownGuard: drawdown {drawdown:.1%} "
                    f"(peak={peak:.2f}, equity={equity:.2f}) >= block {self._block:.1%}"
                )
            if drawdown >= self._reduce:
                # Inject a hint into signal metadata so risk_agent halves the lot
                signal.metadata["lot_multiplier"] = 0.5
                logger.debug(
                    "EquityDrawdownGuard: drawdown %.1f%% — signalling lot reduction",
                    drawdown,
                )

        except Exception as exc:
            logger.warning("EquityDrawdownGuard: broker call failed (%s) — skipping", exc)
        return True, ""


class MarketHoursGuard(Guard):
    """Avoid placing trades during low-liquidity hours (server time UTC).

    Crypto (BTCUSD, ETHUSD, etc.) is 24/7 — only the hourly quiet-hours
    filter applies; weekends are never blocked for crypto.
    """

    _CRYPTO: frozenset[str] = frozenset({
        "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
        "ADAUSD", "DOTUSD", "LTCUSD", "EOSUSD", "XLMUSD",
        "TRXUSD", "AVAXUSD", "DOGEUSD", "LINKUSD", "BCHUSD",
    })

    def __init__(self, avoid_hours: list[int] | None = None) -> None:
        # Default: avoid Fri 21:00–23:59 and Sat/Sun entirely (forex)
        self._avoid = set(avoid_hours) if avoid_hours is not None else {21, 22, 23}

    def check(self, signal, open_trades, broker):
        now = datetime.now(UTC)
        # Strip trailing suffixes (e.g. BTCUSDm → BTCUSD)
        sym = signal.symbol.upper().rstrip("m.r_")
        is_crypto = sym in self._CRYPTO

        # Crypto is 24/7 — only hourly quiet-hours filter applies
        # One shared definition of the forex weekend (Fri 22:00 -> Sun 22:00
        # UTC).  The previous weekday()>=5 test blocked the whole of Sunday,
        # including the two hours after the FX week reopens.
        if not is_crypto and is_weekend(now):
            return False, "MarketHoursGuard: market closed (weekend)"
        if now.hour in self._avoid:
            return False, (
                f"MarketHoursGuard: low-liquidity hour UTC {now.hour:02d}:xx blocked"
            )
        return True, ""


class VolatilityGuard(Guard):
    """Skip new entries when VIX is above a threshold (from CrucixAgent context)."""

    def __init__(self, max_vix: float = 40.0) -> None:
        self._max_vix = max_vix

    def check(self, signal, open_trades, broker):
        vix = getattr(signal, "macro_vix", 0.0)
        if vix == 0.0:
            return True, ""  # VIX unknown — don't block
        if vix > self._max_vix:
            return False, (
                f"VolatilityGuard: VIX={vix:.1f} > threshold {self._max_vix}"
            )
        return True, ""


class FeedFreshnessGuard(Guard):
    """Reject signals whose most recent candle timestamp is stale (>N seconds)."""

    def __init__(self, max_staleness_seconds: float = 120) -> None:
        self._max_stale = max_staleness_seconds

    def check(self, signal, open_trades, broker):
        candle_ts = getattr(signal, "candle_timestamp", None)
        if candle_ts is None:
            return True, ""  # No timestamp attached — can't validate
        now = datetime.now(UTC)
        if candle_ts.tzinfo is None:
            candle_ts = candle_ts.replace(tzinfo=UTC)
        age = (now - candle_ts).total_seconds()
        if age > self._max_stale:
            return False, (
                f"FeedFreshnessGuard: candle is {age:.0f}s old "
                f"(max {self._max_stale}s)"
            )
        return True, ""


# ── Volume filter guard ───────────────────────────────────────────────────────

class VolumeFilterGuard(Guard):
    """Block signals when the current bar's volume is abnormally low.

    Volume is measured against a rolling average of the last N M5 candles.
    Low volume bars often produce unreliable breakout / momentum signals,
    especially in scalp and momentum strategies.

    Freqtrade VolumePairList inspiration — adapted for pre-execution guard use.
    """

    def __init__(
        self,
        lookback_candles: int = 20,
        min_volume_pct: float = 0.50,
        timeframe: str = "M5",
    ) -> None:
        self._lookback = lookback_candles
        self._min_pct = min_volume_pct
        self._tf = timeframe

    def check(self, signal, open_trades, broker) -> tuple[bool, str]:
        try:
            candles = broker.get_candles(signal.symbol, self._tf, self._lookback + 1)
        except Exception as exc:
            logger.warning("VolumeFilterGuard: broker.get_candles failed (%s) — skipping", exc)
            return True, ""

        if len(candles) < self._lookback:
            return True, ""  # Not enough data — can't validate

        # Most recent candle = current bar
        current_vol = candles[-1].tick_volume if hasattr(candles[-1], "tick_volume") else 0.0
        if current_vol <= 0:
            # Volume data unavailable (OTC forex / demo broker) — skip guard silently
            return True, ""

        # Rolling average of all but the current bar (to avoid look-ahead bias)
        hist_vols = [c.tick_volume if hasattr(c, "tick_volume") else 0.0 for c in candles[:-1]]
        avg_vol = sum(hist_vols) / len(hist_vols)
        if avg_vol <= 0:
            return True, ""

        ratio = current_vol / avg_vol
        if ratio < self._min_pct:
            return False, (
                f"VolumeFilterGuard: volume {current_vol:.0f} < {self._min_pct:.0%} "
                f"of avg {avg_vol:.0f} ({ratio:.1%}) on {signal.symbol}"
            )
        return True, ""



# ── Pipeline ──────────────────────────────────────────────────────────────────

class GuardPipeline:
    """Run all guards in sequence.  Returns (True, "") if ALL pass."""

    GUARDS: list[Guard] = [
        MaxPositionSizeGuard(max_lots=2.0),
        SymbolWhitelistGuard(),
        CooldownGuard(min_seconds_between_trades=300),
        DailyDrawdownGuard(
            max_daily_loss_pct=float(getattr(settings, "MAX_DAILY_LOSS", 0.05) or 0.05)
        ),
        EquityDrawdownGuard(reduce_threshold=0.10, block_threshold=0.20),
        MarketHoursGuard(),
        VolatilityGuard(max_vix=40.0),
        FeedFreshnessGuard(max_staleness_seconds=120),
        VolumeFilterGuard(),
    ]

    def __init__(
        self,
        broker: "BrokerConnector",
        db: "Database | None" = None,
        guards: list[Guard] | None = None,
    ) -> None:
        self._broker = broker
        self._db = db
        self._guards: list[Guard] = guards if guards is not None else list(self.GUARDS)

    def check(
        self,
        signal: "Signal",
        open_trades: list["Trade"] | None = None,
    ) -> tuple[bool, str]:
        """Run every guard.  Returns (passed, blocking_reason).

        A reason string of "" means all guards passed.
        """
        trades = open_trades or []
        for guard in self._guards:
            guard_name = type(guard).__name__
            try:
                passed, reason = guard.check(signal, trades, self._broker)
            except Exception as exc:
                # Fail CLOSED.  A guard that crashed is a gate that can no
                # longer be trusted; continuing would trade with that protection
                # silently absent, which is worse than not trading at all.
                reason = f"{guard_name} crashed: {exc}"
                logger.error(
                    "GuardPipeline: %s raised (%s) — BLOCKING (fail-closed)",
                    guard_name,
                    exc,
                )
                self._emit(
                    "error",
                    f"Guard {guard_name} crashed — trade blocked (fail-closed)",
                    {"guard": guard_name, "error": str(exc)},
                )
                return False, reason
            if not passed:
                logger.info("GuardPipeline BLOCKED: %s", reason)
                self._emit("info", f"Trade blocked: {reason}", {"reason": reason})
                return False, reason
        return True, ""

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            try:
                self._db.log_agent_event("guards", level, msg, data)
            except Exception:
                pass

    def record_closed_trade_pnl(self, pnl: float) -> None:
        """Called by trade_manager when any trade closes.

        Updates DailyDrawdownGuard's realised-P&L tracker.
        """
        dd_guard: DailyDrawdownGuard | None = next(
            (g for g in self._guards if isinstance(g, DailyDrawdownGuard)),
            None,
        )
        if dd_guard is not None:
            dd_guard.record_closed_trade_pnl(pnl)

    # ── Status snapshot for dashboard ─────────────────────────────────────────

    def get_status(
        self,
        broker: "BrokerConnector",
        open_trades: list["Trade"] | None = None,
    ) -> list[dict]:
        """Return current status of all guards as a list of dicts.

        Used by HeartbeatManager to persist guard state to the DB so the
        dashboard can display it via GET /api/risk without running a guard
        check against a live signal.
        """
        import uuid
        from dataclasses import dataclass, field

        @dataclass
        class DummySignal:
            symbol: str = "EURUSD"
            direction: str = "buy"
            lot_size_override: float | None = None
            macro_vix: float = 0.0
            candle_timestamp: datetime | None = None
            metadata: dict = field(default_factory=dict)

        signal = DummySignal()
        trades = open_trades or []
        results: list[dict] = []

        for guard in self._guards:
            gname = type(guard).__name__.replace("Guard", "")
            try:
                passed, reason = guard.check(signal, trades, broker)
            except Exception as exc:
                results.append({
                    "name": gname,
                    "status": "warn",
                    "threshold": "?",
                    "current": f"error: {exc}",
                })
                continue

            # Derive current/threshold human-readable strings per guard type
            if isinstance(guard, DailyDrawdownGuard):
                threshold = f"{guard._max_pct:.0%}"
                try:
                    equity = broker.get_equity()
                    starting, realised = guard._ensure_today_state(broker)
                    if starting > 0:
                        loss_pct = max(0.0, -(starting + realised - equity) / starting)
                        current = f"{loss_pct:.1%}"
                        status = "fail" if loss_pct >= guard._max_pct else "pass"
                    else:
                        current = "—"
                        status = "pass"
                except Exception:
                    current = "—"
                    status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, EquityDrawdownGuard):
                threshold = f"{guard._block:.0%}"
                try:
                    equity = broker.get_equity()
                    peak = guard._load_peak()
                    if peak > 0:
                        dd_pct = max(0.0, (peak - equity) / peak)
                        current = f"{dd_pct:.1%}"
                        if dd_pct >= guard._block:
                            status = "fail"
                        elif dd_pct >= guard._reduce:
                            status = "warn"
                        else:
                            status = "pass"
                    else:
                        current = "0.0%"
                        status = "pass"
                except Exception:
                    current = "—"
                    status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, CooldownGuard):
                threshold = f"{guard._min_s:.0f}s"
                if trades:
                    now = datetime.now(UTC)
                    ages = []
                    for t in trades:
                        opened = getattr(t, "opened_at", None) or getattr(t, "open_time", None)
                        if opened:
                            if opened.tzinfo is None:
                                opened = opened.replace(tzinfo=UTC)
                            ages.append((now - opened).total_seconds())
                    youngest = min(ages) if ages else 0.0
                    current = f"{youngest:.0f}s"
                    status = "warn" if youngest < guard._min_s else "pass"
                else:
                    current = "idle"
                    status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, VolatilityGuard):
                threshold = f"VIX>{guard._max_vix}"
                vix = getattr(signal, "macro_vix", 0.0)
                current = f"VIX {vix:.1f}" if vix > 0 else "VIX —"
                status = "fail" if vix > guard._max_vix else "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, MaxPositionSizeGuard):
                threshold = f"{guard._max:.1f} lots"
                current = "—"
                status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, SymbolWhitelistGuard):
                threshold = "whitelist"
                current = "—"
                status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, MarketHoursGuard):
                threshold = "active session"
                now = datetime.now(UTC)
                sess = current_session(now)
                # Check if we're in an avoided hour
                in_avoid = now.hour in guard._avoid
                status = "warn" if in_avoid else "pass"
                current = sess.capitalize()
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, FeedFreshnessGuard):
                threshold = f"{guard._max_stale:.0f}s stale"
                # Can't determine without a real signal candle — report last known
                current = "—"
                status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            elif isinstance(guard, VolumeFilterGuard):
                threshold = f"vol > {guard._min_pct:.0%}"
                current = "—"
                status = "pass"
                results.append({"name": gname, "status": status,
                                "threshold": threshold, "current": current})

            else:
                results.append({
                    "name": gname,
                    "status": "pass" if passed else "fail",
                    "threshold": "—",
                    "current": reason if reason else "ok",
                })

        return results
