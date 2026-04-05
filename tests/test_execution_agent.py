"""Tests for ExecutionAgent."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from agents.execution_agent import ExecutionAgent
from tests.conftest import make_signal, make_trade


class TestExecutionAgent:
    def _make_agent(self, broker, state):
        return ExecutionAgent(
            broker=broker,
            state=state,
            calculate_position_size=lambda sig: 0.10,
        )

    @patch("utils.telegram_bot.send_message")
    def test_open_trade_success(self, mock_tg, broker, state):
        agent = self._make_agent(broker, state)
        signal = make_signal()
        trade = agent.open_trade(signal)

        assert trade is not None
        assert trade.symbol == "EURUSD"
        assert trade.direction == "BUY"
        assert trade.lot_size == 0.10
        assert trade.broker_ticket > 0
        assert trade.status == "OPEN"

    @patch("utils.telegram_bot.send_message")
    def test_trade_persisted_to_db(self, mock_tg, broker, state, db):
        agent = self._make_agent(broker, state)
        signal = make_signal()
        trade = agent.open_trade(signal)

        loaded = db.get_trade(trade.id)
        assert loaded is not None
        assert loaded.symbol == trade.symbol

    @patch("utils.telegram_bot.send_message")
    def test_duplicate_rejected(self, mock_tg, broker, state, db):
        agent = self._make_agent(broker, state)
        signal = make_signal()

        t1 = agent.open_trade(signal)
        assert t1 is not None

        t2 = agent.open_trade(signal)
        assert t2 is None  # duplicate blocked

    @patch("utils.telegram_bot.send_message")
    def test_tp_lots_sum_to_total(self, mock_tg, broker, state):
        agent = self._make_agent(broker, state)
        signal = make_signal()
        trade = agent.open_trade(signal)

        total = trade.tp1_lots + trade.tp2_lots + trade.tp3_lots
        assert abs(total - trade.lot_size) < 0.01

    @patch("utils.telegram_bot.send_message")
    def test_snapshot_fields_copied(self, mock_tg, broker, state):
        agent = self._make_agent(broker, state)
        signal = make_signal()
        trade = agent.open_trade(signal)

        assert trade.snap_rsi_aligned is True
        assert trade.snap_trend_aligned is True
        assert trade.snap_session == "London"

    @patch("utils.telegram_bot.send_message")
    def test_rejects_below_min_lot(self, mock_tg, broker, state):
        agent = ExecutionAgent(
            broker=broker,
            state=state,
            calculate_position_size=lambda sig: 0.001,  # below MIN_LOT_SIZE
        )
        signal = make_signal()
        trade = agent.open_trade(signal)
        assert trade is None

    @patch("utils.telegram_bot.pause")
    @patch("utils.telegram_bot.send_message")
    def test_autotrading_disabled_error_sets_execution_cooldown(
        self,
        mock_tg,
        mock_pause,
        broker,
        state,
    ):
        agent = self._make_agent(broker, state)
        signal = make_signal()

        class _Res:
            success = False
            message = "MT5 error 10027: AutoTrading disabled by client"

        broker.place_order = lambda **kwargs: _Res()

        trade = agent.open_trade(signal)

        assert trade is None
        assert agent._autotrading_block_until is not None
        assert agent._autotrading_block_until > datetime.now(UTC)
        assert mock_pause.called

    @patch("utils.telegram_bot.send_message")
    def test_skips_execution_while_autotrading_backoff_active(self, mock_tg, broker, state):
        agent = self._make_agent(broker, state)
        signal = make_signal()

        agent._autotrading_block_until = datetime.now(UTC) + timedelta(seconds=120)

        called = {"place_order": 0}

        def _place_order(**kwargs):
            called["place_order"] += 1
            raise AssertionError("place_order should not be called during backoff")

        broker.place_order = _place_order

        trade = agent.open_trade(signal)
        assert trade is None
        assert called["place_order"] == 0
