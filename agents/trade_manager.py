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
        self._emit("info", f"Loaded {len(self._open_trades)} open trades from DB")
        logger.info("Loaded %d open trades from DB", len(self._open_trades))

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("trade_manager", level, msg, data)

    def reconcile(self, send_alert: Callable[[str], None] | None = None) -> None:
        """Run full reconciliation: DB vs broker, including TP repair."""
        alert_fn = send_alert or telegram_bot.send_message
        self._open_trades = self._state.reconcile(alert_fn)
        self.sync_existing_position_targets(alert_fn)

    def sync_existing_position_targets(self, send_alert: Callable[[str], None] = lambda msg: None) -> None:
        """Scan all open broker positions, ensure bot-owned TPs are correct."""
        broker_positions = self._broker.get_open_positions()
        db_trades = {t.broker_ticket: t for t in self._open_trades if t.broker_ticket}
        mismatches = []
        for pos in broker_positions:
            # Ownership check: magic number and comment pattern
            if getattr(pos, 'magic', 0) != 202603:
                continue
            if not pos.comment or not any(tp in pos.comment for tp in ("_TP1", "_TP2", "_TP3")):
                continue
            # Determine intended TP
            intended_tp = None
            tp_level = None
            trade = db_trades.get(pos.ticket)
            if trade:
                # Use DB if available
                if "_TP1" in pos.comment:
                    intended_tp = trade.take_profit_1
                    tp_level = "TP1"
                elif "_TP2" in pos.comment:
                    intended_tp = trade.take_profit_2
                    tp_level = "TP2"
                elif "_TP3" in pos.comment:
                    intended_tp = trade.take_profit_3
                    tp_level = "TP3"
            else:
                # Try to parse TP from comment pattern
                if "_TP1" in pos.comment:
                    tp_level = "TP1"
                elif "_TP2" in pos.comment:
                    tp_level = "TP2"
                elif "_TP3" in pos.comment:
                    tp_level = "TP3"
                # Fallback: try to parse from comment (not robust)
                # Could extend to parse symbol/strategy if needed
            # If no intended TP, skip
            if intended_tp is None and tp_level:
                # Try to recover from position itself if possible
                # (not robust, but better than nothing)
                intended_tp = getattr(pos, 'take_profit', None)
            if intended_tp is None:
                continue
            # Compare broker TP to intended TP
            broker_tp = getattr(pos, 'take_profit', None)
            if broker_tp is None or abs(broker_tp - intended_tp) > 1e-5:
                # Attempt to fix
                ok = self._broker.modify_order(pos.ticket, tp=intended_tp)
                msg = (f"TP RECONCILE: ticket {pos.ticket} {pos.symbol} {tp_level} "
                       f"broker TP={broker_tp} intended TP={intended_tp} — "
                       f"{'FIXED' if ok else 'FAILED'}")
                if not ok:
                    msg += " (broker rejected modification)"
                mismatches.append(msg)
                logger.warning(msg)
            else:
                logger.info(f"TP OK: ticket {pos.ticket} {pos.symbol} {tp_level} TP={broker_tp}")
        if mismatches:
            alert_text = "⚠️ TP RECONCILIATION:\n" + "\n".join(mismatches)
            send_alert(alert_text)

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
                # Position no longer open — determine why.
                # If the bot already processed the TP/SL handler this iteration
                # (tp*_hit flags updated), the trade will be marked CLOSED by
                # that handler.  If not, the broker closed it (TP hit server-side
                # or manual close).  Infer the most likely reason from state.
                if trade.tp1_hit and trade.tp2_hit:
                    reason = "TP3"
                elif trade.tp1_hit:
                    reason = "TP2"
                elif trade.pnl < -0.01:
                    # Negative PnL and no bot-managed TP hit → SL was triggered
                    # (either by the broker server-side or manual intervention)
                    reason = "SL"
                elif trade.take_profit_1 and trade.pnl > 0:
                    # Position closed profitably at broker level before bot processed it
                    reason = "TP1"
                else:
                    reason = "EXTERNAL"
                trade.status = "CLOSED"
                trade.close_time = datetime.now(UTC)
                trade.close_reason = reason
                self._state.save_trade(trade)
                if reason == "EXTERNAL":
                    logger.warning("Trade %s closed externally (manual/margin-call)", trade.id)
                else:
                    logger.info("Trade %s closed by broker at %s", trade.id, reason)
                continue

            current_price = pos.current_price
            trade.pnl = pos.pnl

            # ── Check TP1 ────────────────────────────────────────────────
            if not trade.tp1_hit:
                if self._tp_reached(trade, current_price, trade.take_profit_1):
                    self._handle_tp1(trade, pos_map)

            # ── Check TP2 ────────────────────────────────────────────────
            elif not trade.tp2_hit:
                if self._tp_reached(trade, current_price, trade.take_profit_2):
                    self._handle_tp2(trade, pos_map)

            # ── Check TP3 ────────────────────────────────────────────────
            elif not trade.tp3_hit:
                # Trail SL
                self._trail_stop(trade, current_price)
                if self._tp_reached(trade, current_price, trade.take_profit_3):
                    self._handle_tp3(trade, pos_map)

            # ── Check SL ─────────────────────────────────────────────────
            if trade.is_open() and self._sl_hit(trade, current_price):
                self._handle_sl(trade, pos_map)

        # Remove fully closed trades from in-memory list
        self._open_trades = [t for t in self._open_trades if t.is_open()]

    # ── TP / SL handlers ─────────────────────────────────────────────────

    def _position_still_open(self, ticket: int, pos_map: dict | None = None) -> bool:
        """Return True if the broker ticket is still in the open positions list.

        Pass pos_map (from _monitor_inner) to avoid an extra broker API call.
        Falls back to a fresh broker call if pos_map is not provided.
        """
        if pos_map is not None:
            return ticket in pos_map
        try:
            return any(p.ticket == ticket for p in self._broker.get_open_positions())
        except Exception:
            return True  # assume still open on error — safer

    def _handle_tp1(self, trade: Trade, pos_map: dict) -> None:
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp1_lots, trade.direction,
        )
        if not ok:
            # Broker may have already closed the position at the TP level itself.
            # If it's gone, treat that as a successful TP hit rather than EXTERNAL.
            if self._position_still_open(trade.broker_ticket, pos_map):
                logger.error("Failed to close TP1 partial for trade %s", trade.id)
                return
            logger.info("TP1 closed by broker for trade %s — treating as TP hit", trade.id)
        trade.tp1_hit = True
        trade.status = "PARTIAL"

        be_sl = self._breakeven_price(trade)
        self._broker.modify_order(trade.broker_ticket, sl=be_sl)
        trade.stop_loss = be_sl

        self._state.save_trade(trade)
        self._emit("info",
                   f"TP1 hit on {trade.symbol}! Closed {trade.tp1_lots:.2f} lots, moving SL → breakeven ({be_sl:.5f})",
                   {"trade_id": trade.id, "tp": 1, "lots_closed": trade.tp1_lots})
        logger.info("TP1 hit: trade %s — partial close %.2f lots, SL→BE %.5f",
                     trade.id, trade.tp1_lots, be_sl)
        telegram_bot.send_message(
            f"✅ TP1 hit: {trade.symbol} — closed {trade.tp1_lots} lots, SL→ breakeven"
        )

    def _handle_tp2(self, trade: Trade, pos_map: dict) -> None:
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp2_lots, trade.direction,
        )
        if not ok:
            if self._position_still_open(trade.broker_ticket, pos_map):
                logger.error("Failed to close TP2 partial for trade %s", trade.id)
                return
            logger.info("TP2 closed by broker for trade %s — treating as TP hit", trade.id)
        trade.tp2_hit = True
        self._state.save_trade(trade)
        self._emit("info",
                   f"TP2 hit on {trade.symbol}! Closed {trade.tp2_lots:.2f} lots — trailing SL is now active.",
                   {"trade_id": trade.id, "tp": 2, "lots_closed": trade.tp2_lots})
        logger.info("TP2 hit: trade %s — partial close %.2f lots, trailing enabled",
                     trade.id, trade.tp2_lots)
        telegram_bot.send_message(
            f"✅ TP2 hit: {trade.symbol} — closed {trade.tp2_lots} lots, trailing SL active"
        )

    def _handle_tp3(self, trade: Trade, pos_map: dict) -> None:
        ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        if not ok and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to close TP3 for trade %s — position still open", trade.id)
            return
        trade.tp3_hit = True
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "TP3"
        true_pnl = round(trade.pnl - trade.commission, 2)
        self._state.save_trade(trade)
        self._emit("info",
                   f"TP3 hit on {trade.symbol}! Trade fully closed "
                   f"(gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}) — perfect exit.",
                   {"trade_id": trade.id, "tp": 3, "pnl": trade.pnl, "true_pnl": true_pnl})
        logger.info("TP3 hit: trade %s — fully closed (true PnL %.2f)", trade.id, true_pnl)
        telegram_bot.send_message(
            f"🎯 TP3 hit: {trade.symbol} — fully closed "
            f"gross {trade.pnl:.2f} − commission {trade.commission:.2f} = **{true_pnl:.2f}**"
        )

    def _handle_sl(self, trade: Trade, pos_map: dict) -> None:
        ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        if not ok and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to close SL for trade %s — position still open", trade.id)
            return
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "SL"
        true_pnl = round(trade.pnl - trade.commission, 2)
        self._state.save_trade(trade)
        self._emit("warn",
                   f"SL hit on {trade.symbol} — closed at loss "
                   f"(gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}).",
                   {"trade_id": trade.id, "pnl": trade.pnl, "commission": trade.commission,
                    "true_pnl": true_pnl})
        logger.info("SL hit: trade %s — closed (gross PnL %.2f, commission %.2f, true %.2f)",
                    trade.id, trade.pnl, trade.commission, true_pnl)
        telegram_bot.send_message(
            f"🛑 SL hit: {trade.symbol} — "
            f"gross {trade.pnl:.2f} − commission {trade.commission:.2f} = **{true_pnl:.2f}**"
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
        self._emit("critical", f"CLOSE ALL: {reason} — all positions closed")

    def close_trade(self, trade_id: str, reason: str) -> None:
        for trade in self._open_trades:
            if trade.id == trade_id and trade.is_open():
                self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
                trade.status = "CLOSED"
                trade.close_time = datetime.now(UTC)
                trade.close_reason = reason
                self._state.save_trade(trade)
                self._emit("info",
                           f"Trade {trade.symbol} closed: {reason} (PnL {trade.pnl:.2f})",
                           {"trade_id": trade.id, "reason": reason})
                logger.info("Trade %s closed: %s", trade.id, reason)
                return

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _tp_reached(trade: Trade, current: float, tp: float) -> bool:
        if not tp:  # 0.0 or None means TP not set — never treat as reached
            return False
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
