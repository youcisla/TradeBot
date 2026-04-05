"""Mock Broker for Historical Backtesting.

Simulates the MT5 broker environment offline by:
1. Advancing through historical candles bar-by-bar
2. Tracking virtual balance and equity
3. Processing simulated orders with proper SL/TP, partial closes, and
   symbol-aware PnL calculation.
"""

from __future__ import annotations

import csv
import logging
import uuid
from datetime import UTC, datetime

from broker.connector import BrokerConnector, OrderResult, PositionInfo
from config.symbols import contract_size as _contract_size
from models.market_data import Candle

logger = logging.getLogger(__name__)


# Typical bid/ask spreads used when no real spread data is available.
# Values are in price units (not pips).
_TYPICAL_SPREADS: dict[str, float] = {
    "EURUSD": 0.00010, "GBPUSD": 0.00015, "USDJPY": 0.010,
    "USDCHF": 0.00012, "AUDUSD": 0.00013, "USDCAD": 0.00014,
    "USDMXN": 0.00100, "USDZAR": 0.00200,
    "EURGBP": 0.00012, "EURJPY": 0.014,  "GBPJPY": 0.020,
    "AUDJPY": 0.015,   "EURAUD": 0.00020, "GBPAUD": 0.00025,
    "EURCHF": 0.00015, "GBPCHF": 0.00020, "AUDNZD": 0.00020,
    "CADJPY": 0.015,   "CHFJPY": 0.015,   "NZDUSD": 0.00014,
    "XAUUSD": 0.30,    "XAGUSD": 0.03,    "USOIL": 0.05, "UKOIL": 0.05,
    "BTCUSD": 50.0,    "ETHUSD": 5.0,     "LTCUSD": 0.30,
    "XRPUSD": 0.0003,  "SOLUSD": 0.10,
}


