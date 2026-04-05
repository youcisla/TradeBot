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
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Sequence

from config import settings

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
        # We can't know the final lot here, but we guard the maximum allowed
        max_allowed = getattr(settings, "MAX_LOT_SIZE", self._max)
        if max_allowed > self._max:
            return False, (
                f"MaxPositionSizeGuard: settings.MAX_LOT_SIZE={max_allowed} "
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
    """Block new trades when today's realised loss exceeds a daily cap."""

    def __init__(self, max_daily_loss_pct: float = 0.05) -> None:
        self._max_pct = max_daily_loss_pct

    def check(self, signal, open_trades, broker):
        try:
            balance = broker.get_balance()
            equity = broker.get_equity()
            if balance <= 0:
                return True, ""
            drawdown = (balance - equity) / balance
            if drawdown >= self._max_pct:
                return False, (
                    f"DailyDrawdownGuard: current drawdown {drawdown:.1%} "
                    f">= limit {self._max_pct:.1%}"
                )
        except Exception as exc:
            logger.warning("DailyDrawdownGuard: broker call failed (%s) — skipping", exc)
        return True, ""


class MarketHoursGuard(Guard):
    """Avoid placing trades during low-liquidity hours (server time UTC)."""

    def __init__(self, avoid_hours: list[int] | None = None) -> None:
        # Default: avoid Fri 21:00–23:59 and Sat/Sun entirely
        self._avoid = set(avoid_hours) if avoid_hours is not None else {21, 22, 23}

    def check(self, signal, open_trades, broker):
        now = datetime.now(UTC)
        # Block Saturday and Sunday
        if now.weekday() >= 5:
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
