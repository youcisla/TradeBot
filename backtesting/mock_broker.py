"""Mock Broker for Historical Backtesting.

Simulates the MT5 broker environment offline by:
1. Advancing through historical candles bar-by-bar
2. Tracking virtual balance and equity
3. Processing simulated orders and executing SL/TP
"""

from __future__ import annotations

import csv
import logging
import uuid
from datetime import UTC, datetime
from typing import Iterator

from broker.connector import BrokerConnector, OrderResult, PositionInfo
from models.market_data import Candle

logger = logging.getLogger(__name__)

class MockBroker(BrokerConnector):
    """Offline broker simulator for backtesting."""

    def __init__(self, initial_balance: float = 10000.0) -> None:
        self._connected = False
        self._balance = initial_balance
        
        # Format: list of all historical candles
        self.history: list[Candle] = []
        
        # State pointing to the current "live" edge of history
        self.current_idx: int = -1
        self.current_candle: Candle | None = None
        
        # Open positions {"ticket": PositionInfo}
        self.positions: dict[int, PositionInfo] = {}
        self._next_ticket = 1
        
        # Closed positions for reporting
        self.closed_positions: list[PositionInfo] = []

    def load_data(self, csv_path: str) -> None:
        """Load historical candle data from CSV."""
        self.history.clear()
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Expect cols: time, open, high, low, close, tick_volume, spread
                try:
                    ts = int(row["time"])
                except ValueError:
                    # In case it's formatted as a date string
                    # MT5 copy_rates returns raw integer timestamps
                    continue 

                dt = datetime.fromtimestamp(ts, tz=UTC)
                candle = Candle(
                    timestamp=dt,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["tick_volume"]),
                )
                self.history.append(candle)
                
        # Sort chronologically just in case
        self.history.sort(key=lambda c: c.timestamp)
        logger.info("MockBroker loaded %d historical candles", len(self.history))
        self.current_idx = -1

    def step(self) -> bool:
        """Advance the simulated clock by one candle.
        
        Returns True if advanced, False if EOF.
        """
        if self.current_idx + 1 >= len(self.history):
            return False
            
        self.current_idx += 1
        self.current_candle = self.history[self.current_idx]
        
        # Process open orders against the NEW candle's high/low
        self._process_orders(self.current_candle)
        
        return True

    def _process_orders(self, candle: Candle) -> None:
        """Check if any open orders hit SL or TP on this candle."""
        to_close = []
        
        for ticket, p in self.positions.items():
            hit_sl = False
            hit_tp = False
            close_price = 0.0
            
            if p.direction == "BUY":
                # Price drops below SL
                if p.stop_loss > 0 and candle.low <= p.stop_loss:
                    hit_sl = True
                    # Slippage simulation: if open gaps below SL, fill at open, else fill at SL
                    close_price = candle.open if candle.open < p.stop_loss else p.stop_loss
                # Price rises above TP
                elif p.current_price > 0 and candle.high >= p.current_price:  # using current_price as TP internally here for simulation
                    hit_tp = True
                    close_price = candle.open if candle.open > p.current_price else p.current_price
                    
            elif p.direction == "SELL":
                # Price rises above SL
                if p.stop_loss > 0 and candle.high >= p.stop_loss:
                    hit_sl = True
                    close_price = candle.open if candle.open > p.stop_loss else p.stop_loss
                # Price drops below TP
                elif p.current_price > 0 and candle.low <= p.current_price:  # TP
                    hit_tp = True
                    close_price = candle.open if candle.open < p.current_price else p.current_price

            if hit_sl or hit_tp:
                # Calculate P&L
                # Simplification: assuming 1 lot = $10 per pip/point (standard FX logic approximation)
                # In reality this depends heavily on quote currency and contract size. 
                # For MT5 generic backtesting, we compute pure price diffs:
                diff = (close_price - p.entry_price) if p.direction == "BUY" else (p.entry_price - close_price)
                
                # Assume standard multiplier 100000 for standard lot
                # This is a stub implementation. Real PnL logic requires tick_value.
                pnl = diff * 100000 * p.lot_size
                
                p.current_price = close_price  # Store exit price
                p.pnl = pnl
                self._balance += pnl
                to_close.append((ticket, hit_sl))

        for ticket, was_sl in to_close:
            reason = "SL" if was_sl else "TP"
            logger.info("[%s] Hit %s => %s", reason, self.current_candle.timestamp, self.positions[ticket])
            self.closed_positions.append(self.positions.pop(ticket))

    # ── BrokerConnector Implementation ──────────────────────────────────────

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def get_balance(self) -> float:
        return self._balance

    def get_equity(self) -> float:
        # Balance + floating PnL
        equity = self._balance
        if not self.current_candle:
            return equity
            
        c = self.current_candle.close
        for p in self.positions.values():
            diff = (c - p.entry_price) if p.direction == "BUY" else (p.entry_price - c)
            floating = diff * 100000 * p.lot_size
            equity += floating
        return equity

    def get_tick(self, symbol: str) -> dict[str, float]:
        if not self.current_candle:
            raise RuntimeError("Requested tick before loading data")
        
        # Return the close of the current candle as the "live" price
        c = self.current_candle.close
        return {
            "bid": c,
            "ask": c,  # Ignoring spread for simple backtesting unless provided
            "spread": 0.0,
            "volume": self.current_candle.volume,
        }

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        if self.current_idx < 0:
            return []
        
        # Slicing history up to current_idx (inclusive)
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
            current_price=tp or 0.0,  # HACK: Using current_price to store TP since PositionInfo lacks a tp field
            pnl=0.0,
            comment=comment
        )
        self.positions[ticket] = pos
        logger.info("[MOCK BROKER] Placed %s %s order at %.5f (SL: %.5f, TP: %.5f)", direction, symbol, entry_price, sl, tp or 0.0)
        
        return OrderResult(
            success=True,
            order_id=str(uuid.uuid4()),
            broker_ticket=ticket,
            filled_lots=lot_size,
            fill_price=entry_price,
            message="MOCK_FILL"
        )

    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        if ticket in self.positions:
            if sl is not None:
                self.positions[ticket].stop_loss = sl
            if tp is not None:
                self.positions[ticket].current_price = tp # HACK for TP
            return True
        return False

    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        # Stub for simple backtesting
        return self.close_order(ticket, symbol, direction)

    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        if ticket in self.positions:
            p = self.positions.pop(ticket)
            
            c = self.current_candle.close if self.current_candle else p.entry_price
            diff = (c - p.entry_price) if p.direction == "BUY" else (p.entry_price - c)
            pnl = diff * 100000 * p.lot_size
            
            p.current_price = c # exit price
            p.pnl = pnl
            self._balance += pnl
            self.closed_positions.append(p)
            return True
        return False

    def get_open_positions(self) -> list[PositionInfo]:
        """Update floating PnL and return open positions."""
        c = self.current_candle.close if self.current_candle else 0.0
        for p in self.positions.values():
            diff = (c - p.entry_price) if p.direction == "BUY" else (p.entry_price - c)
            p.pnl = diff * 100000 * p.lot_size
        return list(self.positions.values())

    def get_fill_size(self, order_id: str) -> float:
        return 1.0 # Mock

    def reconcile(self) -> list[PositionInfo]:
        return self.get_open_positions()
