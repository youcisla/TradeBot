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
from config.symbols import pip_value, contract_size, commission_per_lot
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
        """Load open trades from MT5 on startup — broker is the source of truth.

        Runs a full reconciliation (broker vs DB) so any positions closed while
        the bot was offline are marked closed, and any orphaned broker positions
        are adopted, before we start monitoring.
        """
        self.reconcile()
        self._emit("info", f"Loaded {len(self._open_trades)} open trades from MT5 (reconciled)")
        logger.info("Loaded %d open trades from MT5 (reconciled)", len(self._open_trades))

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("trade_manager", level, msg, data)

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """Normalize a datetime to timezone-aware UTC for safe arithmetic."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

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
                # Fresh orders may take a short time to appear in the broker's
                # open-position feed. Keep a small grace window before treating
                # the absence as an external close.
                open_time_utc = self._ensure_utc(trade.open_time)
                age_seconds = (datetime.now(UTC) - open_time_utc).total_seconds()
                if age_seconds < settings.EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS:
                    continue

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
            trade.current_price = current_price
            if self._db:
                self._db.update_live_state(trade.id, trade.pnl, trade.current_price)

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

            # ── Check TP4 (runner to HTF liquidity) ──────────────────────
            elif not trade.tp4_hit and trade.take_profit_4 > 0:
                # Continue trailing the runner slice
                self._trail_stop(trade, current_price)
                if self._tp_reached(trade, current_price, trade.take_profit_4):
                    self._handle_tp4(trade, pos_map)

            # ── Check SL ─────────────────────────────────────────────────
            if trade.is_open() and self._sl_hit(trade, current_price):
                self._handle_sl(trade, pos_map)

            # ── Time-in-trade limit ───────────────────────────────────────
            if trade.is_open():
                open_time_utc = self._ensure_utc(trade.open_time)
                hours_open = (datetime.now(UTC) - open_time_utc).total_seconds() / 3600
                if hours_open >= settings.MAX_HOURS_IN_TRADE:
                    self._handle_time_limit(trade, pos_map, hours_open)

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

    def _reconcile_partial_close(
        self,
        ticket: int,
        before_lots: float,
        expected_closed_lots: float,
    ) -> tuple[bool, float]:
        """Verify how many lots were actually closed after a partial-close attempt."""
        try:
            positions = self._broker.get_open_positions()
            pos = next((p for p in positions if p.ticket == ticket), None)
        except Exception:
            logger.exception("Failed to reconcile partial close for ticket %s", ticket)
            return False, 0.0

        if pos is None:
            # Position fully closed at broker side.
            return True, round(max(0.0, before_lots), 2)

        actual_closed = round(max(0.0, before_lots - pos.lot_size), 2)
        if actual_closed <= 0:
            return False, 0.0

        if actual_closed + 1e-9 < expected_closed_lots:
            logger.warning(
                "Partial-fill reconciliation: ticket %s closed %.2f < requested %.2f",
                ticket,
                actual_closed,
                expected_closed_lots,
            )

        return True, actual_closed

    def _handle_tp1(self, trade: Trade, pos_map: dict) -> None:
        before_lots = pos_map.get(trade.broker_ticket).lot_size if trade.broker_ticket in pos_map else trade.remaining_lots()
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp1_lots, trade.direction,
        )
        reconciled, actual_closed = self._reconcile_partial_close(
            trade.broker_ticket,
            before_lots,
            trade.tp1_lots,
        )
        if not ok and not reconciled:
            # Broker may have already closed the position at the TP level itself.
            # If it's gone, treat that as a successful TP hit rather than EXTERNAL.
            if self._position_still_open(trade.broker_ticket, pos_map):
                logger.error("Failed to close TP1 partial for trade %s", trade.id)
                return
            logger.info("TP1 closed by broker for trade %s — treating as TP hit", trade.id)
        if reconciled and actual_closed + 1e-9 < trade.tp1_lots:
            self._emit(
                "warn",
                (
                    f"TP1 partial fill mismatch on {trade.symbol}: requested {trade.tp1_lots:.2f}, "
                    f"closed {actual_closed:.2f}"
                ),
                {
                    "trade_id": trade.id,
                    "ticket": trade.broker_ticket,
                    "requested": trade.tp1_lots,
                    "closed": actual_closed,
                },
            )
        trade.tp1_hit = True
        trade.status = "PARTIAL"

        # Pillar 4 — structural breakeven: prefer the structural swing level
        # stored at trade-open time; fall back to the entry+spread formula.
        if trade.structural_be > 0:
            be_sl = trade.structural_be
            be_type = "structural"
        else:
            be_sl = self._breakeven_price(trade)
            be_type = "entry+spread"
        self._broker.modify_order(trade.broker_ticket, sl=be_sl)
        trade.stop_loss = be_sl

        self._state.save_trade(trade)
        self._emit("info",
                   f"TP1 hit on {trade.symbol}! Closed {trade.tp1_lots:.2f} lots, "
                   f"moving SL → {be_type} breakeven ({be_sl:.5f})",
                   {"trade_id": trade.id, "tp": 1, "lots_closed": trade.tp1_lots,
                    "be_type": be_type})
        logger.info("TP1 hit: trade %s — partial close %.2f lots, SL→BE %.5f (%s)",
                     trade.id, trade.tp1_lots, be_sl, be_type)
        telegram_bot.send_message(
            f"✅ TP1 hit: {trade.symbol} — closed {trade.tp1_lots} lots, "
            f"SL→ {be_type} breakeven ({be_sl:.5f})"
        )

    def _handle_tp2(self, trade: Trade, pos_map: dict) -> None:
        before_lots = pos_map.get(trade.broker_ticket).lot_size if trade.broker_ticket in pos_map else trade.remaining_lots()
        ok = self._broker.close_partial(
            trade.broker_ticket, trade.symbol, trade.tp2_lots, trade.direction,
        )
        reconciled, actual_closed = self._reconcile_partial_close(
            trade.broker_ticket,
            before_lots,
            trade.tp2_lots,
        )
        if not ok and not reconciled:
            if self._position_still_open(trade.broker_ticket, pos_map):
                logger.error("Failed to close TP2 partial for trade %s", trade.id)
                return
            logger.info("TP2 closed by broker for trade %s — treating as TP hit", trade.id)
        if reconciled and actual_closed + 1e-9 < trade.tp2_lots:
            self._emit(
                "warn",
                (
                    f"TP2 partial fill mismatch on {trade.symbol}: requested {trade.tp2_lots:.2f}, "
                    f"closed {actual_closed:.2f}"
                ),
                {
                    "trade_id": trade.id,
                    "ticket": trade.broker_ticket,
                    "requested": trade.tp2_lots,
                    "closed": actual_closed,
                },
            )
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
        # When TP4 (runner) is active, TP3 is a partial close, not the final exit.
        has_runner = trade.take_profit_4 > 0 and trade.tp4_lots > 0
        if has_runner:
            before_lots = pos_map.get(trade.broker_ticket).lot_size if trade.broker_ticket in pos_map else trade.remaining_lots()
            ok = self._broker.close_partial(
                trade.broker_ticket, trade.symbol, trade.tp3_lots, trade.direction,
            )
            reconciled, actual_closed = self._reconcile_partial_close(
                trade.broker_ticket,
                before_lots,
                trade.tp3_lots,
            )
        else:
            ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
            reconciled = True
            actual_closed = trade.tp3_lots
        if not ok and not reconciled and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to close TP3 for trade %s — position still open", trade.id)
            return
        if has_runner and reconciled and actual_closed + 1e-9 < trade.tp3_lots:
            self._emit(
                "warn",
                (
                    f"TP3 partial fill mismatch on {trade.symbol}: requested {trade.tp3_lots:.2f}, "
                    f"closed {actual_closed:.2f}"
                ),
                {
                    "trade_id": trade.id,
                    "ticket": trade.broker_ticket,
                    "requested": trade.tp3_lots,
                    "closed": actual_closed,
                },
            )
        trade.tp3_hit = True
        if not has_runner:
            trade.status = "CLOSED"
            trade.close_time = datetime.now(UTC)
            trade.close_reason = "TP3"
        true_pnl = round(trade.pnl - trade.commission, 2)
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._emit("info",
                   f"TP3 hit on {trade.symbol}! "
                   + (f"Closed {trade.tp3_lots:.2f} lots — runner active to TP4={trade.take_profit_4:.5f}"
                      if has_runner else
                      f"Trade fully closed (gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}; "
                      f"expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f}) — perfect exit."),
                   {"trade_id": trade.id, "tp": 3, "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap,
                    "runner": has_runner})
        logger.info("TP3 hit: trade %s — %s (true PnL so far %.2f)",
                    trade.id, "runner continues" if has_runner else "fully closed", true_pnl)
        telegram_bot.send_message(
            f"🎯 TP3 hit: {trade.symbol} — "
            + (f"closed {trade.tp3_lots} lots, runner to TP4={trade.take_profit_4:.5f}"
               if has_runner else
               f"fully closed gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f} | "
               f"expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}")
        )

    def _handle_tp4(self, trade: Trade, pos_map: dict) -> None:
        """Close the runner slice at the HTF liquidity target (TP4)."""
        ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        if not ok and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to close TP4 runner for trade %s — position still open", trade.id)
            return
        trade.tp4_hit = True
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "TP4"
        true_pnl = round(trade.pnl - trade.commission, 2)
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._emit("info",
                   f"TP4 (runner) hit on {trade.symbol}! Trade fully closed at HTF liquidity "
                   f"(gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}; "
                   f"expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f})",
                   {"trade_id": trade.id, "tp": 4, "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap})
        logger.info("TP4 runner hit: trade %s — fully closed (true PnL %.2f)", trade.id, true_pnl)
        telegram_bot.send_message(
            f"🚀 TP4 runner hit: {trade.symbol} — fully closed at HTF liquidity "
            f"gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f} | "
            f"expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
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
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._emit("warn",
                   f"SL hit on {trade.symbol} — closed at loss "
                   f"(gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}; "
                   f"expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f}).",
                   {"trade_id": trade.id, "pnl": trade.pnl, "commission": trade.commission,
                    "true_pnl": true_pnl, "expected_pnl": trade.expected_pnl,
                    "expected_gap": expected_gap})
        logger.info("SL hit: trade %s — closed (gross PnL %.2f, commission %.2f, true %.2f)",
                    trade.id, trade.pnl, trade.commission, true_pnl)
        telegram_bot.send_message(
            f"🛑 SL hit: {trade.symbol} — "
            f"gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f} | "
            f"expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
        )

    def _handle_time_limit(self, trade: Trade, pos_map: dict, hours_open: float) -> None:
        """Force-close a stale trade that has exceeded MAX_HOURS_IN_TRADE."""
        ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        if not ok and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to force-close stale trade %s after %.1fh", trade.id, hours_open)
            return
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "TIME_LIMIT"
        true_pnl = round(trade.pnl - trade.commission, 2)
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._emit("warn",
                   f"Time limit: {trade.symbol} closed after {hours_open:.1f}h "
                   f"(max={settings.MAX_HOURS_IN_TRADE}h) "
                   f"(gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f}; "
                   f"expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f})",
                   {"trade_id": trade.id, "hours_open": round(hours_open, 1),
                    "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap})
        logger.warning("TIME_LIMIT: trade %s force-closed after %.1fh (true PnL %.2f)",
                       trade.id, hours_open, true_pnl)
        telegram_bot.send_message(
            f"⏰ Time limit: {trade.symbol} closed after {hours_open:.1f}h — "
            f"gross {trade.pnl:.2f} − commission {trade.commission:.2f} = {true_pnl:.2f} | "
            f"expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
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
        """Entry + spread + commission offset.

        Commission offset converts the per-lot dollar commission into a price
        offset: commission_usd / contract_size gives the price movement needed
        to recover commission cost.
          EURUSD (100k/lot): 7 / 100_000 = 0.00007  (~0.7 pips)
          BTCUSD (1/lot):    7 / 1       = 7.0       ($7 price move)
          XAUUSD (100/lot):  7 / 100     = 0.07      ($0.07 per oz)
        """
        cs = contract_size(trade.symbol)
        commission_offset = commission_per_lot(trade.symbol) / cs
        offset = trade.spread_at_entry + commission_offset
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
