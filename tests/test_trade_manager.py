"""Tests for TradeManagerAgent."""

from unittest.mock import patch

from agents.trade_manager import TradeManagerAgent
from broker.connector import PositionInfo
from tests.conftest import make_trade


class TestTradeManagerAgent:
    def _make_manager(self, broker, state, db):
        return TradeManagerAgent(broker, state, db)

    @patch("utils.telegram_bot.send_message")
    def test_monitor_detects_external_close(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(broker_ticket=999_999)
        state.save_trade(trade)
        mgr._open_trades = [trade]

        # Broker has no positions → trade should be marked CLOSED
        mgr.monitor()
        assert trade.status == "CLOSED"
        assert trade.close_reason == "EXTERNAL"

    @patch("utils.telegram_bot.send_message")
    def test_tp1_hit(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(entry=1.1050, sl=1.1000, lots=0.10, broker_ticket=100_001)
        state.save_trade(trade)

        # Put matching position on the mock broker at TP1 price
        pos = PositionInfo(
            ticket=trade.broker_ticket, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=trade.take_profit_1 + 0.0001,  # above TP1
            pnl=5.0,
        )
        broker._positions[trade.broker_ticket] = pos
        # Prevent MockConnector.get_open_positions from re-wobbling prices
        broker.get_open_positions = lambda: list(broker._positions.values())
        mgr._open_trades = [trade]

        mgr.monitor()
        assert trade.tp1_hit is True
        assert trade.status == "PARTIAL"

    @patch("utils.telegram_bot.send_message")
    def test_sl_hit_closes_trade(self, mock_tg, broker, state, db):
        mgr = self._make_manager(broker, state, db)

        trade = make_trade(entry=1.1050, sl=1.1000, lots=0.10, broker_ticket=100_002)
        state.save_trade(trade)

        pos = PositionInfo(
            ticket=trade.broker_ticket, symbol="EURUSD", direction="BUY",
            lot_size=0.10, entry_price=1.1050, stop_loss=1.1000,
            current_price=1.0990,  # below SL
            pnl=-6.0,
        )
        broker._positions[trade.broker_ticket] = pos
        # Prevent MockConnector.get_open_positions from re-wobbling prices
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
