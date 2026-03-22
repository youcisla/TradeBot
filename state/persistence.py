"""Trade state persistence & reconciliation layer.

Wraps the database so that the rest of the bot treats trade state as an
opaque store — read on startup, write on every change.
"""

from __future__ import annotations

import logging
from typing import Callable

from broker.connector import BrokerConnector, PositionInfo
from database.db import Database
from models.trade import Trade

logger = logging.getLogger(__name__)


class StatePersistence:
    """Manages trade state in SQLite and provides reconciliation."""

    def __init__(self, db: Database, broker: BrokerConnector) -> None:
        self._db = db
        self._broker = broker

    # ── basic CRUD ───────────────────────────────────────────────────────

    def save_trade(self, trade: Trade) -> None:
        """Persist a trade (insert or update)."""
        self._db.upsert_trade(trade)
        logger.debug("State persisted: trade=%s status=%s", trade.id, trade.status)

    def get_open_trades(self) -> list[Trade]:
        """Load all non-closed trades from DB."""
        return self._db.get_open_trades()

    def get_trade(self, trade_id: str) -> Trade | None:
        return self._db.get_trade(trade_id)

    # ── reconciliation ───────────────────────────────────────────────────

    def reconcile(self, send_alert: Callable[[str], None] = lambda msg: None) -> list[Trade]:
        """Compare DB state against broker state and resolve mismatches.

        Returns the final list of open trades after reconciliation.
        """
        db_trades = self._db.get_open_trades()
        broker_positions = self._broker.reconcile()

        db_map: dict[int, Trade] = {t.broker_ticket: t for t in db_trades if t.broker_ticket}
        broker_map: dict[int, PositionInfo] = {p.ticket: p for p in broker_positions}

        mismatches: list[str] = []

        # 1. Trades in DB but NOT on broker → mark closed, fetch real PnL
        for ticket, trade in db_map.items():
            if ticket not in broker_map:
                closed_pnl = self._broker.get_closed_pnl(ticket)
                pnl_str = f"pnl={closed_pnl:.2f}" if closed_pnl is not None else "pnl=unknown"
                msg = (
                    f"RECONCILE: trade {trade.id} (ticket {ticket}) "
                    f"in DB but broker says closed — {pnl_str}"
                )
                logger.critical(msg)
                mismatches.append(msg)
                trade.status = "CLOSED"
                trade.close_reason = "RECONCILE_BROKER_CLOSED"
                if closed_pnl is not None:
                    trade.pnl = closed_pnl
                self.save_trade(trade)

        # 2. Positions on broker but NOT in DB → adopt them
        for ticket, pos in broker_map.items():
            if ticket not in db_map:
                msg = f"RECONCILE: broker position ticket {ticket} ({pos.symbol}) not in DB — adopting"
                logger.critical(msg)
                mismatches.append(msg)
                # Try to recover TP identity from comment
                tp1 = tp2 = tp3 = 0.0
                if hasattr(pos, 'comment') and pos.comment:
                    if "_TP1" in pos.comment:
                        tp1 = getattr(pos, 'take_profit', 0.0) or 0.0
                    elif "_TP2" in pos.comment:
                        tp2 = getattr(pos, 'take_profit', 0.0) or 0.0
                    elif "_TP3" in pos.comment:
                        tp3 = getattr(pos, 'take_profit', 0.0) or 0.0
                orphan = Trade(
                    symbol=pos.symbol,
                    strategy="UNKNOWN_RECONCILED",
                    direction=pos.direction,
                    entry_price=pos.entry_price,
                    lot_size=pos.lot_size,
                    stop_loss=pos.stop_loss,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    take_profit_3=tp3,
                    broker_ticket=pos.ticket,
                    status="OPEN",
                )
                self.save_trade(orphan)
                db_trades.append(orphan)

        # 3. Both exist but SL or lot_size differ → adopt broker values
        for ticket in set(db_map) & set(broker_map):
            trade = db_map[ticket]
            pos = broker_map[ticket]
            diffs: list[str] = []
            if abs(trade.lot_size - pos.lot_size) > 0.001:
                diffs.append(f"lot_size DB={trade.lot_size} broker={pos.lot_size}")
                trade.lot_size = pos.lot_size
            if abs(trade.stop_loss - pos.stop_loss) > 0.00001:
                diffs.append(f"stop_loss DB={trade.stop_loss:.5f} broker={pos.stop_loss:.5f}")
                trade.stop_loss = pos.stop_loss
            if diffs:
                msg = f"RECONCILE: trade {trade.id} ticket {ticket}: {', '.join(diffs)}"
                logger.critical(msg)
                mismatches.append(msg)
                self.save_trade(trade)

        if mismatches:
            alert_text = "⚠️ RECONCILIATION MISMATCHES:\n" + "\n".join(mismatches)
            send_alert(alert_text)
        else:
            logger.info("Reconciliation complete — no mismatches.")

        return self._db.get_open_trades()
