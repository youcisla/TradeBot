"""Trade state persistence & reconciliation layer.

Wraps the database so that the rest of the bot treats trade state as an
opaque store — read on startup, write on every change.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Callable

from broker.connector import BrokerConnector, PositionInfo
from config.symbols import pip_value
from database.db import Database
from models.trade import Trade
from utils.mesh_bus import record_call

logger = logging.getLogger(__name__)


class StatePersistence:
    """Manages trade state in SQLite and provides reconciliation."""

    def __init__(self, db: Database, broker: BrokerConnector) -> None:
        self._db = db
        self._broker = broker
        self._last_closed_deal_sync: datetime | None = None

    # ── basic CRUD ───────────────────────────────────────────────────────

    def save_trade(self, trade: Trade) -> None:
        """Persist a trade (insert or update)."""
        _t0 = time.monotonic()
        self._db.upsert_trade(trade)
        record_call("state", (time.monotonic() - _t0) * 1000.0, True)
        logger.debug("State persisted: trade=%s status=%s", trade.id, trade.status)

    def get_open_trades(self) -> list[Trade]:
        """Internal use only — called by reconcile() to diff DB vs broker.

        External callers must use broker.get_open_positions() for live state.
        DB is a metadata/audit store, not a source of truth for open positions.
        """
        return self._db.get_open_trades()

    def get_trade(self, trade_id: str) -> Trade | None:
        return self._db.get_trade(trade_id)

    # ── reconciliation ───────────────────────────────────────────────────

    def reconcile(self, send_alert: Callable[[str], None] = lambda msg: None) -> list[Trade]:
        """Compare DB state against broker state and resolve mismatches.

        Returns the final list of open trades after reconciliation.
        """
        _t0 = time.monotonic()
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
            # Broker-side price normalization can round SL by a fraction of a pip.
            # Use symbol-aware tolerance to prevent false-positive critical events.
            sl_tolerance = max(pip_value(trade.symbol) * 0.5, 0.00001)
            if abs(trade.stop_loss - pos.stop_loss) > sl_tolerance:
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

        record_call("state_reconcile", (time.monotonic() - _t0) * 1000.0, True)
        return self._db.get_open_trades()

    # ── periodic MT5 → DB sync ─────────────────────────────────────────

    def sync_mt5_to_db(self) -> None:
        """Push live MT5 state into the DB every sync cycle.

        Covers:
        - Open positions: lot_size, stop_loss, take_profit, current_price
        - Closed deals since last sync: new CLOSED trades with P&L
        - Account equity and balance → bot_status
        """
        _t0 = time.monotonic()
        self._sync_open_trades()
        self._sync_closed_trades()
        self._sync_account_status()
        logger.debug("MT5→DB sync complete in %.1fms", (time.monotonic() - _t0) * 1000.0)

    def _sync_open_trades(self) -> None:
        """Overwrite open-trade DB rows with live MT5 values."""
        import logging
        _log = logging.getLogger(__name__ + "._sync_open_trades")
        broker_positions = self._broker.get_open_positions()
        if not broker_positions:
            return
        db_trades = {t.broker_ticket: t for t in self._db.get_open_trades()}
        for pos in broker_positions:
            if not pos.ticket:
                continue
            if pos.ticket in db_trades:
                trade = db_trades[pos.ticket]
                changed: list[str] = []
                if abs(trade.lot_size - pos.lot_size) > 0.0001:
                    changed.append(f"lot {trade.lot_size}→{pos.lot_size}")
                    trade.lot_size = pos.lot_size
                if abs(trade.stop_loss - pos.stop_loss) > 0.00001:
                    changed.append(f"sl {trade.stop_loss:.5f}→{pos.stop_loss:.5f}")
                    trade.stop_loss = pos.stop_loss
                if pos.take_profit and abs(trade.take_profit_1 - pos.take_profit) > 0.00001:
                    trade.take_profit_1 = pos.take_profit
                if pos.current_price and trade.current_price != pos.current_price:
                    trade.current_price = pos.current_price
                if changed:
                    self.save_trade(trade)
                    _log.debug("Synced ticket %d: %s", pos.ticket, ", ".join(changed))
            else:
                # Orphan: in MT5 but not in DB — create minimal entry
                new_trade = Trade(
                    symbol=pos.symbol,
                    strategy="MT5_SYNC",
                    direction=pos.direction,
                    entry_price=pos.entry_price,
                    lot_size=pos.lot_size,
                    stop_loss=pos.stop_loss,
                    take_profit_1=pos.take_profit or 0.0,
                    status="OPEN",
                    open_time=datetime.now(UTC),
                    broker_ticket=pos.ticket,
                    current_price=pos.current_price or pos.entry_price,
                )
                self.save_trade(new_trade)
                _log.warning("MT5→DB: adopted orphan ticket %d (%s) into DB", pos.ticket, pos.symbol)

    def _sync_closed_trades(self) -> None:
        """Fetch closed deals from MT5 since last sync and upsert as CLOSED trades."""
        import logging
        from datetime import UTC, timedelta
        _log = logging.getLogger(__name__ + "._sync_closed_trades")

        try:
            import MetaTrader5 as mt5
        except Exception:
            _log.debug("MT5 not available for closed deal sync")
            return

        now_utc = datetime.now(UTC)
        # First sync: go back 7 days to catch recently closed trades
        if self._last_closed_deal_sync is None:
            sync_start = now_utc - timedelta(days=7)
        else:
            sync_start = self._last_closed_deal_sync

        try:
            deals = mt5.history_deals_get(sync_start, now_utc)
        except Exception as exc:
            _log.warning("history_deals_get failed: %s", exc)
            return

        if not deals:
            self._last_closed_deal_sync = now_utc
            return

        # Group deals by position ticket
        by_ticket: dict[int, list] = {}
        for deal in deals:
            if deal.position_id:
                by_ticket.setdefault(deal.position_id, []).append(deal)

        synced = 0
        for ticket, ticket_deals in by_ticket.items():
            # Skip if already CLOSED in DB (idempotent — won't re-create)
            existing = self._db.get_trade_by_broker_ticket(ticket)
            if existing and existing.status == "CLOSED":
                continue

            first = ticket_deals[0]
            last = ticket_deals[-1]
            pnl = float(sum(d.profit for d in ticket_deals))
            swap = float(sum(d.swap for d in ticket_deals))
            commission = float(sum(abs(d.commission) for d in ticket_deals))
            entry_price = float(first.price)
            close_price = float(last.price)
            direction = "BUY" if first.type_enum in (
                mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT,
                mt5.ORDER_TYPE_BUY_STOP,
            ) else "SELL"

            # Resolve symbol from first deal
            symbol = str(first.symbol) if first.symbol else ""
            if not symbol:
                _log.debug("Skipping deal ticket=%d — no symbol", ticket)
                continue

            trade = Trade(
                id=f"MT5-{ticket}",
                symbol=symbol,
                strategy="MT5_SYNC",
                direction=direction,
                entry_price=entry_price,
                lot_size=float(first.volume),
                stop_loss=0.0,
                take_profit_1=0.0,
                take_profit_2=0.0,
                take_profit_3=0.0,
                take_profit_4=0.0,
                tp1_lots=0.0, tp2_lots=0.0, tp3_lots=0.0, tp4_lots=0.0,
                tp1_hit=False, tp2_hit=False, tp3_hit=False, tp4_hit=False,
                status="CLOSED",
                open_time=datetime.fromtimestamp(first.time, tz=UTC),
                close_time=datetime.fromtimestamp(last.time, tz=UTC),
                pnl=round(pnl, 2),
                current_price=close_price,
                commission=round(commission, 2),
                swap=round(swap, 2),
                close_reason="MT5_SYNC",
                broker_ticket=ticket,
                spread_at_entry=0.0,
            )
            self.save_trade(trade)
            synced += 1

        self._last_closed_deal_sync = now_utc
        if synced:
            _log.info("MT5→DB: synced %d new closed trade(s)", synced)

    def _sync_account_status(self) -> None:
        """Push live equity and balance from MT5 to bot_status."""
        import logging
        _log = logging.getLogger(__name__ + "._sync_account_status")
        equity = self._broker.get_equity()
        balance = self._broker.get_balance()
        positions = self._broker.get_open_positions()
        open_trades = len(positions)

        # Compute daily P&L from MT5 deal history (midnight UTC → now)
        daily_pnl = 0.0
        try:
            daily_pnl = self._broker.get_daily_pnl()
        except Exception:
            pass

        try:
            self._db.update_bot_status(
                state="running",
                equity=equity,
                open_trades=open_trades,
                daily_pnl=round(daily_pnl, 2),
                balance=balance,
            )
        except Exception as exc:
            _log.warning("update_bot_status failed: %s", exc)
