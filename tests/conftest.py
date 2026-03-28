"""Shared test fixtures.

Every test gets an in-memory mock DB and a MockConnector so no
external dependencies or files are needed.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from broker.mock_connector import MockConnector
from models.market_data import Candle, MarketContext, MarketData
from models.signal import EntrySnapshot, Signal
from models.trade import Trade
from state.persistence import StatePersistence


class _MockDatabase:
    """In-memory shim that satisfies the Database interface used by tests.

    Provides:
    - A real ``sqlite3`` connection (``self.conn``) with an ``events`` table
      so that logging-agent tests can query it directly.
    - ``log_event`` that inserts into the SQLite table.
    - All methods called by LoggingAgent, LearningAgent, and other agents
      during the test suite.
    """

    def __init__(self) -> None:
        self._trades: dict[str, Trade] = {}
        self._events: list[dict[str, Any]] = []
        self._confidences: dict[str, float] = {}

        # Real in-memory SQLite so logging-agent tests can query conn directly.
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE events (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                level   TEXT,
                source  TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    # ── trade persistence ─────────────────────────────────────────────────

    def upsert_trade(self, trade: Trade) -> None:
        self._trades[trade.id] = trade

    def get_open_trades(self) -> list[Trade]:
        return [t for t in self._trades.values() if t.status != "CLOSED"]

    def get_trade(self, trade_id: str) -> Trade | None:
        return self._trades.get(trade_id)

    def get_trades_closed_today(self) -> list[Trade]:
        return []

    # ── event logging ─────────────────────────────────────────────────────

    def log_event(self, level: str, source: str, message: str) -> None:
        """Insert a structured event into the in-memory SQLite events table."""
        self.conn.execute(
            "INSERT INTO events (level, source, message) VALUES (?, ?, ?)",
            (level, source, message),
        )
        self.conn.commit()

    def log_agent_event(self, agent: str, level: str, message: str, data: Any = None) -> None:
        self._events.append({"agent": agent, "level": level, "message": message, "data": data})

    # ── strategy confidence ───────────────────────────────────────────────

    def get_confidence(self, strategy: str) -> float | None:
        """Return stored confidence for ``strategy``, or None if not set."""
        return self._confidences.get(strategy)

    def upsert_confidence(
        self,
        strategy: str,
        confidence: float,
        total_trades: int,
        total_score: int,
    ) -> None:
        self._confidences[strategy] = confidence

    # Legacy names used by non-learning agents (kept for backward compat)
    def get_strategy_confidence(self, strategy: str, symbol: str) -> float:
        return self._confidences.get(strategy, 0.5)

    def upsert_strategy_confidence(self, strategy: str, symbol: str, confidence: float) -> None:
        self._confidences[strategy] = confidence

    def boost_all_strategy_confidence(self, boost: float) -> None:
        for key in self._confidences:
            self._confidences[key] = min(1.0, self._confidences[key] + boost)

    # ── trade scoring ─────────────────────────────────────────────────────

    def insert_score(self, **kwargs: Any) -> None:
        """No-op stub — score persistence is not verified in unit tests."""

    def save_trade_score(self, *args: Any, **kwargs: Any) -> None:
        pass

    # ── streak tracking ───────────────────────────────────────────────────

    def get_strategy_streak(self, strategy: str) -> int:
        return 0

    def update_strategy_streak(self, strategy: str, streak: int, score: float) -> None:
        pass

    # ── rolling statistics ────────────────────────────────────────────────

    def get_rolling_avg_score(self, strategy: str, n: int = 10) -> float | None:
        return None

    # ── period performance snapshots ──────────────────────────────────────

    def get_period_stats(self, since: Any, until: Any) -> dict[str, Any]:
        return {"trades": 0, "total_pnl": 0.0, "win_rate": 0.0, "avg_score": 0.0}

    def save_performance_snapshot(
        self, period_type: str, period_key: str, **kwargs: Any
    ) -> None:
        pass

    def get_previous_snapshot(
        self, period_type: str, period_key: str
    ) -> dict[str, Any] | None:
        return None

    # ── command bus ───────────────────────────────────────────────────────

    def get_pending_command(self) -> dict[str, Any] | None:
        return None

    def mark_command_done(self, command_id: int) -> None:
        pass

    # ── bot status ────────────────────────────────────────────────────────

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
def crucix_agent():
    from agents.crucix_agent import CrucixAgent
    return CrucixAgent()


def make_candles(count: int = 60, base: float = 1.1050,
                 trend: float = 0.0001) -> list[Candle]:
    """Generate a deterministic list of candles with a slight upward trend."""
    from datetime import UTC, datetime, timedelta
    candles = []
    for i in range(count):
        c = round(base + i * trend, 5)
        candles.append(Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i),
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
