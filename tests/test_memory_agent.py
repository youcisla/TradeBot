"""Tests for agents/memory_agent.py — Persistent Agent Memory (Todo #6)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents.memory_agent import (
    BLOCK_INCIDENT_LOG,
    BLOCK_MARKET_REGIME,
    BLOCK_MODEL_PERFORMANCE,
    BLOCK_PERFORMANCE_JOURNAL,
    BLOCK_SESSION_CONTEXT,
    BLOCK_STRATEGY_NOTES,
    BLOCK_TRADE_HISTORY,
    BLOCK_USER_PREFERENCES,
    MemoryAgent,
)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _db(read_return=None):
    """Return a mock DB whose read_memory_block returns *read_return*."""
    mock = MagicMock()
    mock.read_memory_block.return_value = read_return
    return mock


def _trade(id_="T1", symbol="EURUSD", direction="buy", pnl=10.0, outcome="win", close_time=None):
    t = SimpleNamespace(
        id=id_,
        symbol=symbol,
        direction=direction,
        pnl=pnl,
        outcome=outcome,
        close_time=close_time or datetime.now(timezone.utc),  # datetime, not str
    )
    return t


# ─── TestMemoryAgentInit ──────────────────────────────────────────────────────


class TestMemoryAgentInit:
    def test_no_args(self):
        agent = MemoryAgent()
        assert agent is not None

    def test_with_db(self):
        db = _db()
        agent = MemoryAgent(db=db)
        assert agent is not None


# ─── TestWriteBlock ───────────────────────────────────────────────────────────


class TestWriteBlock:
    def test_no_db_returns_false(self):
        agent = MemoryAgent()
        result = agent.write_block("test", "value")
        assert result is False

    def test_db_write_called(self):
        db = _db()
        agent = MemoryAgent(db=db)
        result = agent.write_block("test_block", "hello")
        db.write_memory_block.assert_called_once_with("test_block", "hello")
        assert result is True

    def test_db_exception_returns_false(self):
        db = _db()
        db.write_memory_block.side_effect = RuntimeError("db down")
        agent = MemoryAgent(db=db)
        result = agent.write_block("test_block", "hello")
        assert result is False


# ─── TestReadBlock ────────────────────────────────────────────────────────────


class TestReadBlock:
    def test_no_db_returns_none(self):
        agent = MemoryAgent()
        assert agent.read_block("anything") is None

    def test_found_returns_content(self):
        db = _db(read_return="some_content")
        agent = MemoryAgent(db=db)
        result = agent.read_block("test_block")
        db.read_memory_block.assert_called_once_with("test_block")
        assert result == "some_content"

    def test_not_found_returns_none(self):
        db = _db(read_return=None)
        agent = MemoryAgent(db=db)
        result = agent.read_block("missing_block")
        assert result is None


# ─── TestUpdateSessionContext ────────────────────────────────────────────────


class TestUpdateSessionContext:
    def test_writes_session_block(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_session_context(["EURUSD", "GBPUSD"], regime="BULL")
        assert db.write_memory_block.called
        call_args = db.write_memory_block.call_args
        block_name, content = call_args[0]
        assert block_name == BLOCK_SESSION_CONTEXT
        payload = json.loads(content)
        assert payload["symbols"] == ["EURUSD", "GBPUSD"]
        assert payload["regime"] == "BULL"
        assert "started_at" in payload

    def test_custom_started_at(self):
        db = _db()
        agent = MemoryAgent(db=db)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        agent.update_session_context(["USDJPY"], started_at=ts)
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["started_at"] == ts.isoformat()


# ─── TestUpdateTradeHistory ──────────────────────────────────────────────────


class TestUpdateTradeHistory:
    def test_empty_list(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_trade_history([])
        assert db.write_memory_block.called
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["trades"] == []

    def test_truncates_to_20(self):
        db = _db()
        agent = MemoryAgent(db=db)
        trades = [_trade(id_=f"T{i}") for i in range(30)]
        agent.update_trade_history(trades)
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert len(payload["trades"]) == 20

    def test_outcome_mapped(self):
        db = _db()
        agent = MemoryAgent(db=db)
        trade = _trade(pnl=50.0, outcome="win")
        agent.update_trade_history([trade])
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["trades"][0]["pnl"] == 50.0
        assert payload["trades"][0]["outcome"] == "win"


# ─── TestUpdateModelPerformance ──────────────────────────────────────────────


class TestUpdateModelPerformance:
    def test_writes_with_timestamp(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_model_performance({"accuracy": 0.75, "sharpe": 1.2})
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["accuracy"] == 0.75
        assert "updated_at" in payload

    def test_empty_dict(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_model_performance({})
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert "updated_at" in payload


# ─── TestUpdateMarketRegime ──────────────────────────────────────────────────


class TestUpdateMarketRegime:
    def test_dict_adds_timestamp(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_market_regime({"risk_tier": "CLEAR", "vix": 15.0})
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["risk_tier"] == "CLEAR"
        assert "updated_at" in payload

    def test_string_stored_directly(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_market_regime("BULL_REGIME_2024")
        _, content = db.write_memory_block.call_args[0]
        assert content == "BULL_REGIME_2024"


# ─── TestAppendIncident ──────────────────────────────────────────────────────


class TestAppendIncident:
    def test_empty_log_creates_entry(self):
        db = _db(read_return=None)
        agent = MemoryAgent(db=db)
        agent.append_incident("BOT_CRASH")
        _, content = db.write_memory_block.call_args[0]
        entries = json.loads(content)
        assert len(entries) == 1
        assert entries[0]["event"] == "BOT_CRASH"
        assert "ts" in entries[0]

    def test_appends_to_existing(self):
        existing = json.dumps([{"ts": "2024-01-01T00:00:00", "event": "OLD"}])
        db = _db(read_return=existing)
        agent = MemoryAgent(db=db)
        agent.append_incident("NEW_EVENT")
        _, content = db.write_memory_block.call_args[0]
        entries = json.loads(content)
        assert len(entries) == 2
        assert entries[-1]["event"] == "NEW_EVENT"

    def test_caps_at_50(self):
        existing_entries = [{"ts": "2024-01-01T00:00:00", "event": f"E{i}"} for i in range(50)]
        db = _db(read_return=json.dumps(existing_entries))
        agent = MemoryAgent(db=db)
        agent.append_incident("OVERFLOW")
        _, content = db.write_memory_block.call_args[0]
        entries = json.loads(content)
        assert len(entries) == 50
        assert entries[-1]["event"] == "OVERFLOW"


# ─── TestUpdatePerformanceJournal ────────────────────────────────────────────


class TestUpdatePerformanceJournal:
    def test_writes_with_timestamp(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_performance_journal({"trades": 5, "pnl": 120.0})
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["trades"] == 5
        assert "updated_at" in payload

    def test_custom_stats(self):
        db = _db()
        agent = MemoryAgent(db=db)
        agent.update_performance_journal({"win_rate": 0.6})
        _, content = db.write_memory_block.call_args[0]
        payload = json.loads(content)
        assert payload["win_rate"] == 0.6


# ─── TestReadMarketRegime ────────────────────────────────────────────────────


class TestReadMarketRegime:
    def test_no_db_returns_none(self):
        agent = MemoryAgent()
        assert agent.read_market_regime() is None

    def test_stored_value_returned(self):
        db = _db(read_return='{"risk_tier": "PRIORITY"}')
        agent = MemoryAgent(db=db)
        result = agent.read_market_regime()
        assert result == '{"risk_tier": "PRIORITY"}'


# ─── TestMemoryBlockNames ────────────────────────────────────────────────────


class TestMemoryBlockNames:
    def test_all_eight_blocks_defined(self):
        blocks = [
            BLOCK_SESSION_CONTEXT,
            BLOCK_TRADE_HISTORY,
            BLOCK_MODEL_PERFORMANCE,
            BLOCK_MARKET_REGIME,
            BLOCK_USER_PREFERENCES,
            BLOCK_STRATEGY_NOTES,
            BLOCK_INCIDENT_LOG,
            BLOCK_PERFORMANCE_JOURNAL,
        ]
        assert len(blocks) == 8

    def test_all_are_strings(self):
        blocks = [
            BLOCK_SESSION_CONTEXT,
            BLOCK_TRADE_HISTORY,
            BLOCK_MODEL_PERFORMANCE,
            BLOCK_MARKET_REGIME,
            BLOCK_USER_PREFERENCES,
            BLOCK_STRATEGY_NOTES,
            BLOCK_INCIDENT_LOG,
            BLOCK_PERFORMANCE_JOURNAL,
        ]
        assert all(isinstance(b, str) for b in blocks)

    def test_all_unique(self):
        blocks = [
            BLOCK_SESSION_CONTEXT,
            BLOCK_TRADE_HISTORY,
            BLOCK_MODEL_PERFORMANCE,
            BLOCK_MARKET_REGIME,
            BLOCK_USER_PREFERENCES,
            BLOCK_STRATEGY_NOTES,
            BLOCK_INCIDENT_LOG,
            BLOCK_PERFORMANCE_JOURNAL,
        ]
        assert len(set(blocks)) == 8

    def test_market_regime_name(self):
        assert BLOCK_MARKET_REGIME == "market_regime"
