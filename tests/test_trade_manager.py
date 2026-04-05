"""Tests for TradeManagerAgent."""

from datetime import UTC, datetime, timedelta

import pytest
from unittest.mock import patch

from agents.trade_manager import TradeManagerAgent
from broker.connector import PositionInfo
from tests.conftest import make_trade


class TestTradeManagerAgent:

    def _make_manager(self, broker, state, db):
        return TradeManagerAgent(broker, state, db)

    @pytest.mark.parametrize("tp_level,tp_field,tp_value", [
        ("_TP1", "take_profit_1", 1.1200),
        ("_TP2", "take_profit_2", 1.1300),
        ("_TP3", "take_profit_3", 1.1400),
    ])
    def test_tp_reconciliation_correct(self, broker, state, db, tp_level, tp_field, tp_value):
        comment = f"strategy{tp_level}"
        pos = PositionInfo(
            ticket=100_010, symbol="EURUSD", direction="BUY", lot_size=0.10,
            entry_price=1.1000, stop_loss=1.0900, take_profit=tp_value, current_price=1.1000, pnl=0.0,
            magic=202603, comment=comment,
        )
        broker._positions[100_010] = pos
        trade = make_trade(broker_ticket=100_010)
        setattr(trade, tp_field, tp_value)
        state.save_trade(trade)
        mgr = self._make_manager(broker, state, db)
        mgr._open_trades = [trade]
        mgr.sync_existing_position_targets()
        assert broker._positions[100_010].take_profit == tp_value

    @pytest.mark.parametrize("tp_level,tp_field,tp_value", [
        ("_TP1", "take_profit_1", 1.1200),
        ("_TP2", "take_profit_2", 1.1300),
        ("_TP3", "take_profit_3", 1.1400),
    ])
    def test_tp_reconciliation_missing(self, broker, state, db, tp_level, tp_field, tp_value):
        comment = f"strategy{tp_level}"
        pos = PositionInfo(
            ticket=100_011, symbol="EURUSD", direction="BUY", lot_size=0.10,
            entry_price=1.1000, stop_loss=1.0900, take_profit=None, current_price=1.1000, pnl=0.0,
            magic=202603, comment=comment,
        )
        broker._positions[100_011] = pos
        trade = make_trade(broker_ticket=100_011)
        setattr(trade, tp_field, tp_value)
        state.save_trade(trade)
        mgr = self._make_manager(broker, state, db)
        mgr._open_trades = [trade]
        mgr.sync_existing_position_targets()
        assert abs(broker._positions[100_011].take_profit - tp_value) < 1e-5

    @pytest.mark.parametrize("tp_level,tp_field,tp_value", [
        ("_TP1", "take_profit_1", 1.1200),
        ("_TP2", "take_profit_2", 1.1300),
        ("_TP3", "take_profit_3", 1.1400),
    ])
    def test_tp_reconciliation_incorrect(self, broker, state, db, tp_level, tp_field, tp_value):
        comment = f"strategy{tp_level}"
        pos = PositionInfo(
            ticket=100_012, symbol="EURUSD", direction="BUY", lot_size=0.10,
            entry_price=1.1000, stop_loss=1.0900, take_profit=tp_value + 0.01, current_price=1.1000, pnl=0.0,
            magic=202603, comment=comment,
        )
        broker._positions[100_012] = pos
        trade = make_trade(broker_ticket=100_012)
        setattr(trade, tp_field, tp_value)
        state.save_trade(trade)
        mgr = self._make_manager(broker, state, db)
        mgr._open_trades = [trade]
        mgr.sync_existing_position_targets()
        assert abs(broker._positions[100_012].take_profit - tp_value) < 1e-5

    def test_tp_reconciliation_skips_manual(self, broker, state, db):
        pos = PositionInfo(
            ticket=100_013, symbol="EURUSD", direction="BUY", lot_size=0.10,
            entry_price=1.1000, stop_loss=1.0900, take_profit=1.1200, current_price=1.1000, pnl=0.0,
            magic=123456, comment="manual_trade",
        )
        broker._positions[100_013] = pos
        mgr = self._make_manager(broker, state, db)
        mgr.sync_existing_position_targets()
        assert broker._positions[100_013].take_profit == 1.1200

    def test_tp_reconciliation_orphan_adoption(self, broker, state, db):
        pos = PositionInfo(
            ticket=100_014, symbol="EURUSD", direction="BUY", lot_size=0.10,
            entry_price=1.1000, stop_loss=1.0900, take_profit=1.1200, current_price=1.1000, pnl=0.0,
            magic=202603, comment="strategy_TP1",
        )
        broker._positions[100_014] = pos
        mgr = self._make_manager(broker, state, db)
        mgr._open_trades = []
        mgr.sync_existing_position_targets()
        assert broker._positions[100_014].take_profit == 1.1200

    @patch("utils.telegram_bot.send_message")
    def test_monitor_detects_external_close(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(broker_ticket=999_999)
        trade.open_time = datetime.now(UTC) - timedelta(seconds=120)
        state.save_trade(trade)
        mgr._open_trades = [trade]

        mgr.monitor()
        assert trade.status == "CLOSED"
        assert trade.close_reason == "EXTERNAL"

    @patch("utils.telegram_bot.send_message")
    def test_tp1_hit(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(entry=1.1050, sl=1.1000, lots=0.10, broker_ticket=100_001)
        state.save_trade(trade)

        pos = PositionInfo(
            ticket=trade.broker_ticket, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=trade.take_profit_1 + 0.0001,
            pnl=5.0,
        )
        broker._positions[trade.broker_ticket] = pos
        broker.get_open_positions = lambda: list(broker._positions.values())
        mgr._open_trades = [trade]

        mgr.monitor()
        assert trade.tp1_hit is True
        assert trade.status == "PARTIAL"

    @patch("utils.telegram_bot.send_message")
    def test_tp1_handles_partial_fill_mismatch(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(entry=1.1050, sl=1.1000, lots=0.10, broker_ticket=100_101)
        state.save_trade(trade)

        pos = PositionInfo(
            ticket=trade.broker_ticket,
            symbol="EURUSD",
            direction="BUY",
            lot_size=0.10,
            entry_price=1.1050,
            stop_loss=1.1000,
            current_price=trade.take_profit_1 + 0.0001,
            pnl=5.0,
        )
        broker._positions[trade.broker_ticket] = pos

        def _partial_fill_close(ticket, symbol, lot_size, direction):
            position = broker._positions.get(ticket)
            if position is None:
                return False
            # Simulate a partial fill that closes only half of requested lots.
            position.lot_size = round(max(0.0, position.lot_size - (lot_size / 2.0)), 2)
            return True

        broker.close_partial = _partial_fill_close
        broker.get_open_positions = lambda: list(broker._positions.values())
        mgr._open_trades = [trade]

        mgr.monitor()

        assert trade.tp1_hit is True
        assert trade.status == "PARTIAL"
        assert broker._positions[trade.broker_ticket].lot_size == 0.08

    @patch("utils.telegram_bot.send_message")
    def test_sl_hit_closes_trade(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(entry=1.1050, sl=1.1000, lots=0.10, broker_ticket=100_002)
        state.save_trade(trade)

        pos = PositionInfo(
            ticket=trade.broker_ticket, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=1.0990,
            pnl=-6.0,
        )
        broker._positions[trade.broker_ticket] = pos
        broker.get_open_positions = lambda: list(broker._positions.values())
        mgr._open_trades = [trade]

        mgr.monitor()
        assert trade.status == "CLOSED"
        assert trade.close_reason == "SL"

    @patch("utils.telegram_bot.send_message")
    def test_close_all(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        t1 = make_trade(broker_ticket=100_003)
        t2 = make_trade(broker_ticket=100_004)
        state.save_trade(t1)
        state.save_trade(t2)
        broker._positions[100_003] = PositionInfo(
            ticket=100_003, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=1.1060, pnl=1.0,
        )
        broker._positions[100_004] = PositionInfo(
            ticket=100_004, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=1.1060, pnl=1.0,
        )
        mgr._open_trades = [t1, t2]

        mgr.close_all("KILL_SWITCH")

        assert t1.status == "CLOSED"
        assert t2.status == "CLOSED"
        assert len(mgr.get_open_trades()) == 0

    def test_get_open_trades_filters_closed(self, broker, state, db):
        mgr = self._make_manager(broker, state, db)
        t1 = make_trade()
        t2 = make_trade()
        t2.status = "CLOSED"
        mgr._open_trades = [t1, t2]

        assert len(mgr.get_open_trades()) == 1

    @patch("utils.telegram_bot.send_message")
    def test_add_trade(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)
        trade = make_trade()
        mgr.add_trade(trade)
        assert trade in mgr._open_trades

    @patch("utils.telegram_bot.send_message")
    def test_tp_reached_buy(self, mock_tg, broker, state, db):
        trade = make_trade(direction="BUY")
        assert TradeManagerAgent._tp_reached(trade, 1.1200, 1.1100) is True
        assert TradeManagerAgent._tp_reached(trade, 1.1000, 1.1100) is False

    @patch("utils.telegram_bot.send_message")
    def test_tp_reached_sell(self, mock_tg, broker, state, db):
        trade = make_trade(direction="SELL")
        assert TradeManagerAgent._tp_reached(trade, 1.0900, 1.1000) is True
        assert TradeManagerAgent._tp_reached(trade, 1.1100, 1.1000) is False

    def test_sl_hit_buy(self, broker, state, db):
        trade = make_trade(direction="BUY", sl=1.1000)
        assert TradeManagerAgent._sl_hit(trade, 1.0990) is True
        assert TradeManagerAgent._sl_hit(trade, 1.1050) is False

    def test_sl_hit_sell(self, broker, state, db):
        trade = make_trade(direction="SELL", sl=1.1100)
        assert TradeManagerAgent._sl_hit(trade, 1.1110) is True
        assert TradeManagerAgent._sl_hit(trade, 1.1050) is False
