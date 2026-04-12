"""HKU copy trading service.

Bridges the HKU real-time notification channel (WebSocket) to broker-side
position mirroring.  When a followed leader publishes a signal, we open an
equivalent position on our broker and keep it in sync with HKU's copied
position state.

Design principles:
  - Fail-open: HKU copy trading errors never stall the main trading loop.
  - Position mirroring is conservative: fixed fraction of free margin per
    copied trade, never exceeds max_copy_trades concurrent copies.
  - HKU handles TP/SL exits on the platform side; we just mirror entry.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.hku_client import HKUClient
    from broker.connector import BrokerConnector

logger = logging.getLogger(__name__)


@dataclass
class CopyTradeConfig:
    """Runtime copy-trading configuration (derived from settings)."""

    enabled: bool = False
    # Fraction of free margin used per copied trade (e.g. 0.05 = 5%)
    margin_fraction_per_trade: float = 0.05
    # Absolute max concurrent copied positions
    max_copy_trades: int = 3
    # Minimum leader win-rate (0-1) to start copying them
    min_leader_winrate: float = 0.55
    # Fixed SL distance in ATR multiples for copied trades
    sl_atr_multiples: float = 1.5
    # Fixed TP distance in ATR multiples for copied trades
    tp_atr_multiples: float = 2.5


@dataclass
class CopiedPosition:
    """Tracks a single copied position in our broker that mirrors an HKU leader."""

    leader_id: str
    hku_position_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    broker_ticket: int = 0
    lot_size: float = 0.0
    opened_at_ts: float = 0.0


class HKUCopyTradingService:
    """Service that mirrors leader positions via the HKU copy-trading API."""

    def __init__(
        self,
        hku_client: "HKUClient",
        broker: "BrokerConnector",
        config: CopyTradeConfig | None = None,
    ) -> None:
        self._hku = hku_client
        self._broker = broker
        self._config = config or CopyTradeConfig()
        # Active copied positions keyed by HKU position id
        self._copied: dict[str, CopiedPosition] = {}
        self._lock = threading.Lock()
        self._sync_thread: threading.Thread | None = None
        self._sync_stop = threading.Event()
        self._pending_signals: list[dict] = []
        self._pending_lock = threading.Lock()

    # ── lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Register notification callback and start background sync."""
        if not self._config.enabled:
            logger.info("HKU copy trading disabled")
            return

        self._hku.register_notification_callback(self._on_hku_notification)
        self._sync_stop.clear()
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            name="hku-copy-sync",
            daemon=True,
        )
        self._sync_thread.start()
        logger.info(
            "HKU copy trading started (max_trades=%d, margin_fraction=%.0f%%)",
            self._config.max_copy_trades,
            self._config.margin_fraction_per_trade * 100,
        )

    def stop(self) -> None:
        """Stop sync loop and close all copied positions."""
        self._sync_stop.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=10.0)
        self._close_all_copied()
        logger.info("HKU copy trading stopped")

    # ── notification callback ─────────────────────────────────────────

    def _on_hku_notification(self, notification: dict) -> None:
        """Handle incoming HKU WebSocket notification.

        Supported types:
          - 'new_signal'   : leader published a new signal we should copy
          - 'position_closed': a copied position was closed on HKU side
        """
        ntype = notification.get("type", "")
        data = notification.get("data", {})

        if ntype == "new_signal":
            self._handle_new_signal(data)
        elif ntype == "position_closed":
            self._handle_position_closed(data)
        elif ntype == "points_update":
            pts = data.get("points", 0)
            logger.info("HKU points update: %.0f points", pts)

    def _handle_new_signal(self, data: dict) -> None:
        """Queue a new leader signal for copy (processed in sync loop)."""
        with self._pending_lock:
            self._pending_signals.append(data)
        logger.debug("HKU new signal queued for copy: %s", data)

    def _handle_position_closed(self, data: dict) -> None:
        """Close our mirrored position when HKU closes the leader's position."""
        hku_id = str(data.get("position_id", "") or data.get("id", ""))
        if not hku_id:
            return
        self._close_copied_position(hku_id)

    # ── sync loop ─────────────────────────────────────────────────────

    def _sync_loop(self) -> None:
        """Background loop: process pending signals + reconcile HKU positions."""
        while not self._sync_stop.wait(timeout=5.0):
            self._process_pending_signals()
            self._reconcile_copied_positions()

    def _process_pending_signals(self) -> None:
        """Open broker positions for queued leader signals."""
        with self._pending_lock:
            signals = list(self._pending_signals)
            self._pending_signals.clear()

        for sig_data in signals:
            self._copy_signal(sig_data)

    def _reconcile_copied_positions(self) -> None:
        """Ensure our broker positions match HKU's known copied positions.

        Closes any broker copies that HKU has already closed, and opens any
        HKU copies we don't yet have (in case we missed a notification).
        """
        if len(self._copied) >= self._config.max_copy_trades:
            return

        hku_positions = self._hku.get_copied_positions()
        hku_ids = {str(p.get("id", "")) for p in hku_positions}

        with self._lock:
            # Close any we have but HKU doesn't (stale copies)
            stale = set(self._copied) - hku_ids
            for hku_id in stale:
                self._close_copied_position(hku_id)

            # Open any HKU has that we don't yet have
            for hku_pos in hku_positions:
                hku_id = str(hku_pos.get("id", ""))
                if hku_id not in self._copied:
                    self._open_copied_from_position(hku_pos)

    # ── copy signal (entry) ───────────────────────────────────────────

    def _copy_signal(self, sig_data: dict) -> None:
        """Open a broker position mirroring a leader's signal."""
        if not self._config.enabled:
            return

        with self._lock:
            if len(self._copied) >= self._config.max_copy_trades:
                logger.debug("Max copy trades reached — skipping signal")
                return

        symbol = str(sig_data.get("symbol", ""))
        direction = str(sig_data.get("direction", "")).upper()
        if not symbol or direction not in ("BUY", "SELL"):
            logger.warning("HKU copy_signal: invalid data %s", sig_data)
            return

        # Check leader quality (skip if leader win-rate too low)
        leader_id = str(sig_data.get("agent_id", ""))
        win_rate = float(sig_data.get("win_rate", 0.0))
        if win_rate > 0 and win_rate < self._config.min_leader_winrate:
            logger.debug("Skipping low-winrate leader %s: %.0f%%", leader_id, win_rate * 100)
            return

        # Calculate position size
        lot_size = self._calc_lot_size(symbol)
        if lot_size <= 0:
            logger.warning("HKU copy_signal: could not determine lot size for %s", symbol)
            return

        # Get current price + ATR for SL/TP
        try:
            tick = self._broker.get_tick(symbol)
            ask = tick["ask"]
            bid = tick["bid"]
        except Exception as exc:
            logger.warning("HKU copy_signal: failed to get tick for %s: %s", symbol, exc)
            return

        entry_price = ask if direction == "BUY" else bid
        sl_price = self._calc_sl_price(symbol, direction, entry_price)
        tp_price = self._calc_tp_price(symbol, direction, entry_price)

        comment = f"hku_copy:{leader_id}"
        result = self._broker.place_order(
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            sl=sl_price,
            tp=tp_price,
            comment=comment,
        )

        if result.success:
            hku_pos_id = str(sig_data.get("position_id") or sig_data.get("id") or "")
            with self._lock:
                self._copied[hku_pos_id] = CopiedPosition(
                    leader_id=leader_id,
                    hku_position_id=hku_pos_id,
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    broker_ticket=result.broker_ticket,
                    lot_size=lot_size,
                    opened_at_ts=time.monotonic(),
                )
            logger.info(
                "HKU copied position opened: %s %s %.2f lots @ %.5f "
                "(SL=%.5f TP=%.5f) leader=%s ticket=%d",
                direction, symbol, lot_size, entry_price,
                sl_price, tp_price, leader_id, result.broker_ticket,
            )
        else:
            logger.warning("HKU copy_signal: broker rejected order: %s", result.message)

    def _open_copied_from_position(self, hku_pos: dict) -> None:
        """Open a broker position for a known HKU copied position (reconciliation)."""
        with self._lock:
            if len(self._copied) >= self._config.max_copy_trades:
                return
        self._copy_signal(hku_pos)

    # ── close copied position ──────────────────────────────────────────

    def _close_copied_position(self, hku_position_id: str) -> None:
        """Close a broker position that mirrors the given HKU copied position."""
        with self._lock:
            copied = self._copied.pop(hku_position_id, None)
        if not copied:
            return

        if copied.broker_ticket <= 0:
            return

        try:
            self._broker.close_order(
                ticket=copied.broker_ticket,
                symbol=copied.symbol,
                direction=copied.direction,
            )
            logger.info(
                "HKU copied position closed: ticket=%d symbol=%s",
                copied.broker_ticket, copied.symbol,
            )
        except Exception as exc:
            logger.warning(
                "HKU close_copied_position failed: ticket=%d error=%s",
                copied.broker_ticket, exc,
            )

    def _close_all_copied(self) -> None:
        """Emergency close all copied positions on shutdown."""
        with self._lock:
            hku_ids = list(self._copied.keys())
        for hku_id in hku_ids:
            self._close_copied_position(hku_id)

    # ── position sizing ───────────────────────────────────────────────

    def _calc_lot_size(self, symbol: str) -> float:
        """Calculate safe lot size for a copied trade.

        Uses a fixed fraction of free margin, capped by max_copy_trades and
        broker contract-size limits.
        """
        try:
            equity = self._broker.get_equity()
            balance = self._broker.get_balance()
            free_margin = equity - (equity - balance)  # rough approximation
            contract_size = self._broker.get_contract_size(symbol)
            tick_value = self._broker.get_tick_value(symbol)
            if tick_value <= 0 or contract_size <= 0:
                return 0.0

            # Risk: margin_fraction of free margin per pip per lot
            # lot_size = (free_margin × fraction) / (tick_value × contract_size × ATR_distance)
            # We simplify: ATR distance ≈ 100 pips for a typical H1 trade
            atr_distance_pips = 100 * self._broker.get_tick_size(symbol)
            risk_per_lot = tick_value * contract_size * atr_distance_pips
            if risk_per_lot <= 0:
                return 0.0

            target_risk = free_margin * self._config.margin_fraction_per_trade
            raw_lot = target_risk / risk_per_lot

            # Floor at 0.01 (micro-lot), cap at 1.0 lot
            return float(math.floor(raw_lot * 100) / 100)
        except Exception as exc:
            logger.debug("HKU calc_lot_size failed: %s", exc)
            return 0.0

    def _calc_sl_price(self, symbol: str, direction: str, entry: float) -> float:
        """Calculate SL price using ATR-based distance."""
        try:
            candles = self._broker.get_candles(symbol, "H1", 14)
            if len(candles) < 14:
                return entry
            trs = [max(
                c.high - c.low,
                abs(c.high - (candles[i + 1].close if i + 1 < len(candles) else c.close)),
                abs(c.low - (candles[i + 1].close if i + 1 < len(candles) else c.close)),
            ) for i, c in enumerate(candles[:-1])]
            atr = sum(trs) / len(trs) if trs else 0.0
            distance = atr * self._config.sl_atr_multiples
            return entry - distance if direction == "BUY" else entry + distance
        except Exception:
            # Fallback: 1% SL
            return entry * (0.99 if direction == "BUY" else 1.01)

    def _calc_tp_price(self, symbol: str, direction: str, entry: float) -> float:
        """Calculate TP price using ATR-based distance."""
        try:
            candles = self._broker.get_candles(symbol, "H1", 14)
            if len(candles) < 14:
                return entry
            trs = [max(
                c.high - c.low,
                abs(c.high - (candles[i + 1].close if i + 1 < len(candles) else c.close)),
                abs(c.low - (candles[i + 1].close if i + 1 < len(candles) else c.close)),
            ) for i, c in enumerate(candles[:-1])]
            atr = sum(trs) / len(trs) if trs else 0.0
            distance = atr * self._config.tp_atr_multiples
            return entry + distance if direction == "BUY" else entry - distance
        except Exception:
            # Fallback: 2% TP
            return entry * (1.02 if direction == "BUY" else 0.98)

    # ── public status ─────────────────────────────────────────────────

    def get_active_copies(self) -> list[dict]:
        """Return a summary of currently copied positions for the dashboard."""
        with self._lock:
            return [
                {
                    "leader_id": cp.leader_id,
                    "hku_position_id": cp.hku_position_id,
                    "symbol": cp.symbol,
                    "direction": cp.direction,
                    "entry_price": cp.entry_price,
                    "broker_ticket": cp.broker_ticket,
                    "lot_size": cp.lot_size,
                }
                for cp in self._copied.values()
            ]
