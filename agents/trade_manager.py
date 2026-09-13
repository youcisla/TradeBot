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
from typing import TYPE_CHECKING, Callable

from broker.connector import MAGIC, BrokerConnector
from utils.mesh_bus import mesh_span
from config import settings
from config.symbols import pip_value, contract_size, commission_per_lot
from adapters.db.db import Database
from models.trade import Trade
from state.persistence import StatePersistence
from utils import telegram_bot

if TYPE_CHECKING:
    from agents.guards import GuardPipeline

logger = logging.getLogger(__name__)


class TradeManagerAgent:
    """Monitors and manages all open trades."""

    def __init__(
        self,
        broker: BrokerConnector,
        state: StatePersistence,
        db: Database,
        guard_pipeline: "GuardPipeline | None" = None,
    ) -> None:
        self._broker = broker
        self._state = state
        self._db = db
        self._guard_pipeline = guard_pipeline
        self._open_trades: list[Trade] = []

    # ── internal helpers ──────────────────────────────────────────────────

    def _record_pnl(self, pnl: float) -> None:
        """Tell the guard pipeline about closed-trade P&L. Safe to call when _guard_pipeline is None."""
        if self._guard_pipeline is not None:
            self._guard_pipeline.record_closed_trade_pnl(pnl)

    # ── lifecycle ────────────────────────────────────────────────────────

    def load_open_trades(self) -> None:
        """Load open trades from MT5 on startup — broker is the source of truth.

        Runs a full reconciliation (broker vs DB) so any positions closed while
        the bot was offline are marked closed, and any orphaned broker positions
        are adopted, before we start monitoring.
        """
        self.reconcile()
        # Restore in-memory _open_trades from DB after reconcile so the manager
        # tracks what the broker actually has open (gabagool pattern).
        self._open_trades = self._state.get_open_trades()
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
        """Ensure every bot-owned position carries the targets its DB trade expects.

        The bot opens ONE position per trade and sets the broker TP to the
        furthest active target, doing scale-out itself via partial closes.
        This previously keyed on a ``_TP1``/``_TP2``/``_TP3`` comment convention
        that ``order_executor`` never writes — comments carry the strategy name
        — so the safety net matched nothing and never repaired a single stop.
        Ownership is now decided by magic number plus a DB lookup, and the
        broker is treated as authoritative for the stop.
        """
        broker_positions = self._broker.get_open_positions()
        db_trades = {t.broker_ticket: t for t in self._open_trades if t.broker_ticket}
        problems: list[str] = []

        for pos in broker_positions:
            if getattr(pos, "magic", 0) != MAGIC:
                continue

            trade = db_trades.get(pos.ticket)
            if trade is None:
                problems.append(
                    f"ORPHAN: ticket {pos.ticket} {pos.symbol} {pos.lot_size:.2f} lots "
                    "carries our magic but has no DB trade"
                )
                continue

            targets = [
                tp
                for tp in (
                    trade.take_profit_1,
                    trade.take_profit_2,
                    trade.take_profit_3,
                    trade.take_profit_4,
                )
                if tp and tp > 0
            ]
            intended_tp = max(targets) if targets else None
            broker_tp = getattr(pos, "take_profit", None)
            if intended_tp and (broker_tp is None or abs(broker_tp - intended_tp) > 1e-5):
                ok = self._broker.modify_order(pos.ticket, tp=intended_tp)
                problems.append(
                    f"TP RECONCILE: ticket {pos.ticket} {pos.symbol} "
                    f"broker={broker_tp} intended={intended_tp} "
                    f"{'FIXED' if ok else 'FAILED (broker rejected)'}"
                )

            # The broker's stop is what the account actually carries.  If it
            # differs from ours, adopt theirs rather than pushing ours — a
            # rejectable modify would otherwise leave the DB claiming a
            # protection the position does not have.
            if trade.stop_loss and abs(pos.stop_loss - trade.stop_loss) > 1e-5:
                problems.append(
                    f"SL DIVERGENCE: ticket {pos.ticket} {pos.symbol} "
                    f"broker SL={pos.stop_loss:.5f} DB SL={trade.stop_loss:.5f} "
                    "— adopting broker value"
                )
                trade.stop_loss = pos.stop_loss
                self._state.save_trade(trade)

        if problems:
            logger.warning("Position target reconciliation:\n%s", "\n".join(problems))
            send_alert("⚠️ POSITION RECONCILIATION:\n" + "\n".join(problems))

    def get_open_trades(self) -> list[Trade]:
        return [t for t in self._open_trades if t.is_open()]

    # ── main monitor loop ────────────────────────────────────────────────

    def monitor(self) -> None:
        """Called once per main loop iteration."""
        try:
            with mesh_span("trade_manager"):
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
        # Only record the move once the broker confirms it.  Committing a
        # rejected stop locally makes the DB claim a protection the account
        # does not actually hold — the wider broker stop is what is exposed.
        if self._broker.modify_order(trade.broker_ticket, sl=be_sl):
            trade.stop_loss = be_sl
        else:
            logger.error(
                "Broker rejected breakeven SL for trade %s (ticket=%s, sl=%.5f) "
                "— local SL left unchanged",
                trade.id,
                trade.broker_ticket,
                be_sl,
            )
            self._emit(
                "error",
                f"Broker rejected breakeven SL for {trade.symbol} — stop unchanged",
                {"trade_id": trade.id, "ticket": trade.broker_ticket, "sl": be_sl},
            )

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
            # Overwrite floating pnl with actual net from MT5 deal history before persisting.
            realized = self._broker.get_closed_pnl(trade.broker_ticket)
            if realized is not None:
                trade.pnl = realized
            realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
            if realized_swap is not None:
                trade.swap = realized_swap
        # trade.pnl is now the authoritative MT5 net P&L (commission already deducted at deal level).
        # expected_pnl was set at open and does NOT include commission, so use trade.pnl directly.
        true_pnl = trade.pnl
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        if not has_runner:
            self._record_pnl(true_pnl)
            self._close_thesis(trade, "CLOSED_WIN")
        self._emit("info",
                   f"TP3 hit on {trade.symbol}! "
                   + (f"Closed {trade.tp3_lots:.2f} lots — runner active to TP4={trade.take_profit_4:.5f}"
                      if has_runner else
                      f"Trade fully closed net {true_pnl:.2f} "
                      f"(expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f}) — perfect exit."),
                   {"trade_id": trade.id, "tp": 3, "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap,
                    "runner": has_runner})
        logger.info("TP3 hit: trade %s — %s (net PnL %.2f)",
                    trade.id, "runner continues" if has_runner else "fully closed", true_pnl)
        telegram_bot.send_message(
            f"🎯 TP3 hit: {trade.symbol} — "
            + (f"closed {trade.tp3_lots} lots, runner to TP4={trade.take_profit_4:.5f}"
               if has_runner else
               f"fully closed net {true_pnl:.2f} | expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}")
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
        realized = self._broker.get_closed_pnl(trade.broker_ticket)
        if realized is not None:
            trade.pnl = realized
        realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
        if realized_swap is not None:
            trade.swap = realized_swap
        true_pnl = trade.pnl
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._record_pnl(true_pnl)
        self._close_thesis(trade, "CLOSED_WIN")
        self._emit("info",
                   f"TP4 (runner) hit on {trade.symbol}! Trade fully closed at HTF liquidity "
                   f"(net {true_pnl:.2f}; expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f})",
                   {"trade_id": trade.id, "tp": 4, "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap})
        logger.info("TP4 runner hit: trade %s — fully closed (net PnL %.2f)", trade.id, true_pnl)
        telegram_bot.send_message(
            f"🚀 TP4 runner hit: {trade.symbol} — fully closed at HTF liquidity "
            f"net {true_pnl:.2f} | expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
        )

    def _handle_sl(self, trade: Trade, pos_map: dict) -> None:
        ok = self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
        if not ok and self._position_still_open(trade.broker_ticket, pos_map):
            logger.error("Failed to close SL for trade %s — position still open", trade.id)
            return
        trade.status = "CLOSED"
        trade.close_time = datetime.now(UTC)
        trade.close_reason = "SL"
        realized = self._broker.get_closed_pnl(trade.broker_ticket)
        if realized is not None:
            trade.pnl = realized
        realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
        if realized_swap is not None:
            trade.swap = realized_swap
        true_pnl = trade.pnl
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._record_pnl(true_pnl)
        self._close_thesis(trade, "CLOSED_LOSS")
        self._emit("warn",
                   f"SL hit on {trade.symbol} — closed at loss "
                   f"(net {true_pnl:.2f}; expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f}).",
                   {"trade_id": trade.id, "pnl": trade.pnl, "commission": trade.commission,
                    "true_pnl": true_pnl, "expected_pnl": trade.expected_pnl,
                    "expected_gap": expected_gap})
        logger.info("SL hit: trade %s — closed (net PnL %.2f, expected %.2f, Δ %.2f)",
                    trade.id, true_pnl, trade.expected_pnl, expected_gap)
        telegram_bot.send_message(
            f"🛑 SL hit: {trade.symbol} — "
            f"net {true_pnl:.2f} | expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
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
        realized = self._broker.get_closed_pnl(trade.broker_ticket)
        if realized is not None:
            trade.pnl = realized
        realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
        if realized_swap is not None:
            trade.swap = realized_swap
        true_pnl = trade.pnl
        expected_gap = round(true_pnl - float(trade.expected_pnl or 0.0), 2)
        self._state.save_trade(trade)
        self._record_pnl(true_pnl)
        _tl_outcome = (
            "CLOSED_WIN" if trade.pnl > 0
            else "CLOSED_LOSS" if trade.pnl < -0.01
            else "CLOSED_SCRATCH"
        )
        self._close_thesis(trade, _tl_outcome)
        self._emit("warn",
                   f"Time limit: {trade.symbol} closed after {hours_open:.1f}h "
                   f"(max={settings.MAX_HOURS_IN_TRADE}h) "
                   f"(net {true_pnl:.2f}; expected {trade.expected_pnl:.2f}, Δ {expected_gap:+.2f})",
                   {"trade_id": trade.id, "hours_open": round(hours_open, 1),
                    "pnl": trade.pnl, "true_pnl": true_pnl,
                    "expected_pnl": trade.expected_pnl, "expected_gap": expected_gap})
        logger.warning("TIME_LIMIT: trade %s force-closed after %.1fh (net PnL %.2f)",
                       trade.id, hours_open, true_pnl)
        telegram_bot.send_message(
            f"⏰ Time limit: {trade.symbol} closed after {hours_open:.1f}h — "
            f"net {true_pnl:.2f} | expected {trade.expected_pnl:.2f} | Δ {expected_gap:+.2f}"
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
            realized = self._broker.get_closed_pnl(trade.broker_ticket)
            if realized is not None:
                trade.pnl = realized
            realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
            if realized_swap is not None:
                trade.swap = realized_swap
            true_pnl = trade.pnl
            self._state.save_trade(trade)
            self._record_pnl(true_pnl)
            self._close_thesis(trade, "CLOSED_SCRATCH")
        self._open_trades.clear()
        self._emit("critical", f"CLOSE ALL: {reason} — all positions closed")

    def close_trade(self, trade_id: str, reason: str) -> None:
        for trade in self._open_trades:
            if trade.id == trade_id and trade.is_open():
                self._broker.close_order(trade.broker_ticket, trade.symbol, trade.direction)
                trade.status = "CLOSED"
                trade.close_time = datetime.now(UTC)
                trade.close_reason = reason
                realized = self._broker.get_closed_pnl(trade.broker_ticket)
                if realized is not None:
                    trade.pnl = realized
                realized_swap = self._broker.get_closed_swap(trade.broker_ticket)
                if realized_swap is not None:
                    trade.swap = realized_swap
                true_pnl = trade.pnl
                self._state.save_trade(trade)
                self._record_pnl(true_pnl)
                self._close_thesis(trade, "CLOSED_SCRATCH")
                self._emit("info",
                           f"Trade {trade.symbol} closed: {reason} (PnL {trade.pnl:.2f})",
                           {"trade_id": trade.id, "reason": reason})
                logger.info("Trade %s closed: %s", trade.id, reason)
                return

    # ── helpers ──────────────────────────────────────────────────────────

    def _close_thesis(self, trade: "Trade", outcome: str) -> None:
        """Fire-and-forget — update trade_theses row when a trade fully closes."""
        if not self._db:
            return
        try:
            # trade.pnl is now the authoritative MT5 net P&L (commission already deducted
            # at the deal level). _close_thesis notes are for human reference only.
            true_pnl = trade.pnl
            self._db.update_trade_outcome(
                trade.id,
                actual_outcome=outcome,
                notes=f"pnl={true_pnl:.2f} reason={trade.close_reason}",
            )
        except Exception:
            logger.debug("update_trade_outcome failed (non-fatal)", exc_info=True)

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
            improves = new_sl > trade.stop_loss
        else:
            new_sl = round(current + distance, 5)
            improves = new_sl < trade.stop_loss
        if not improves:
            return

        # Only commit once the broker confirms.  A rejected trailing move that
        # is recorded locally leaves the DB and the account disagreeing about
        # where the stop actually sits.
        if self._broker.modify_order(trade.broker_ticket, sl=new_sl):
            trade.stop_loss = new_sl
            self._state.save_trade(trade)
        else:
            logger.error(
                "Broker rejected trailing SL for trade %s (ticket=%s, sl=%.5f)",
                trade.id,
                trade.broker_ticket,
                new_sl,
            )

    def add_trade(self, trade: Trade) -> None:
        """Register a newly opened trade for monitoring."""
        self._open_trades.append(trade)
