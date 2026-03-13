"""Tests for LoggingAgent."""

from unittest.mock import patch

from agents.logging_agent import LoggingAgent


class TestLoggingAgent:
    @patch("utils.telegram_bot.send_message")
    def test_record_writes_to_db(self, mock_tg, db, tmp_path):
        agent = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        agent.record("TEST_EVENT", "hello world")

        cur = db.conn.execute("SELECT * FROM events WHERE source='TEST_EVENT'")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["message"] == "hello world"

    @patch("utils.telegram_bot.send_message")
    def test_log_trade(self, mock_tg, db, tmp_path):
        agent = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        agent.log_trade("abc123", "OPENED", "BUY EURUSD 0.1 lots")

        cur = db.conn.execute("SELECT * FROM events WHERE source='TRADE'")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert "abc123" in rows[0]["message"]

    @patch("utils.telegram_bot.send_message")
    def test_send_daily_summary_no_trades(self, mock_tg, db, tmp_path):
        agent = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        agent.send_daily_summary({"trades_today": 0})
        mock_tg.assert_called_once()
        msg = mock_tg.call_args[0][0]
        assert "No trades today" in msg

    @patch("utils.telegram_bot.send_message")
    def test_send_daily_summary_with_trades(self, mock_tg, db, tmp_path):
        agent = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        report = {
            "trades_today": 5, "wins": 3, "losses": 2,
            "win_rate": 0.6, "total_pnl": 42.5, "avg_pnl": 8.5,
        }
        agent.send_daily_summary(report)
        mock_tg.assert_called_once()
        msg = mock_tg.call_args[0][0]
        assert "Trades: 5" in msg
        assert "42.50" in msg

    @patch("utils.telegram_bot.send_message")
    def test_logging_configures_once(self, mock_tg, db, tmp_path):
        import logging
        # Clear all handlers so the test starts fresh
        root = logging.getLogger()
        root.handlers.clear()

        agent1 = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        count1 = len(root.handlers)
        agent2 = LoggingAgent(db, log_dir=str(tmp_path / "logs"))
        count2 = len(root.handlers)
        assert count1 == count2  # should not add handlers again