class MockBroker(BrokerConnector):
    """Offline broker simulator for backtesting."""

    # Commission rate per lot per side (round-turn = 2×).
    # Default 0.0001 matches a typical raw-spread ECN account (~$10/standard lot).
    COMMISSION_PER_LOT_PER_SIDE: float = 0.0001

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        commission_per_lot_per_side: float | None = None,
    ) -> None:
        self._connected = False
        self._balance = initial_balance
        self._commission_rate: float = (
            commission_per_lot_per_side
            if commission_per_lot_per_side is not None
            else self.COMMISSION_PER_LOT_PER_SIDE
        )
        self.total_commission_paid: float = 0.0  # accumulated for reporting

        self.history: list[Candle] = []
        self.current_idx: int = -1
        self.current_candle: Candle | None = None

        # ticket → PositionInfo
        self.positions: dict[int, PositionInfo] = {}
        self._next_ticket = 1

        # All closed (full or partial) position records for reporting
        self.closed_positions: list[PositionInfo] = []

    # ── Data loading ─────────────────────────────────────────────────────

    def load_data(self, csv_path: str) -> None:
        """Load historical candle data from CSV (columns: time, open, high, low, close, tick_volume)."""
        self.history.clear()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = int(row["time"])
                except (ValueError, KeyError):
                    continue
                dt = datetime.fromtimestamp(ts, tz=UTC)
                candle = Candle(
                    timestamp=dt,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("tick_volume", row.get("volume", 0))),
                )
                self.history.append(candle)
        self.history.sort(key=lambda c: c.timestamp)
        logger.info("MockBroker loaded %d historical candles", len(self.history))
        self.current_idx = -1

    # ── Simulation control ───────────────────────────────────────────────

    def step(self) -> bool:
        """Advance the simulated clock by one candle. Returns False at EOF."""
        if self.current_idx + 1 >= len(self.history):
            return False
        self.current_idx += 1
        self.current_candle = self.history[self.current_idx]
        self._process_orders(self.current_candle)
        return True

    def _pnl(self, symbol: str, direction: str, entry: float, exit_: float, lot_size: float) -> float:
        """Calculate realised PnL using the symbol's contract size."""
        cs = _contract_size(symbol)
        diff = (exit_ - entry) if direction == "BUY" else (entry - exit_)
        return diff * cs * lot_size

    def _process_orders(self, candle: Candle) -> None:
        """Check every open position against the new candle's high/low for SL/TP hits."""
        to_close: list[tuple[int, bool]] = []  # (ticket, hit_sl)

        for ticket, p in self.positions.items():
            tp = p.take_profit  # always use the dedicated take_profit field
            hit_sl = False
            hit_tp = False
            close_price = 0.0

            if p.direction == "BUY":
                if p.stop_loss > 0 and candle.low <= p.stop_loss:
                    hit_sl = True
                    # Slippage: if open gaps through SL, fill at open (worse); else at SL
                    close_price = candle.open if candle.open < p.stop_loss else p.stop_loss
                elif tp and tp > 0 and candle.high >= tp:
                    hit_tp = True
                    close_price = candle.open if candle.open > tp else tp
            elif p.direction == "SELL":
                if p.stop_loss > 0 and candle.high >= p.stop_loss:
                    hit_sl = True
                    close_price = candle.open if candle.open > p.stop_loss else p.stop_loss
                elif tp and tp > 0 and candle.low <= tp:
                    hit_tp = True
                    close_price = candle.open if candle.open < tp else tp

            if hit_sl or hit_tp:
                pnl = self._pnl(p.symbol, p.direction, p.entry_price, close_price, p.lot_size)
                p.current_price = close_price
                p.pnl = pnl
                # Deduct exit commission (one side — entry was already charged)
                exit_commission = self._commission_rate * p.lot_size
                self._balance += pnl - exit_commission
                self.total_commission_paid += exit_commission
                to_close.append((ticket, hit_sl))

        for ticket, was_sl in to_close:
            reason = "SL" if was_sl else "TP"
            pos = self.positions.pop(ticket)
            logger.debug("[%s] %s %s closed at %s pnl=%.2f",
                         reason, pos.symbol, pos.direction,
                         self.current_candle.timestamp, pos.pnl)
            self.closed_positions.append(pos)

    # ── BrokerConnector interface ────────────────────────────────────────

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def get_balance(self) -> float:
        return self._balance

    def get_equity(self) -> float:
        """Balance plus floating PnL on all open positions."""
        equity = self._balance
        if not self.current_candle:
            return equity
        c = self.current_candle.close
        for p in self.positions.values():
            equity += self._pnl(p.symbol, p.direction, p.entry_price, c, p.lot_size)
        return equity

    def get_tick(self, symbol: str) -> dict[str, float]:
        if not self.current_candle:
            raise RuntimeError("Requested tick before loading data")
        c = self.current_candle.close
        spread = _TYPICAL_SPREADS.get(symbol, 0.0001)
        return {
            "bid": c,
            "ask": c + spread,
            "spread": spread,
            "volume": self.current_candle.volume,
        }

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        if self.current_idx < 0:
            return []
        start = max(0, self.current_idx - count + 1)
        return self.history[start : self.current_idx + 1]

    def place_order(self, symbol: str, direction: str, lot_size: float,
                    sl: float, tp: float | None = None,
                    comment: str = "") -> OrderResult:
        if not self.current_candle:
            return OrderResult(success=False, message="No market data")

        entry_price = self.current_candle.close
        ticket = self._next_ticket
        self._next_ticket += 1

        pos = PositionInfo(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp or 0.0,   # stored in the correct field — no hack
            current_price=entry_price,
            pnl=0.0,
            comment=comment,
        )
        self.positions[ticket] = pos

        # Deduct entry commission immediately (one side)
        entry_commission = self._commission_rate * lot_size
        self._balance -= entry_commission
        self.total_commission_paid += entry_commission

        logger.debug("[MOCK] %s %s %.2f lots @ %.5f SL=%.5f TP=%.5f commission=%.4f",
                     direction, symbol, lot_size, entry_price, sl, tp or 0.0,
                     entry_commission)
        return OrderResult(
            success=True,
            order_id=str(uuid.uuid4()),
            broker_ticket=ticket,
            filled_lots=lot_size,
            fill_price=entry_price,
            message="MOCK_FILL",
        )

    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        if ticket not in self.positions:
            return False
        if sl is not None:
            self.positions[ticket].stop_loss = sl
        if tp is not None:
            self.positions[ticket].take_profit = tp  # correct field
        return True

    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        """Partially close *lot_size* of an open position.

        Creates a closed record for the reduced portion and reduces the
        remaining lots on the live position.  If *lot_size* >= position size,
        the full position is closed instead.
        """
        if ticket not in self.positions:
            return False
        pos = self.positions[ticket]
        if lot_size >= pos.lot_size:
            return self.close_order(ticket, symbol, direction)

        c = self.current_candle.close if self.current_candle else pos.entry_price
        pnl = self._pnl(symbol, pos.direction, pos.entry_price, c, lot_size)
        self._balance += pnl

        # Record the closed portion
        partial = PositionInfo(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            lot_size=lot_size,
            entry_price=pos.entry_price,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            current_price=c,
            pnl=pnl,
            comment=pos.comment + "_partial",
        )
        self.closed_positions.append(partial)

        # Reduce remaining lot_size
        pos.lot_size = round(pos.lot_size - lot_size, 2)
        return True

    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        if ticket not in self.positions:
            return False
        pos = self.positions.pop(ticket)
        c = self.current_candle.close if self.current_candle else pos.entry_price
        pnl = self._pnl(symbol, pos.direction, pos.entry_price, c, pos.lot_size)
        pos.current_price = c
        # Deduct exit commission (other side of round-turn)
        exit_commission = self._commission_rate * pos.lot_size
        self._balance -= exit_commission
        self.total_commission_paid += exit_commission
        pos.pnl = pnl
        self._balance += pnl
        self.closed_positions.append(pos)
        return True

    def get_open_positions(self) -> list[PositionInfo]:
        """Update floating PnL and return all open positions."""
        if not self.current_candle:
            return list(self.positions.values())
        c = self.current_candle.close
        for p in self.positions.values():
            p.pnl = self._pnl(p.symbol, p.direction, p.entry_price, c, p.lot_size)
            p.current_price = c
        return list(self.positions.values())

    def get_fill_size(self, order_id: str) -> float:
        return 1.0  # always fully filled in simulation

    def reconcile(self) -> list[PositionInfo]:
        return self.get_open_positions()
