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

# Project root — one level up from the agents/ directory
_ROOT = pathlib.Path(__file__).resolve().parent.parent

if TYPE_CHECKING:
    from broker.connector import BrokerConnector
    from database.db import Database
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
        "US500", "US30", "USTEC", "GER40", "BTCUSD",
    }

    def __init__(self, allowed: set[str] | None = None) -> None:
        self._allowed = allowed or self._DEFAULT_WHITELIST

    def check(self, signal, open_trades, broker):
        sym = signal.symbol.upper()
        # Also accept a trailing suffix like XAUUSD.r / EURUSDm
        base = sym.rstrip("m.r_").upper()
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
            # Net floating loss = starting_balance + realised_pnl - equity
            # (realised_pnl is negative when losing, positive when winning)
            net_loss = starting_balance + realised_pnl - equity
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
        if not is_crypto and now.weekday() >= 5:
            return False, f"MarketHoursGuard: market closed (weekend)"
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
            return False, (
                f"VolumeFilterGuard: current volume is 0 for {signal.symbol}"
            )

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


# ── Scalp-specific guard ────────────────────────────────────────────────────────

class ScalpExposureGuard(Guard):
    """Block scalp signals that exceed scalp-specific exposure limits.

    Tracks:
    - Concurrent scalp positions (max SCALP_MAX_CONCURRENT)
    - Scalp trades per rolling hour (max SCALP_MAX_TRADES_PER_HOUR)
    - Scalp daily realised P&L (max SCALP_DAILY_LOSS_LIMIT — blocks if loss exceeded)

    Persists scalp daily P&L to a JSON file so it survives bot restarts within the same day.
    """

    def __init__(
        self,
        max_lots: float | None = None,
        max_concurrent: int | None = None,
        max_per_hour: int | None = None,
        daily_loss_limit: float | None = None,
    ) -> None:
        self._max_lot = (
            max_lots
            if max_lots is not None
            else getattr(settings, "SCALP_MAX_LOT_SIZE", 0.50)
        )
        self._max_concurrent = (
            max_concurrent
            if max_concurrent is not None
            else getattr(settings, "SCALP_MAX_CONCURRENT", 2)
        )
        self._max_per_hour = (
            max_per_hour
            if max_per_hour is not None
            else getattr(settings, "SCALP_MAX_TRADES_PER_HOUR", 4)
        )
        self._daily_loss_limit = (
            daily_loss_limit
            if daily_loss_limit is not None
            else getattr(settings, "SCALP_DAILY_LOSS_LIMIT", 0.02)
        )
        # In-memory rolling window of scalp trade timestamps (UTC)
        self._scalp_timestamps: list[datetime] = []
        # Persistent daily loss state (written to disk)
        self._state_file = str(_ROOT / "data" / "scalp_guard_state.json")

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        import json, pathlib, os
        path = pathlib.Path(self._state_file)
        if not path.exists():
            return {"date": "", "realised_pnl": 0.0}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {"date": "", "realised_pnl": 0.0}

    def _save_state(self, date_str: str, realised_pnl: float) -> None:
        import json, pathlib
        path = pathlib.Path(self._state_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w") as f:
                json.dump({"date": date_str, "realised_pnl": realised_pnl}, f)
        except Exception:
            pass

    def _realised_scalp_pnl(self) -> float:
        state = self._load_state()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if state.get("date") != today:
            self._save_state(today, 0.0)
            return 0.0
        return state.get("realised_pnl", 0.0)

    def _record_scalp_close(self, pnl: float) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        current = self._realised_scalp_pnl()
        self._save_state(today, current + pnl)

    # ── Guard.check ────────────────────────────────────────────────────────────

    def check(self, signal, open_trades, broker) -> tuple[bool, str]:
        is_scalp = getattr(signal, "strategy", "") == "scalp_m5"
        if not is_scalp:
            return True, ""

        # 1. Concurrent scalp positions
        scalp_open = sum(
            1
            for t in (open_trades or [])
            if getattr(t, "strategy", "") == "scalp_m5"
        )
        if scalp_open >= self._max_concurrent:
            return False, (
                f"ScalpExposureGuard: {scalp_open} scalp positions open "
                f"(max {self._max_concurrent})"
            )

        # 2. Rolling hourly rate
        now = datetime.now(UTC)
        cutoff = datetime.timestamp(
            datetime.fromtimestamp(now.timestamp() - 3600, tz=UTC)
        )
        # Prune old timestamps
        self._scalp_timestamps = [
            ts for ts in self._scalp_timestamps if datetime.timestamp(ts) > cutoff
        ]
        if len(self._scalp_timestamps) >= self._max_per_hour:
            return False, (
                f"ScalpExposureGuard: {len(self._scalp_timestamps)} scalp trades "
                f"in the last hour (max {self._max_per_hour})"
            )

        # 3. Daily scalp realised loss cap
        scalp_pnl = self._realised_scalp_pnl()
        if scalp_pnl <= -self._daily_loss_limit:
            return False, (
                f"ScalpExposureGuard: scalp daily loss {scalp_pnl:.4f} "
                f"exceeds limit {self._daily_loss_limit:.4f}"
            )

        return True, ""

    def record_scalp_trade_closed(self, pnl: float) -> None:
        """Call this from trade_manager when a scalp trade closes."""
        self._record_scalp_close(pnl)
        # Also remove from rolling window (approximate)
        if self._scalp_timestamps:
            self._scalp_timestamps = self._scalp_timestamps[:-1]


# ── Pipeline ──────────────────────────────────────────────────────────────────

class GuardPipeline:
    """Run all guards in sequence.  Returns (True, "") if ALL pass."""

    GUARDS: list[Guard] = [
        MaxPositionSizeGuard(max_lots=2.0),
        SymbolWhitelistGuard(),
        CooldownGuard(min_seconds_between_trades=300),
        DailyDrawdownGuard(max_daily_loss_pct=0.05),
        MarketHoursGuard(),
        VolatilityGuard(max_vix=40.0),
        FeedFreshnessGuard(max_staleness_seconds=120),
        VolumeFilterGuard(),
        ScalpExposureGuard(),
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
        # ScalpExposureGuard reference for close-event recording
        self._scalp_guard: ScalpExposureGuard | None = next(
            (g for g in self._guards if isinstance(g, ScalpExposureGuard)),
            None,
        )

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
            try:
                passed, reason = guard.check(signal, trades, self._broker)
            except Exception as exc:
                # Guard crash → log and skip (fail-open so trading continues)
                guard_name = type(guard).__name__
                logger.warning(
                    "GuardPipeline: %s raised unexpectedly (%s) — skipping guard",
                    guard_name,
                    exc,
                )
                self._emit(
                    "warn",
                    f"Guard {guard_name} crashed — skipped (fail-open)",
                    {"guard": guard_name, "error": str(exc)},
                )
                continue
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

    def record_scalp_close(self, pnl: float) -> None:
        """Called by trade_manager when a scalp_m5 trade closes."""
        if self._scalp_guard is not None:
            self._scalp_guard.record_scalp_trade_closed(pnl)

    def record_closed_trade_pnl(self, pnl: float) -> None:
        """Called by trade_manager when any non-scalp trade closes.

        Updates DailyDrawdownGuard's realised-P&L tracker.
        """
        dd_guard: DailyDrawdownGuard | None = next(
            (g for g in self._guards if isinstance(g, DailyDrawdownGuard)),
            None,
        )
        if dd_guard is not None:
            dd_guard.record_closed_trade_pnl(pnl)
