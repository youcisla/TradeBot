"""End-to-end trade lifecycle tests.

MockConnector → ExecutionAgent → TradeManager
Covers: trade open, TP1 partial close + breakeven SL, TP2, and SL hit.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from broker.connector import PositionInfo
from agents.execution_agent import ExecutionAgent
from agents.trade_manager import TradeManagerAgent
from tests.conftest import _MockDatabase, make_signal

# Order placement is gated by MarketHoursGuard, which reads the wall clock.
# Pin it to a weekday session so these tests don't fail at weekends.
pytestmark = pytest.mark.usefixtures("market_clock_open")


# ── Deterministic broker helper ───────────────────────────────────────────────


class _ControlledConnector:
    """Thin broker wrapper that serves a fixed price for each call to
    get_open_positions(), letting tests drive the price to any level."""

    def __init__(self, inner):
        self._inner = inner
        self._forced_price: float | None = None   # if set, overrides pos.current_price

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def set_price(self, price: float) -> None:
        """Force all open positions to report this current_price."""
        self._forced_price = price
        for pos in self._inner._positions.values():
            pos.current_price = price

    def get_open_positions(self) -> list[PositionInfo]:
        positions = list(self._inner._positions.values())
        if self._forced_price is not None:
            for pos in positions:
                pos.current_price = self._forced_price
        return positions

    # Delegate writes/queries to the inner mock
    def close_partial(self, *a, **kw):
        return self._inner.close_partial(*a, **kw)

    def close_order(self, *a, **kw):
        return self._inner.close_order(*a, **kw)

    def modify_order(self, *a, **kw):
        return self._inner.modify_order(*a, **kw)

    def place_order(self, *a, **kw):
        return self._inner.place_order(*a, **kw)

    def get_tick(self, *a, **kw):
        return self._inner.get_tick(*a, **kw)

    def get_balance(self):
        return self._inner.get_balance()

    def get_equity(self):
        return self._inner.get_equity()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db() -> _MockDatabase:
    return _MockDatabase()


@pytest.fixture
def controlled_broker(broker) -> _ControlledConnector:
    return _ControlledConnector(broker)


def _make_exec(broker, state):
    return ExecutionAgent(
        broker=broker,
        state=state,
        calculate_position_size=lambda sig: 0.10,
    )


def _make_mgr(broker, state, db):
    return TradeManagerAgent(broker=broker, state=state, db=db)


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestTradeOpen:
    @patch("utils.telegram_bot.send_message")
    def test_open_trade_appears_in_manager(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        mgr = _make_mgr(controlled_broker, state, db)

        signal = make_signal()
        trade = exec_agent.open_trade(signal)

        assert trade is not None
        mgr.load_open_trades()
        assert len(mgr.get_open_trades()) == 1
        assert mgr.get_open_trades()[0].id == trade.id

    @patch("utils.telegram_bot.send_message")
    def test_open_trade_is_open_status(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        exec_agent.open_trade(make_signal())

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()
        trade = mgr.get_open_trades()[0]
        assert trade.status == "OPEN"


class TestTP1Lifecycle:
    @patch("utils.telegram_bot.send_message")
    def test_tp1_hit_partial_close_and_breakeven(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        signal = make_signal(entry=1.1050, sl=1.1000, tp1=1.1100, tp2=1.1150, tp3=1.1200)
        trade = exec_agent.open_trade(signal)
        assert trade is not None

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()

        # Push price to TP1
        controlled_broker.set_price(1.1100)
        mgr.monitor()

        managed = db.get_trade(trade.id)
        assert managed is not None
        assert managed.tp1_hit is True
        assert managed.status == "PARTIAL"

    @patch("utils.telegram_bot.send_message")
    def test_tp1_moves_sl_to_breakeven(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        signal = make_signal(entry=1.1050, sl=1.1000, tp1=1.1100, tp2=1.1150, tp3=1.1200)
        trade = exec_agent.open_trade(signal)

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()

        controlled_broker.set_price(1.1100)
        mgr.monitor()

        managed = db.get_trade(trade.id)
        # After TP1, SL should be at or above the actual fill price (breakeven).
        # MockConnector fills at a random bid/ask offset so we use managed.entry_price,
        # not signal.entry_price, to avoid a flaky assertion.
        assert managed.stop_loss >= managed.entry_price


class TestTP2Lifecycle:
    @patch("utils.telegram_bot.send_message")
    def test_tp2_hit_after_tp1(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        signal = make_signal(entry=1.1050, sl=1.1000, tp1=1.1100, tp2=1.1150, tp3=1.1200)
        trade = exec_agent.open_trade(signal)

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()

        # First: TP1
        controlled_broker.set_price(1.1100)
        mgr.monitor()

        # Reload the in-memory trade after TP1 (state was saved, reload from db)
        mgr.load_open_trades()

        # Then: TP2
        controlled_broker.set_price(1.1150)
        mgr.monitor()

        managed = db.get_trade(trade.id)
        assert managed.tp1_hit is True
        assert managed.tp2_hit is True


class TestSLLifecycle:
    @patch("utils.telegram_bot.send_message")
    def test_sl_hit_closes_trade(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        signal = make_signal(entry=1.1050, sl=1.1000, tp1=1.1100, tp2=1.1150, tp3=1.1200)
        trade = exec_agent.open_trade(signal)

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()

        # Push price below SL
        controlled_broker.set_price(1.0990)
        mgr.monitor()

        managed = db.get_trade(trade.id)
        assert managed.status == "CLOSED"
        assert managed.close_reason == "SL"

    @patch("utils.telegram_bot.send_message")
    def test_sl_trade_removed_from_open_list(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        exec_agent.open_trade(make_signal(entry=1.1050, sl=1.1000))

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()

        controlled_broker.set_price(1.0990)
        mgr.monitor()

        assert len(mgr.get_open_trades()) == 0


class TestEmergencyClose:
    @patch("utils.telegram_bot.send_message")
    def test_close_all_closes_every_trade(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        exec_agent.open_trade(make_signal(symbol="EURUSD"))
        # MockConnector serves one base_price (1.1050) for every symbol, so the
        # second entry must sit near it — a distant price trips the slippage
        # guard, which correctly rejects a fill that invalidates SL/TP.
        exec_agent.open_trade(make_signal(symbol="GBPUSD"))

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()
        assert len(mgr.get_open_trades()) == 2

        mgr.close_all("RISK_LIMIT")
        assert len(mgr.get_open_trades()) == 0

    @patch("utils.telegram_bot.send_message")
    def test_close_all_marks_reason(self, _tg, controlled_broker, state, db):
        exec_agent = _make_exec(controlled_broker, state)
        trade = exec_agent.open_trade(make_signal())

        mgr = _make_mgr(controlled_broker, state, db)
        mgr.load_open_trades()
        mgr.close_all("DAILY_LOSS_LIMIT")

        managed = db.get_trade(trade.id)
        assert managed.close_reason == "DAILY_LOSS_LIMIT"
        assert managed.status == "CLOSED"
