"""Trade Manager Agent — monitors open positions and manages lifecycle.

Answers: *What do we do with the trade?*

Responsibilities:
- Partial closes at TP1/TP2
- SL to breakeven (entry + spread + commission) after TP1
- Trailing stop after TP2
- Emergency close (kill switch)
- State persistence on every change
- Reconciliation on startup + periodic
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Callable

from broker.connector import BrokerConnector
from config import settings
from config.symbols import pip_value
from database.db import Database
from models.trade import Trade
from state.persistence import StatePersistence
from utils import telegram_bot

logger = logging.getLogger(__name__)


class TradeManagerAgent:
    """Monitors and manages all open trades."""

    def __init__(
        self,
        broker: BrokerConnector,
        state: StatePersistence,
        db: Database,
    ) -> None:
        self._broker = broker
        self._state = state
        self._db = db
        self._open_trades: list[Trade] = []

    # ── lifecycle ────────────────────────────────────────────────────────

    def load_open_trades(self) -> None:
        """Load open trades from DB into memory (called on startup)."""
        self._open_trades = self._state.get_open_trades()
        logger.info("Loaded %d open trades from DB", len(self._open_trades))

    def reconcile(self, send_alert: Callable[[str], None] | None = None) -> None:
        """Run full reconciliation: DB vs broker."""
        alert_fn = send_alert or telegram_bot.send_message
        self._open_trades = self._state.reconcile(alert_fn)

    def get_open_trades(self) -> list[Trade]:
        return [t for t in self._open_trades if t.is_open()]

    # ── main monitor loop ────────────────────────────────────────────────

    def monitor(self) -> None:
        """Called once per main loop iteration."""
        try:
            self._monitor_inner()
        except Exception:
            logger.exception("TradeManager.monitor failed")

    def _monitor_inner(self) -> None:
        if not self._open_trades:
            return

        positions = self._broker.get_open_positions()
        pos_map = {p.ticket: p for p in positions}

        for trade in list(self._open_trades):
            if not trade.is_open():
                continue

            pos = pos_map.get(trade.broker_ticket)
            if pos is None:
                # Position closed externally
                trade.status = "CLOSED"
                trade.close_time = datetime.now(UTC)
                trade.close_reason = "EXTERNAL"
                self._state.save_trade(trade)
                logger.warning("Trade %s closed externally", trade.id)
                continue

            current_price = pos.current_price
            trade.pnl = pos.pnl

            # ── Check TP1 ────────────────────────────────────────────────
            if not trade.tp1_hit:
                if self._tp_reached(trade, current_price, trade.take_profit_1):
                    self._handle_tp1(trade)

            # ── Check TP2 ────────────────────────────────────────────────
            elif not trade.tp2_hit:
                if self._tp_reached(trade, current_price, trade.take_profit_2):
                    self._handle_tp2(trade)
                else:
                    # No trailing yet — waiting for TP2
                    pass

            # ── Check TP3 ────────────────────────────────────────────────
            elif not trade.tp3_hit:
                # Trail SL
                self._trail_stop(trade, current_price)
                if self._tp_reached(trade, current_price, trade.take_profit_3):
                    self._handle_tp3(trade)

            # ── Check SL ─────────────────────────────────────────────────
            if trade.is_open() and self._sl_hit(trade, current_price):
                self._handle_sl(trade)

        # Remove fully closed trades from in-memory list
        self._open_trades = [t for t in self._open_trades if t.is_open()]

    # ── TP / SL handlers ─────────────────────────────────────────────────

    def _handle_tp1(self, trade: Trade) -> None:
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp1_lots, trade.direction,
        )
        if not ok:
            logger.error("Failed to close TP1 partial for trade %s", trade.id)
            return
        trade.tp1_hit = True
        trade.status = "PARTIAL"

        # Move SL to breakeven (entry + spread + commission)
        be_sl = self._breakeven_price(trade)
        self._broker.modify_order(trade.broker_ticket, sl=be_sl)
        trade.stop_loss = be_sl

        self._state.save_trade(trade)
        logger.info("TP1 hit: trade %s — partial close %.2f lots, SL→BE %.5f",
                     trade.id, trade.tp1_lots, be_sl)
        telegram_bot.send_message(
            f"✅ TP1 hit: {trade.symbol} — closed {trade.tp1_lots} lots, SL→ breakeven"
        )

    def _handle_tp2(self, trade: Trade) -> None:
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp2_lots, trade.direction,
        )
        if not ok:
            logger.error("Failed to close TP2 partial for trade %s", trade.id)
            return
        trade.tp2_hit = True
        self._state.save_trade(trade)
        logger.info("TP2 hit: trade %s — partial close %.2f lots, trailing enabled",
                     trade.id, trade.tp2_lots)
        telegram_bot.send_message(
            f"✅ TP2 hit: {trade.symbol} — closed {trade.tp2_lots} lots, trailing SL active"
        )

    def _handle_tp3(self, trade: Trade) -> None:
        self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        trade.tp3_hit = True
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "TP3"
        self._state.save_trade(trade)
        logger.info("TP3 hit: trade %s — fully closed", trade.id)
        telegram_bot.send_message(
            f"🎯 TP3 hit: {trade.symbol} — trade fully closed (PnL {trade.pnl:.2f})"
        )

    def _handle_sl(self, trade: Trade) -> None:
        self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "SL"
        self._state.save_trade(trade)
        logger.info("SL hit: trade %s — closed (PnL %.2f)", trade.id, trade.pnl)
        telegram_bot.send_message(
            f"🛑 SL hit: {trade.symbol} — trade closed (PnL {trade.pnl:.2f})"
        )

    # ── emergency close ──────────────────────────────────────────────────

    def close_all(self, reason: str) -> None:
        """Emergency close every open position."""
        logger.critical("CLOSE ALL: %s", reason)
        for trade in list(self._open_trades):
            if not trade.is_open():
                continue
            self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
            trade.status = "CLOSED"
            trade.close_time = datetime.now(UTC)
            trade.close_reason = reason
            self._state.save_trade(trade)
        self._open_trades.clear()

    def close_trade(self, trade_id: str, reason: str) -> None:
        for trade in self._open_trades:
            if trade.id == trade_id and trade.is_open():
                self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
                trade.status = "CLOSED"
                trade.close_time = datetime.now(UTC)
                trade.close_reason = reason
                self._state.save_trade(trade)
                return

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _tp_reached(trade: Trade, current: float, tp: float) -> bool:
        if trade.direction == "BUY":
            return current >= tp
        return current <= tp

    @staticmethod
    def _sl_hit(trade: Trade, current: float) -> bool:
        if trade.direction == "BUY":
            return current <= trade.stop_loss
        return current >= trade.stop_loss

    @staticmethod
    def _breakeven_price(trade: Trade) -> float:
        """Entry + spread + commission offset."""
        pv = pip_value(trade.symbol)
        commission_pips = settings.COMMISSION_PER_LOT / (10 * 100_000) / pv
        offset = trade.spread_at_entry + commission_pips * pv
        if trade.direction == "BUY":
            return round(trade.entry_price + offset, 5)
        return round(trade.entry_price - offset, 5)

    def _trail_stop(self, trade: Trade, current: float) -> None:
        """Trail stop behind price by TRAILING_STOP_DISTANCE_PIPS."""
        pv = pip_value(trade.symbol)
        distance = settings.TRAILING_STOP_DISTANCE_PIPS * pv
        if trade.direction == "BUY":
            new_sl = round(current - distance, 5)
            if new_sl > trade.stop_loss:
                self._broker.modify_order(trade.broker_ticket, sl=new_sl)
                trade.stop_loss = new_sl
                self._state.save_trade(trade)
        else:
            new_sl = round(current + distance, 5)
            if new_sl < trade.stop_loss:
                self._broker.modify_order(trade.broker_ticket, sl=new_sl)
                trade.stop_loss = new_sl
                self._state.save_trade(trade)

    def add_trade(self, trade: Trade) -> None:
        """Register a newly opened trade for monitoring."""
        self._open_trades.append(trade)
