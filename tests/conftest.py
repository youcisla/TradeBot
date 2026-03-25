"""Shared test fixtures.

Every test gets an in-memory mock DB and a MockConnector so no
external dependencies or files are needed.
"""

from __future__ import annotations

from typing import Any

import pytest

from broker.mock_connector import MockConnector
from filters.news_filter import NewsFilter
from models.market_data import Candle, MarketContext, MarketData
from models.signal import EntrySnapshot, Signal
from models.trade import Trade
from state.persistence import StatePersistence


class _MockDatabase:
    """In-memory shim that satisfies the Database interface used by tests."""

    def __init__(self) -> None:
        self._trades: dict[str, Trade] = {}
        self._events: list[dict[str, Any]] = []

    def upsert_trade(self, trade: Trade) -> None:
        self._trades[trade.id] = trade

    def get_open_trades(self) -> list[Trade]:
        return [t for t in self._trades.values() if t.status != "CLOSED"]

    def get_trade(self, trade_id: str) -> Trade | None:
        return self._trades.get(trade_id)

    def log_agent_event(self, agent: str, level: str, message: str, data: Any = None) -> None:
        self._events.append({"agent": agent, "level": level, "message": message, "data": data})

    # Stubs for any other methods that might be called
    def get_strategy_confidence(self, strategy: str, symbol: str) -> float:
        return 0.5

    def upsert_strategy_confidence(self, strategy: str, symbol: str, confidence: float) -> None:
        pass

    def save_trade_score(self, *args: Any, **kwargs: Any) -> None:
        pass

    def get_pending_command(self) -> dict[str, Any] | None:
        return None

    def mark_command_done(self, command_id: int) -> None:
        pass

    def update_bot_status(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.fixture
def broker() -> MockConnector:
    b = MockConnector(starting_balance=10_000.0, base_price=1.1050)
    b.connect()
    return b


@pytest.fixture
def db() -> _MockDatabase:
    return _MockDatabase()


@pytest.fixture
def state(db, broker) -> StatePersistence:
    return StatePersistence(db, broker)


@pytest.fixture
def news_filter() -> NewsFilter:
    return NewsFilter()


def make_candles(count: int = 60, base: float = 1.1050,
                 trend: float = 0.0001) -> list[Candle]:
    """Generate a deterministic list of candles with a slight upward trend."""
    from datetime import datetime, timedelta
    candles = []
    for i in range(count):
        c = round(base + i * trend, 5)
        candles.append(Candle(
            timestamp=datetime(2026, 1, 1) + timedelta(hours=i),
            open=round(c - 0.0002, 5),
            high=round(c + 0.0010, 5),
            low=round(c - 0.0010, 5),
            close=c,
            volume=1000.0,
        ))
    return candles


def make_signal(
    symbol: str = "EURUSD",
    direction: str = "BUY",
    strategy: str = "sma_crossover",
    entry: float = 1.1050,
    sl: float = 1.1000,
    tp1: float = 1.1100,
    tp2: float = 1.1150,
    tp3: float = 1.1200,
    spread: float = 0.00015,
) -> Signal:
    return Signal(
        strategy=strategy,
        symbol=symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        confidence=0.5,
        reason="test signal",
        entry_snapshot=EntrySnapshot(
            spread=spread,
            rsi_aligned=True,
            trend_aligned=True,
            volume_sufficient=True,
            near_news_event=False,
            market_condition="trending",
            session="London",
            day_of_week="Monday",
        ),
    )


def make_trade(
    symbol: str = "EURUSD",
    direction: str = "BUY",
    strategy: str = "sma_crossover",
    entry: float = 1.1050,
    sl: float = 1.1000,
    lots: float = 0.10,
    broker_ticket: int = 100_001,
) -> Trade:
    return Trade(
        symbol=symbol,
        strategy=strategy,
        direction=direction,
        entry_price=entry,
        lot_size=lots,
        stop_loss=sl,
        take_profit_1=round(entry + 0.0050, 5),
        take_profit_2=round(entry + 0.0100, 5),
        take_profit_3=round(entry + 0.0150, 5),
        tp1_lots=round(lots * 0.4, 2),
        tp2_lots=round(lots * 0.3, 2),
        tp3_lots=round(lots * 0.3, 2),
        broker_ticket=broker_ticket,
        spread_at_entry=0.00015,
        snap_rsi_aligned=True,
        snap_trend_aligned=True,
        snap_volume_sufficient=True,
    )
