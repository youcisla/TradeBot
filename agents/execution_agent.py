"""Execution Agent — places trades via the broker.

Answers: *Can we execute it?*

Before every execution it checks for duplicate open positions on the same
symbol + direction + strategy as a final safety net.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Callable

from broker.connector import BrokerConnector
from config import settings
from models.signal import Signal
from models.trade import Trade
from state.persistence import StatePersistence
from utils import telegram_bot

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """Opens trades and persists them immediately to DB."""

    def __init__(
        self,
        broker: BrokerConnector,
        state: StatePersistence,
        calculate_position_size: Callable[[Signal], float],
        db: Database | None = None,
    ) -> None:
        self._broker = broker
        self._state = state
        self._calc_size = calculate_position_size
        self._db = db

    def open_trade(self, signal: Signal) -> Trade | None:
        try:
            self._emit("info",
                       f"Executing {signal.direction} {signal.symbol} — placing order now...",
                       {"symbol": signal.symbol, "direction": signal.direction})
            return self._open_inner(signal)
        except Exception:
            logger.exception("ExecutionAgent.open_trade failed")
            self._emit("error", f"Execution failed for {signal.symbol} {signal.direction}!")
            telegram_bot.send_message(
                f"❌ Execution error: {signal.symbol} {signal.direction}"
            )
            return None

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("execution", level, msg, data)

    def _open_inner(self, signal: Signal) -> Trade | None:
        # ── Final duplicate guard (belt + suspenders) ────────────────────
        open_trades = self._state.get_open_trades()
        for t in open_trades:
            if (t.symbol == signal.symbol
                    and t.direction == signal.direction
                    and t.strategy == signal.strategy
                    and t.is_open()):
                logger.warning(
                    "EXEC REJECT [DUPLICATE]: %s %s %s already open (trade %s)",
                    signal.symbol, signal.direction, signal.strategy, t.id,
                )
                return None

        lot_size = self._calc_size(signal)
        if lot_size < settings.MIN_LOT_SIZE:
            logger.warning("EXEC REJECT: lot_size %.2f below minimum", lot_size)
            return None

        # ── Place order ──────────────────────────────────────────────────
        result = self._broker.place_order(
            symbol=signal.symbol,
            direction=signal.direction,
            lot_size=lot_size,
            sl=signal.stop_loss,
            tp=None,  # We manage TPs ourselves
            comment=signal.strategy,
        )

        if not result.success:
            logger.error("Order failed: %s", result.message)
            telegram_bot.send_message(
                f"❌ Order failed: {signal.symbol} {signal.direction} — {result.message}"
            )
            return None

        # ── Handle partial fills ─────────────────────────────────────────
        filled = result.filled_lots
        if filled < settings.MIN_LOT_SIZE:
            logger.error("Partial fill too small (%.2f), closing", filled)
            self._broker.close_order(result.broker_ticket, signal.symbol, signal.direction)
            return None

        # ── Compute TP portions from actual fill ─────────────────────────
        tp1_lots = round(filled * settings.TP1_CLOSE_PERCENT, 2)
        tp2_lots = round(filled * settings.TP2_CLOSE_PERCENT, 2)
        tp3_lots = round(filled - tp1_lots - tp2_lots, 2)

        # ── Build trade object ───────────────────────────────────────────
        snap = signal.entry_snapshot
        trade = Trade(
            symbol=signal.symbol,
            strategy=signal.strategy,
            direction=signal.direction,
            entry_price=result.fill_price,
            lot_size=filled,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
            take_profit_3=signal.take_profit_3,
            tp1_lots=tp1_lots,
            tp2_lots=tp2_lots,
            tp3_lots=tp3_lots,
            broker_ticket=result.broker_ticket,
            spread_at_entry=snap.spread,
            open_time=datetime.now(UTC),
            # Flatten entry snapshot
            snap_rsi_aligned=snap.rsi_aligned,
            snap_trend_aligned=snap.trend_aligned,
            snap_volume_sufficient=snap.volume_sufficient,
            snap_near_news_event=snap.near_news_event,
            snap_market_condition=snap.market_condition,
            snap_session=snap.session,
            snap_day_of_week=snap.day_of_week,
        )

        # ── Persist immediately ──────────────────────────────────────────
        self._state.save_trade(trade)
        self._emit("info",
                   f"Trade opened! {trade.direction} {trade.symbol} {trade.lot_size:.2f} lots "
                   f"@ {trade.entry_price:.5f}  SL={trade.stop_loss:.5f}  ticket={trade.broker_ticket}",
                   {"trade_id": trade.id, "ticket": trade.broker_ticket,
                    "lots": trade.lot_size, "entry": trade.entry_price})
        logger.info(
            "TRADE OPENED: %s  %s %s  %.2f lots @ %.5f  ticket=%d",
            trade.id, trade.direction, trade.symbol,
            trade.lot_size, trade.entry_price, trade.broker_ticket,
        )
        telegram_bot.send_message(
            f"📈 Trade opened: {trade.direction} {trade.symbol} "
            f"{trade.lot_size} lots @ {trade.entry_price:.5f}  "
            f"SL={trade.stop_loss:.5f}"
        )
        return trade
