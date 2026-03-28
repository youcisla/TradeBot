"""Risk Agent — validates every signal before execution.

Answers: *Is it safe?*

Implements (in order):
1.  Drawdown circuit breaker
1b. Crucix macro blackout
2.  Duplicate signal guard
3.  Correlation guard
4.  Max open trades
5.  Live spread check (per-asset-class)
7.  Position sizing
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Callable

from broker.connector import BrokerConnector
from config import settings
from config.symbols import pip_value, contract_size, asset_class
from models.signal import Signal
from models.trade import Trade
from utils import telegram_bot

if TYPE_CHECKING:
    from agents.crucix_agent import CrucixAgent
    from database.db import Database

logger = logging.getLogger(__name__)


# ── Cross-pair correlation table ─────────────────────────────────────────
# Maps each symbol to a set of symbols that are *positively* correlated
# with it in the same direction (e.g. all USD-short vs USD-long pairs).
# Holding a signal's symbol AND any of these in the SAME direction means
# overlapping exposure — the second trade is blocked.
_CORRELATED_PAIRS: dict[str, frozenset[str]] = {
    # USD-short pairs (BUY = short USD)
    "EURUSD": frozenset({"GBPUSD", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY",
                          "EURCAD", "EURAUD", "EURCHF"}),
    "GBPUSD": frozenset({"EURUSD", "AUDUSD", "NZDUSD", "GBPJPY", "GBPAUD",
                          "GBPCHF"}),
    "AUDUSD": frozenset({"EURUSD", "GBPUSD", "NZDUSD", "AUDJPY", "EURAUD",
                          "GBPAUD", "AUDNZD"}),
    "NZDUSD": frozenset({"EURUSD", "GBPUSD", "AUDUSD", "AUDNZD"}),
    # USD-long pairs (BUY = long USD)
    "USDJPY": frozenset({"USDCAD", "USDCHF", "USDZAR", "USDMXN", "CADJPY",
                          "CHFJPY"}),
    "USDCAD": frozenset({"USDJPY", "USDCHF", "CADJPY"}),
    "USDCHF": frozenset({"USDJPY", "USDCAD", "CHFJPY"}),
    # JPY crosses
    "EURJPY": frozenset({"GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"}),
    "GBPJPY": frozenset({"EURJPY", "AUDJPY", "CADJPY"}),
    "AUDJPY": frozenset({"EURJPY", "GBPJPY", "CADJPY"}),
    "CADJPY": frozenset({"USDJPY", "USDCAD", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY"}),
    "CHFJPY": frozenset({"USDJPY", "USDCHF", "EURJPY", "CADJPY"}),
    # Non-USD crosses
    "GBPAUD": frozenset({"GBPUSD", "AUDUSD", "EURAUD"}),
    "GBPCHF": frozenset({"GBPUSD", "USDCHF", "EURCHF"}),
    "EURAUD": frozenset({"EURUSD", "AUDUSD", "GBPAUD"}),
    "EURCHF": frozenset({"EURUSD", "USDCHF", "GBPCHF"}),
    "EURCAD": frozenset({"EURUSD", "USDCAD"}),
    "AUDNZD": frozenset({"AUDUSD", "NZDUSD"}),
    # Precious metals / safe-haven
    "XAUUSD": frozenset({"XAGUSD"}),
    "XAGUSD": frozenset({"XAUUSD"}),
    # Crypto cluster
    "BTCUSD": frozenset({"ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD"}),
    "ETHUSD": frozenset({"BTCUSD", "LTCUSD", "XRPUSD", "SOLUSD"}),
    "LTCUSD": frozenset({"BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD"}),
    "XRPUSD": frozenset({"BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD"}),
    "SOLUSD": frozenset({"BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"}),
    # Oil
    "USOIL":  frozenset({"UKOIL"}),
    "UKOIL":  frozenset({"USOIL"}),
}


class RiskAgent:
    """Central risk gate.  Every signal must pass ``validate()``."""

    def __init__(
        self,
        broker: BrokerConnector,
        get_open_trades: Callable[[], list[Trade]],
        crucix_agent: "CrucixAgent | None" = None,
        db: "Database | None" = None,
    ) -> None:
        self._broker = broker
        self._get_open_trades = get_open_trades
        self._crucix = crucix_agent
        self._db = db

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
        """Return lot size based on risk parameters.

        Formula: lot_size = risk_usd / (sl_distance × contract_size)

        contract_size is the number of base-currency units per 1 standard lot.
        For USD-quoted instruments the dollar risk per lot is directly:
            sl_distance_in_price × contract_size
        Examples:
          EURUSD: sl_distance=0.0007, contract=100,000 → risk/lot=$70
          BTCUSD: sl_distance=500.0,  contract=1       → risk/lot=$500
          BCHUSD: sl_distance=1.77,   contract=1       → risk/lot=$1.77
        """
        balance = self._broker.get_balance()
        risk_amount = balance * settings.MAX_RISK_PER_TRADE
        sl_distance = abs(signal.entry_price - signal.stop_loss)
        if sl_distance == 0:
            return settings.MIN_LOT_SIZE
        cs = self._broker.get_contract_size(signal.symbol)
        risk_per_lot = sl_distance * cs
        lot_size = risk_amount / risk_per_lot
        raw_lot = round(lot_size, 2)
        lot_size = max(settings.MIN_LOT_SIZE, min(settings.MAX_LOT_SIZE, raw_lot))
        if raw_lot > settings.MAX_LOT_SIZE:
            logger.warning(
                "LOT CAP applied for %s: calculated %.2f → capped at %.2f (SL distance=%.5f)",
                signal.symbol, raw_lot, lot_size, sl_distance,
            )

        # Apply confidence scaling
        if signal.confidence < settings.CONFIDENCE_REDUCED:
            lot_size = round(lot_size * 0.5, 2)
        elif signal.confidence < settings.CONFIDENCE_FULL:
            lot_size = round(lot_size * 0.7, 2)

        # Macro risk scaling from Crucix
        if self._crucix:
            try:
                macro = self._crucix.get_context()
                scale = macro.lot_scale_factor
                if scale != 1.0:
                    lot_size = round(lot_size * scale, 2)
                    logger.info(
                        "MACRO LOT SCALE applied: tier=%s scale=%.2f → lot=%.2f",
                        macro.risk_tier, scale, lot_size,
                    )
            except Exception:
                pass  # Crucix unavailable — use unscaled lot

        return max(settings.MIN_LOT_SIZE, min(settings.MAX_LOT_SIZE, lot_size))

    # ── internal checks (ordered fail-fast) ──────────────────────────────

    def _validate_inner(self, signal: Signal) -> bool:
        # 1. Drawdown circuit breaker
        if self._check_drawdown():
            logger.warning("RISK REJECT [DRAWDOWN]: circuit breaker active")
            self._emit("warn", "Drawdown breaker is ON — no trades allowed!")
            return False

        # 1b. Crucix macro blackout check
        if self._crucix and self._crucix.is_blackout(signal.symbol):
            self._emit("warn",
                       f"MACRO BLACKOUT: FLASH alert active on {signal.symbol}",
                       {"symbol": signal.symbol, "check": "crucix_blackout"})
            return False

        open_trades = self._get_open_trades()

        # 2. Duplicate signal guard
        if self._check_duplicate(signal, open_trades):
            logger.warning(
                "RISK REJECT [DUPLICATE]: %s %s %s already open",
                signal.symbol, signal.direction, signal.strategy,
            )
            self._emit("warn",
                       f"DUPLICATE — {signal.symbol} {signal.direction} already open",
                       {"symbol": signal.symbol, "check": "duplicate"})
            return False

        # 3. Correlation guard (same symbol or correlated pair, same direction)
        if self._check_correlation(signal, open_trades):
            logger.warning(
                "RISK REJECT [CORRELATION]: %s %s blocked by existing exposure",
                signal.symbol, signal.direction,
            )
            self._emit("warn",
                       f"CORRELATION — {signal.symbol} {signal.direction} blocked by correlated open position",
                       {"symbol": signal.symbol, "check": "correlation"})
            return False

        # 4. Maximum concurrent open trades
        if len(open_trades) >= settings.MAX_OPEN_TRADES:
            logger.warning(
                "RISK REJECT [MAX_TRADES]: %d open >= limit %d",
                len(open_trades), settings.MAX_OPEN_TRADES,
            )
            self._emit(
                "warn",
                f"MAX_TRADES — {len(open_trades)} open trades >= limit {settings.MAX_OPEN_TRADES}",
                {"check": "max_trades",
                 "count": len(open_trades),
                 "limit": settings.MAX_OPEN_TRADES},
            )
            return False

        # 5. Live spread check (per-asset-class limits)
        # Prefer a fresh tick over the stale snapshot captured at signal time.
        live_spread = signal.entry_snapshot.spread
        try:
            tick = self._broker.get_tick(signal.symbol)
            if tick and tick.get("spread", 0) > 0:
                live_spread = tick["spread"]
        except Exception:
            pass  # broker unavailable — fall back to snapshot spread

        ac = asset_class(signal.symbol)
        if ac == "crypto":
            # Percentage-of-price check for crypto
            price = signal.entry_price or 1.0
            spread_pct = (live_spread / price) * 100
            if spread_pct > settings.MAX_SPREAD_PCT_CRYPTO:
                logger.warning(
                    "RISK REJECT [SPREAD]: %.3f%% > max %.1f%% for %s (crypto)",
                    spread_pct, settings.MAX_SPREAD_PCT_CRYPTO, signal.symbol,
                )
                self._emit("warn",
                           f"SPREAD — {signal.symbol} {spread_pct:.2f}% > max {settings.MAX_SPREAD_PCT_CRYPTO}%",
                           {"symbol": signal.symbol, "check": "spread",
                            "spread_pct": round(spread_pct, 3), "max": settings.MAX_SPREAD_PCT_CRYPTO})
                return False
        else:
            pv = pip_value(signal.symbol)
            spread_pips = live_spread / pv
            if ac == "commodity":
                max_spread = settings.MAX_SPREAD_PIPS_COMMODITY
            elif ac == "exotic":
                max_spread = settings.MAX_SPREAD_PIPS_EXOTIC
            else:
                max_spread = settings.MAX_SPREAD_PIPS

            if spread_pips > max_spread:
                logger.warning(
                    "RISK REJECT [SPREAD]: %.1f pips > max %.1f for %s (%s)",
                    spread_pips, max_spread, signal.symbol, ac,
                )
                self._emit("warn",
                           f"SPREAD — {signal.symbol} {spread_pips:.1f} pips > max {max_spread} ({ac})",
                           {"symbol": signal.symbol, "check": "spread",
                            "spread_pips": round(spread_pips, 1), "max": max_spread})
                return False

        # 7. Position size sanity
        lot_size = self.calculate_position_size(signal)
        if lot_size < settings.MIN_LOT_SIZE:
            logger.warning("RISK REJECT [LOT_SIZE]: calculated %.2f < min %.2f",
                           lot_size, settings.MIN_LOT_SIZE)
            self._emit("warn",
                       f"LOT_SIZE — {signal.symbol} calculated {lot_size:.3f} < min {settings.MIN_LOT_SIZE}",
                       {"symbol": signal.symbol, "check": "lot_size",
                        "lot_size": lot_size, "min": settings.MIN_LOT_SIZE})
            return False

        logger.info("RISK APPROVED: %s %s %s (lot=%.2f)",
                     signal.symbol, signal.direction, signal.strategy, lot_size)
        self._emit("info",
                   f"All clear — {signal.direction} {signal.symbol} approved (lot={lot_size:.2f})",
                   {"symbol": signal.symbol, "direction": signal.direction,
                    "lot_size": lot_size})
        return True

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("risk", level, msg, data)

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
        """Block if already holding the same symbol+direction from any strategy,
        OR if holding a highly-correlated pair in the same direction."""
        correlated = _CORRELATED_PAIRS.get(signal.symbol, frozenset())
        for t in open_trades:
            if not t.is_open():
                continue
            # Same symbol, any strategy (catches cross-strategy duplicates)
            if t.symbol == signal.symbol and t.direction == signal.direction:
                return True
            # Correlated pair, same direction → overlapping exposure
            if t.symbol in correlated and t.direction == signal.direction:
                logger.debug(
                    "Correlation block: %s %s blocked by open %s %s",
                    signal.direction, signal.symbol, t.direction, t.symbol,
                )
                return True
        return False
