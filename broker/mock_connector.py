"""Mock broker connector for Phase 1 testing.

Simulates order placement, position tracking, and price movement so that
the entire bot loop can run end-to-end without a real broker.  Every
action is logged to the Python logger.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta

from broker.connector import BrokerConnector, OrderResult, PositionInfo
from models.market_data import Candle

logger = logging.getLogger(__name__)

_NEXT_TICKET = 100_000


def _ticket() -> int:
    global _NEXT_TICKET
    _NEXT_TICKET += 1
    return _NEXT_TICKET


class MockConnector(BrokerConnector):
    """In-memory mock broker.  Prices wobble randomly around a base so that
    TP/SL monitoring has something to react to.
    """

    def __init__(self, starting_balance: float = 10_000.0,
                 base_price: float = 1.1050) -> None:
        self._balance = starting_balance
        self._equity = starting_balance
        self._base_price = base_price
        self._positions: dict[int, PositionInfo] = {}
        self._fills: dict[str, float] = {}          # order_id -> filled lots
        self._connected = False

    # ── account ──────────────────────────────────────────────────────────

    def connect(self) -> bool:
        self._connected = True
        logger.info("[MockBroker] Connected (demo, balance=%.2f)", self._balance)
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("[MockBroker] Disconnected")

    def get_balance(self) -> float:
        return self._balance

    def get_equity(self) -> float:
        floating = sum(p.pnl for p in self._positions.values())
        return self._balance + floating

    # ── market data ──────────────────────────────────────────────────────

    def _wobble(self) -> float:
        """Return the base price with a small random offset."""
        return round(self._base_price + random.uniform(-0.0020, 0.0020), 5)

    def get_tick(self, symbol: str) -> dict[str, float]:
        price = self._wobble()
        spread = round(random.uniform(0.5, 2.5) * 0.0001, 5)
        bid = price
        ask = round(price + spread, 5)
        return {"bid": bid, "ask": ask, "spread": spread, "volume": random.uniform(100, 5000)}

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        candles: list[Candle] = []
        now = datetime.utcnow()
        for i in range(count, 0, -1):
            o = self._wobble()
            c = self._wobble()
            h = max(o, c) + random.uniform(0, 0.0010)
            l = min(o, c) - random.uniform(0, 0.0010)
            candles.append(Candle(
                timestamp=now - timedelta(hours=i),
                open=round(o, 5),
                high=round(h, 5),
                low=round(l, 5),
                close=round(c, 5),
                volume=random.uniform(100, 5000),
            ))
        return candles

    # ── order management ─────────────────────────────────────────────────

    def place_order(self, symbol: str, direction: str, lot_size: float,
                    sl: float, tp: float | None = None,
                    comment: str = "") -> OrderResult:
        ticket = _ticket()
        tick = self.get_tick(symbol)
        fill_price = tick["ask"] if direction == "BUY" else tick["bid"]
        order_id = f"MOCK-{ticket}"
        self._fills[order_id] = lot_size

        pos = PositionInfo(
            ticket=ticket, symbol=symbol, direction=direction,
            lot_size=lot_size, entry_price=fill_price,
            stop_loss=sl, current_price=fill_price, pnl=0.0,
        )
        self._positions[ticket] = pos

        logger.info(
            "[MockBroker] ORDER %s %s %.2f lots %s @ %.5f  SL=%.5f  %s",
            direction, symbol, lot_size, order_id, fill_price, sl, comment,
        )
        return OrderResult(
            success=True, order_id=order_id, broker_ticket=ticket,
            filled_lots=lot_size, fill_price=fill_price,
            message="Mock fill OK",
        )

    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        if ticket not in self._positions:
            logger.warning("[MockBroker] modify_order: ticket %d not found", ticket)
            return False
        if sl is not None:
            self._positions[ticket].stop_loss = sl
        logger.info("[MockBroker] MODIFY ticket=%d  new_sl=%s  new_tp=%s", ticket, sl, tp)
        return True

    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        if ticket not in self._positions:
            logger.warning("[MockBroker] close_partial: ticket %d not found", ticket)
            return False
        pos = self._positions[ticket]
        pos.lot_size = round(pos.lot_size - lot_size, 2)
        logger.info(
            "[MockBroker] PARTIAL CLOSE ticket=%d  closed=%.2f lots  remaining=%.2f",
            ticket, lot_size, pos.lot_size,
        )
        if pos.lot_size <= 0:
            del self._positions[ticket]
        return True

    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        if ticket not in self._positions:
            logger.warning("[MockBroker] close_order: ticket %d not found", ticket)
            return False
        del self._positions[ticket]
        logger.info("[MockBroker] FULL CLOSE ticket=%d", ticket)
        return True

    def get_open_positions(self) -> list[PositionInfo]:
        # Update floating P&L
        for pos in self._positions.values():
            tick = self.get_tick(pos.symbol)
            cp = tick["bid"] if pos.direction == "BUY" else tick["ask"]
            pos.current_price = cp
            if pos.direction == "BUY":
                pos.pnl = round((cp - pos.entry_price) * pos.lot_size * 100_000, 2)
            else:
                pos.pnl = round((pos.entry_price - cp) * pos.lot_size * 100_000, 2)
        return list(self._positions.values())

    def get_fill_size(self, order_id: str) -> float:
        return self._fills.get(order_id, 0.0)

    def reconcile(self) -> list[PositionInfo]:
        logger.info("[MockBroker] Reconciliation requested — returning %d positions",
                    len(self._positions))
        return self.get_open_positions()
