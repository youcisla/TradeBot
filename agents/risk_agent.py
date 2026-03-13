"""Risk Agent — validates every signal before execution.

Answers: *Is it safe?*

Implements (in order):
1. Drawdown circuit breaker
2. Duplicate signal guard
3. Correlation guard
4. News blackout
5. Live spread check
6. Max open trades
7. Position sizing
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Callable

from broker.connector import BrokerConnector
from config import settings
from config.symbols import pip_value
from filters.news_filter import NewsFilter
from models.signal import Signal
from models.trade import Trade
from utils import telegram_bot

logger = logging.getLogger(__name__)


class RiskAgent:
    """Central risk gate.  Every signal must pass ``validate()``."""

    def __init__(
        self,
        broker: BrokerConnector,
        get_open_trades: Callable[[], list[Trade]],
        news_filter: NewsFilter | None = None,
    ) -> None:
        self._broker = broker
        self._get_open_trades = get_open_trades  # fn() -> list[Trade]
        self._news = news_filter or NewsFilter()

        # Drawdown tracking
        self._day_start_equity: float = 0.0
        self._day_date: str = ""
        self._circuit_breaker_active = False
        self._circuit_breaker_until: datetime | None = None

    # ── public API ───────────────────────────────────────────────────────

    def validate(self, signal: Signal) -> bool:
        """Return True only if ALL risk checks pass."""
        try:
            return self._validate_inner(signal)
        except Exception:
            logger.exception("RiskAgent.validate crashed — rejecting signal")
            return False

    def calculate_position_size(self, signal: Signal) -> float:
        """Return lot size based on risk parameters."""
        balance = self._broker.get_balance()
        risk_amount = balance * settings.MAX_RISK_PER_TRADE
        sl_distance = abs(signal.entry_price - signal.stop_loss)
        if sl_distance == 0:
            return settings.MIN_LOT_SIZE
        pv = pip_value(signal.symbol)
        sl_pips = sl_distance / pv
        lot_size = risk_amount / (sl_pips * 10)  # simplified pip-value calc
        lot_size = max(settings.MIN_LOT_SIZE, round(lot_size, 2))

        # Apply confidence scaling
        if signal.confidence < settings.CONFIDENCE_REDUCED:
            lot_size = round(lot_size * 0.5, 2)
        elif signal.confidence < settings.CONFIDENCE_FULL:
            lot_size = round(lot_size * 0.7, 2)

        return max(settings.MIN_LOT_SIZE, lot_size)

    # ── internal checks (ordered fail-fast) ──────────────────────────────

    def _validate_inner(self, signal: Signal) -> bool:
        # 1. Drawdown circuit breaker
        if self._check_drawdown():
            logger.warning("RISK REJECT [DRAWDOWN]: circuit breaker active")
            return False

        open_trades = self._get_open_trades()

        # 2. Duplicate signal guard
        if self._check_duplicate(signal, open_trades):
            logger.warning(
                "RISK REJECT [DUPLICATE]: %s %s %s already open",
                signal.symbol, signal.direction, signal.strategy,
            )
            return False

        # 3. Correlation guard
        if self._check_correlation(signal, open_trades):
            logger.warning(
                "RISK REJECT [CORRELATION]: %s %s already open from another strategy",
                signal.symbol, signal.direction,
            )
            return False

        # 4. News blackout
        if self._news.is_blackout(signal.symbol):
            logger.warning("RISK REJECT [NEWS]: blackout for %s", signal.symbol)
            return False

        # 5. Live spread check
        spread_pips = signal.entry_snapshot.spread / pip_value(signal.symbol)
        if spread_pips > settings.MAX_SPREAD_PIPS:
            logger.warning(
                "RISK REJECT [SPREAD]: %.1f pips > max %.1f for %s",
                spread_pips, settings.MAX_SPREAD_PIPS, signal.symbol,
            )
            return False

        # 6. Max open trades
        if len(open_trades) >= settings.MAX_OPEN_TRADES:
            logger.warning(
                "RISK REJECT [MAX_TRADES]: %d open >= %d max",
                len(open_trades), settings.MAX_OPEN_TRADES,
            )
            return False

        # 7. Position size sanity
        lot_size = self.calculate_position_size(signal)
        if lot_size < settings.MIN_LOT_SIZE:
            logger.warning("RISK REJECT [LOT_SIZE]: calculated %.2f < min %.2f",
                           lot_size, settings.MIN_LOT_SIZE)
            return False

        logger.info("RISK APPROVED: %s %s %s (lot=%.2f)",
                     signal.symbol, signal.direction, signal.strategy, lot_size)
        return True

    # ── drawdown circuit breaker ─────────────────────────────────────────

    def _check_drawdown(self) -> bool:
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")

        # If breaker fired, check if cooldown has elapsed
        if self._circuit_breaker_active:
            if self._circuit_breaker_until and now < self._circuit_breaker_until:
                return True
            self._circuit_breaker_active = False
            self._circuit_breaker_until = None
            logger.info("Drawdown circuit breaker cooldown expired — trading resumed")

        # Reset day tracking at midnight UTC
        if today != self._day_date:
            self._day_date = today
            self._day_start_equity = self._broker.get_equity()
            logger.info("Drawdown tracker reset: start_equity=%.2f", self._day_start_equity)

        if self._day_start_equity <= 0:
            return False

        current_equity = self._broker.get_equity()
        drawdown = (self._day_start_equity - current_equity) / self._day_start_equity

        if drawdown >= settings.MAX_DAILY_LOSS:
            self._circuit_breaker_active = True
            self._circuit_breaker_until = now + timedelta(hours=settings.DRAWDOWN_COOLDOWN_HOURS)
            msg = (
                f"🚨 DRAWDOWN CIRCUIT BREAKER: lost {drawdown:.1%} today "
                f"(limit {settings.MAX_DAILY_LOSS:.1%}). "
                f"Trading halted until {self._circuit_breaker_until.isoformat()}"
            )
            logger.critical(msg)
            telegram_bot.send_message(msg)
            return True

        return False

    # ── duplicate guard ──────────────────────────────────────────────────

    @staticmethod
    def _check_duplicate(signal: Signal, open_trades: list[Trade]) -> bool:
        for t in open_trades:
            if (t.symbol == signal.symbol
                    and t.direction == signal.direction
                    and t.strategy == signal.strategy
                    and t.is_open()):
                return True
        return False

    # ── correlation guard ────────────────────────────────────────────────

    @staticmethod
    def _check_correlation(signal: Signal, open_trades: list[Trade]) -> bool:
        for t in open_trades:
            if (t.symbol == signal.symbol
                    and t.direction == signal.direction
                    and t.is_open()):
                return True
        return False
