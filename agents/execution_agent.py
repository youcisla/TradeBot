"""Execution Agent — places trades via the broker.

Answers: *Can we execute it?*

Before every execution it checks for duplicate open positions on the same
symbol + direction + strategy as a final safety net.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Callable

from broker.connector import BrokerConnector
from utils.mesh_bus import mesh_span
from config import settings
from agents.guards import GuardPipeline
from config.symbols import commission_per_lot, contract_size
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
        self._autotrading_block_until: datetime | None = None
        self._autotrading_block_last_notice: datetime | None = None
        # GuardPipeline — pre-execution safety checks
        self._guards = GuardPipeline(broker=broker, db=db)

    def open_trade(self, signal: Signal) -> Trade | None:
        try:
            self._emit("info",
                       f"Executing {signal.direction} {signal.symbol} — placing order now...",
                       {"symbol": signal.symbol, "direction": signal.direction})
            with mesh_span("execution"):
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

    @property
    def guard_pipeline(self) -> GuardPipeline:
        """Exposed so TradeManagerAgent can record scalp closes against the same guard state."""
        return self._guards

    def _open_inner(self, signal: Signal) -> Trade | None:
        # ── GuardPipeline gate ────────────────────────────────────────────
        if getattr(settings, "GUARD_PIPELINE_ENABLED", True):
            live = self._broker.get_open_positions()
            passed, reason = self._guards.check(signal, open_trades=live)
            if not passed:
                logger.warning(
                    "EXEC BLOCKED [GUARD]: %s %s — %s",
                    signal.symbol,
                    signal.direction,
                    reason,
                )
                self._emit(
                    "warn",
                    f"Trade blocked by guard: {reason}",
                    {"symbol": signal.symbol, "direction": signal.direction, "reason": reason},
                )
                return None

        if self._autotrading_block_until is not None:
            now = datetime.now(UTC)
            if now < self._autotrading_block_until:
                if (
                    self._autotrading_block_last_notice is None
                    or (now - self._autotrading_block_last_notice).total_seconds() >= 60
                ):
                    self._autotrading_block_last_notice = now
                    wait_s = int((self._autotrading_block_until - now).total_seconds())
                    logger.warning(
                        "EXEC SKIP [AUTOTRADING_DISABLED]: %s %s (retry in %ss)",
                        signal.symbol,
                        signal.direction,
                        max(1, wait_s),
                    )
                    self._emit(
                        "warn",
                        (
                            f"Execution temporarily blocked — MT5 autotrading disabled; "
                            f"retry in {max(1, wait_s)}s"
                        ),
                        {"symbol": signal.symbol, "direction": signal.direction, "retry_in_s": max(1, wait_s)},
                    )
                return None

        # With FIXED_LOT_SIZE enforced at the broker connector, all trades are
        # 0.01 lot. Unlimited concurrent trades are allowed — each gets its own
        # MT5 ticket and cannot override or close another.
        lot_size = self._calc_size(signal)
        if lot_size < settings.MIN_LOT_SIZE:
            logger.warning("EXEC REJECT: lot_size %.2f below minimum", lot_size)
            return None

        # Calculate per-TP lot allocations.
        # When TP4 is set (runner target at HTF liquidity), carve it from
        # the position; otherwise the runner slice stays in TP3.
        tp1_lots = round(lot_size * settings.TP1_CLOSE_PERCENT, 2)
        tp2_lots = round(lot_size * settings.TP2_CLOSE_PERCENT, 2)
        has_tp4 = signal.take_profit_4 > 0
        tp4_lots = round(lot_size * settings.TP4_CLOSE_PERCENT, 2) if has_tp4 else 0.0
        tp3_lots = round(lot_size - tp1_lots - tp2_lots - tp4_lots, 2)

        # Place ONE order for the full position.
        # Set broker-side TP at the furthest active target as a crash-safety net
        # — trade_manager manages the actual partial exits via close_partial.
        if has_tp4:
            broker_tp = signal.take_profit_4
        elif signal.take_profit_3 > 0:
            broker_tp = signal.take_profit_3
        else:
            broker_tp = None
        result = self._broker.place_order(
            symbol=signal.symbol,
            direction=signal.direction,
            lot_size=lot_size,
            sl=signal.stop_loss,
            tp=broker_tp,
            comment=signal.strategy,
        )
        if not result.success:
            msg = result.message or ""
            # Stale-signal rejection: market moved between detection and execution.
            # Pre-validated in place_order before MT5 sees it — not a real error,
            # just a missed entry. Log at warning, no Telegram noise.
            if "signal stale" in msg:
                logger.warning("Order skipped (stale signal): %s", msg)
                self._emit("warn",
                           f"Entry skipped — market moved past SL before execution "
                           f"({signal.symbol} {signal.direction})",
                           {"symbol": signal.symbol, "reason": "stale_signal"})
                return None
            logger.error("Order failed: %s", msg)
            # Error 10017/10027 = trade disabled in MT5 terminal (autotrading off).
            # This is terminal-level, not symbol-level — back off execution attempts
            # for a cooldown window and pause via Telegram control plane.
            if self._is_autotrading_disabled(msg):
                now = datetime.now(UTC)
                self._autotrading_block_until = now + timedelta(
                    seconds=settings.EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS
                )
                self._autotrading_block_last_notice = now
                telegram_bot.send_message(
                    "⛔ MT5 Trade Disabled (error 10017/10027) — autotrading is OFF in the terminal.\n"
                    "Re-enable 'Algo Trading' in MT5 and use /resume to continue.\n"
                    f"Execution backoff: {settings.EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS}s"
                )
                telegram_bot.pause()
                self._emit(
                    "error",
                    "MT5 autotrading is disabled (10017/10027) — bot paused",
                    {
                        "error": msg,
                        "cooldown_seconds": settings.EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS,
                    },
                )
            else:
                telegram_bot.send_message(
                    f"❌ Order failed: {signal.symbol} {signal.direction} — {msg}"
                )
            return None

        # Watchdog: order_send returned success, but we only proceed once the
        # broker position is actually visible. If it never appears, escalate.
        if not self._confirm_position_open(result.broker_ticket):
            close_ok = self._broker.close_order(
                result.broker_ticket,
                signal.symbol,
                signal.direction,
            )
            timeout_s = settings.EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS
            outcome = "OK" if close_ok else "FAILED"
            logger.error(
                "EXEC TIMEOUT [POSITION_NOT_VISIBLE]: ticket=%s %s %s (%.2fs) close=%s",
                result.broker_ticket,
                signal.symbol,
                signal.direction,
                timeout_s,
                outcome,
            )
            self._emit(
                "error",
                (
                    "Order confirmation timeout: broker ticket not visible in open "
                    f"positions within {timeout_s:.2f}s"
                ),
                {
                    "ticket": result.broker_ticket,
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "timeout_seconds": timeout_s,
                    "emergency_close": outcome,
                },
            )
            telegram_bot.send_message(
                "⚠️ Order confirmation timeout: "
                f"{signal.symbol} {signal.direction} ticket={result.broker_ticket} "
                f"not visible after {timeout_s:.2f}s. "
                f"Emergency close attempt: {outcome}."
            )
            return None

        # Estimate round-trip commission for display/PnL tracking.
        # Rate varies by asset class (crypto/commodity/exotic may differ from forex).
        commission = round(lot_size * commission_per_lot(signal.symbol), 2)

        target_price = (
            signal.take_profit_4
            or signal.take_profit_3
            or signal.take_profit_2
            or signal.take_profit_1
        )
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        target_distance = abs(target_price - signal.entry_price) if target_price > 0 else 0.0
        expected_edge_pct = (target_distance / stop_distance) if stop_distance > 0 else 0.0
        expected_pnl = 0.0
        if target_distance > 0:
            expected_pnl = (
                target_distance * contract_size(signal.symbol) * lot_size
            ) - commission

        snap = signal.entry_snapshot
        trade = Trade(
            symbol=signal.symbol,
            strategy=signal.strategy,
            direction=signal.direction,
            entry_price=result.fill_price,
            lot_size=lot_size,
            commission=commission,
            expected_edge_pct=max(signal.expected_edge_pct, expected_edge_pct),
            expected_pnl=(signal.expected_pnl if signal.expected_pnl != 0.0 else expected_pnl),
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1 or 0.0,
            take_profit_2=signal.take_profit_2 or 0.0,
            take_profit_3=signal.take_profit_3 or 0.0,
            take_profit_4=signal.take_profit_4,
            tp1_lots=tp1_lots,
            tp2_lots=tp2_lots,
            tp3_lots=tp3_lots,
            tp4_lots=tp4_lots,
            structural_be=signal.structural_be,
            broker_ticket=result.broker_ticket,
            spread_at_entry=snap.spread,
            open_time=datetime.now(UTC),
            snap_rsi_aligned=snap.rsi_aligned,
            snap_trend_aligned=snap.trend_aligned,
            snap_volume_sufficient=snap.volume_sufficient,
            snap_near_news_event=snap.near_news_event,
            snap_market_condition=snap.market_condition,
            snap_session=snap.session,
            snap_day_of_week=snap.day_of_week,
        )
        self._state.save_trade(trade)
        # ── persist trade thesis ──────────────────────────────────────────
        if self._db:
            try:
                stop_distance = abs(trade.entry_price - trade.stop_loss)
                target_price = (
                    signal.take_profit_4
                    or signal.take_profit_3
                    or signal.take_profit_2
                    or signal.take_profit_1
                )
                target_distance = abs(target_price - trade.entry_price) if target_price else 0.0
                rr = round(target_distance / stop_distance, 2) if stop_distance > 0 else None
                entry_reason = getattr(signal, "reason", "") or ""
                self._db.save_trade_thesis(
                    symbol=trade.symbol,
                    direction=trade.direction,
                    stage="ACTIVE",
                    trade_id=trade.id,
                    entry_price=trade.entry_price,
                    sl_price=trade.stop_loss,
                    tp_price=float(target_price) if target_price else None,
                    rr_ratio=rr,
                    entry_reason=entry_reason,
                    bull_case=getattr(signal, "bull_case", "") or "",
                    bear_case=getattr(signal, "bear_case", "") or "",
                )
            except Exception:
                logger.debug("save_trade_thesis failed (non-fatal)", exc_info=True)
        self._emit("info",
                   f"Trade opened! {trade.direction} {trade.symbol} {lot_size:.2f} lots "
                   f"@ {trade.entry_price:.5f}  SL={trade.stop_loss:.5f}  "
                   f"TP1={trade.take_profit_1:.5f}  ticket={trade.broker_ticket}",
                   {"trade_id": trade.id, "ticket": trade.broker_ticket,
                    "lots": lot_size, "entry": trade.entry_price})
        logger.info(
            "TRADE OPENED: %s  %s %s  %.2f lots @ %.5f  ticket=%d",
            trade.id, trade.direction, trade.symbol,
            lot_size, trade.entry_price, trade.broker_ticket,
        )
        tp_summary = (
            f"TP1={trade.take_profit_1:.5f} TP2={trade.take_profit_2:.5f} "
            f"TP3={trade.take_profit_3:.5f}"
        )
        if trade.take_profit_4 > 0:
            tp_summary += f" TP4={trade.take_profit_4:.5f}(runner)"
        telegram_bot.send_message(
            f"📈 Trade opened: {trade.direction} {trade.symbol} "
            f"{lot_size} lots @ {trade.entry_price:.5f}  "
            f"SL={trade.stop_loss:.5f}  {tp_summary}"
        )
        return trade

    @staticmethod
    def _is_autotrading_disabled(message: str) -> bool:
        msg = message.lower()
        return "10017" in msg or "10027" in msg or "autotrading disabled" in msg

    def _confirm_position_open(self, ticket: int) -> bool:
        """Wait briefly for broker position visibility after order placement.

        Uses exponential backoff (250ms → 500ms → 1s) when the broker raises an
        exception, avoiding hammer during transient errors. Normal polling uses the
        configured poll interval.
        """
        timeout_s = max(0.0, settings.EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS)
        poll_s = max(0.05, settings.EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS)
        backoff_ms = [250, 500, 1000]
        deadline = time.monotonic() + timeout_s
        attempt = 0

        while True:
            try:
                positions = self._broker.get_open_positions()
                if any(p.ticket == ticket for p in positions):
                    return True
            except Exception:
                logger.exception("Failed while confirming broker position visibility")
                sleep_s = backoff_ms[min(attempt, len(backoff_ms) - 1)] / 1000.0
                attempt += 1

            if time.monotonic() >= deadline:
                return False

            time.sleep(sleep_s if "sleep_s" in dir() else poll_s)
            # Reset backoff on a clean (non-exception) iteration
            if "sleep_s" in dir():
                del sleep_s
            attempt = 0
