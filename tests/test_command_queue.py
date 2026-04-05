from __future__ import annotations

from typing import Any

from main import _process_commands


class _FakeDB:
    def __init__(self, commands: list[dict[str, Any]]) -> None:
        self._commands = commands
        self.updates: list[tuple[int, str, str, bool]] = []
        self.events: list[tuple[str, str, str, dict[str, Any] | None]] = []

    def get_pending_commands(self) -> list[dict[str, Any]]:
        return self._commands

    def update_command(
        self,
        cmd_id: int,
        status: str,
        result: str | None = None,
        *,
        set_executed: bool = True,
    ) -> None:
        self.updates.append((cmd_id, status, result or "", set_executed))

    def log_agent_event(
        self,
        agent: str,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.events.append((agent, level, message, data))


class _FakeTradeManager:
    def __init__(self) -> None:
        self.close_all_reasons: list[str] = []
        self.closed_trade_ids: list[tuple[str, str]] = []

    def close_all(self, reason: str) -> None:
        self.close_all_reasons.append(reason)

    def close_trade(self, trade_id: str, reason: str) -> None:
        self.closed_trade_ids.append((trade_id, reason))


def test_close_all_command_executes(monkeypatch) -> None:
    db = _FakeDB(
        [
            {
                "id": 1,
                "command": "close_all",
                "payload": {"_meta": {"traceId": "cmd_trace_1"}},
            }
        ]
    )
    trade_manager = _FakeTradeManager()

    monkeypatch.setattr("main.telegram_bot.is_kill_requested", lambda: False)
    monkeypatch.setattr("main.telegram_bot.send_message", lambda _: None)

    _process_commands(db, trade_manager, tool_system=None)

    assert trade_manager.close_all_reasons == ["UI_CLOSE_ALL"]
    assert any(status == "running" for _, status, _, _ in db.updates)
    done_updates = [u for u in db.updates if u[1] == "done"]
    assert len(done_updates) == 1
    assert "trace=cmd_trace_1" in done_updates[0][2]
    assert "duration_ms=" in done_updates[0][2]


def test_close_trade_accepts_trade_id_or_tradeId(monkeypatch) -> None:
    db = _FakeDB(
        [
            {
                "id": 9,
                "command": "close_trade",
                "payload": {"tradeId": "trade-123", "_meta": {"traceId": "cmd_trace_2"}},
            }
        ]
    )
    trade_manager = _FakeTradeManager()

    monkeypatch.setattr("main.telegram_bot.is_kill_requested", lambda: False)
    monkeypatch.setattr("main.telegram_bot.send_message", lambda _: None)

    _process_commands(db, trade_manager, tool_system=None)

    assert trade_manager.closed_trade_ids == [("trade-123", "UI_CLOSE")]
    done_updates = [u for u in db.updates if u[1] == "done"]
    assert len(done_updates) == 1
    assert "trace=cmd_trace_2" in done_updates[0][2]
