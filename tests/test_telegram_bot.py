"""Tests for Telegram command filtering and command helper responses."""

from __future__ import annotations

from unittest.mock import patch

from utils import telegram_bot


def _reset_flags() -> None:
    telegram_bot._pause_flag.clear()
    telegram_bot._kill_flag.clear()


class TestTelegramBot:
    def setup_method(self) -> None:
        _reset_flags()

    def teardown_method(self) -> None:
        _reset_flags()

    @patch("utils.telegram_bot.send_message")
    def test_help_command_sends_help_text(self, mock_send):
        telegram_bot._handle_command("/help")

        assert mock_send.called
        sent_text = mock_send.call_args[0][0]
        assert "Command Center" in sent_text
        assert "/status" in sent_text
        assert "/kill" in sent_text

    @patch("utils.telegram_bot.send_message")
    def test_start_command_sends_help_text(self, mock_send):
        telegram_bot._handle_command("/start")

        assert mock_send.called
        sent_text = mock_send.call_args[0][0]
        assert "Command Center" in sent_text

    @patch("utils.telegram_bot.send_message")
    def test_unauthorized_kill_is_blocked(self, mock_send):
        with patch("config.settings.TELEGRAM_ALLOWED_USER_IDS", (111,)):
            telegram_bot._handle_command("/kill", from_user_id=222, from_username="intruder")

        assert not telegram_bot.is_kill_requested()
        assert not telegram_bot.is_paused()
        assert not mock_send.called

    @patch("utils.telegram_bot.send_message")
    def test_authorized_kill_by_user_id(self, mock_send):
        with patch("config.settings.TELEGRAM_ALLOWED_USER_IDS", (111,)):
            telegram_bot._handle_command("/kill", from_user_id=111, from_username="operator")

        assert telegram_bot.is_kill_requested()
        assert telegram_bot.is_paused()
        assert mock_send.called

    @patch("utils.telegram_bot.send_message")
    def test_authorized_kill_by_username(self, mock_send):
        with patch("config.settings.TELEGRAM_ALLOWED_USER_IDS", tuple()):
            with patch("config.settings.TELEGRAM_ALLOWED_USERNAMES", ("trusted",)):
                telegram_bot._handle_command(
                    "/kill",
                    from_user_id=0,
                    from_username="@trusted",
                )

        assert telegram_bot.is_kill_requested()
        assert telegram_bot.is_paused()
        assert mock_send.called
