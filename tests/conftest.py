"""Shared test fixtures.

Every test gets an in-memory SQLite DB and a MockConnector so no
external dependencies or files are needed.
"""

from __future__ import annotations

import pytest

from broker.mock_connector import MockConnector
from database.db import Database
from filters.news_filter import NewsFilter
from models.market_data import Candle, MarketContext, MarketData
from models.signal import EntrySnapshot, Signal
from models.trade import Trade
from state.persistence import StatePersistence


@pytest.fixture
def broker() -> MockConnector:
    b = MockConnector(starting_balance=10_000.0, base_price=1.1050)
    b.connect()
    return b


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(db_path=str(tmp_path / "test.db"))


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
