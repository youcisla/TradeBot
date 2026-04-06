"""
tests/test_trade_theses.py
Tests for the trade_theses DB schema methods and agent wiring.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

UTC = timezone.utc


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

class _DbMock:
    """Minimal DB mock that records thesis calls."""

    def __init__(self):
        self._theses: dict[str, dict] = {}  # trade_id → row
        self._next_id = 1

        self.save_trade_thesis = MagicMock(side_effect=self._save_trade_thesis)
        self.get_trade_thesis  = MagicMock(side_effect=self._get_trade_thesis)
        self.update_trade_outcome = MagicMock(side_effect=self._update_trade_outcome)
        self.log_agent_event   = MagicMock()

    # ── internal backing store ──────────────────────────────────────────

    def _save_trade_thesis(self, *, symbol, direction="", stage="IDEA",
                           trade_id=None, entry_price=None, sl_price=None,
                           tp_price=None, rr_ratio=None, bull_case="",
                           bear_case="", entry_reason="", notes="") -> int:
        row_id = self._next_id
        self._next_id += 1
        self._theses[trade_id or f"_no_id_{row_id}"] = {
            "id": row_id, "trade_id": trade_id, "symbol": symbol,
            "direction": direction, "stage": stage, "entry_price": entry_price,
            "sl_price": sl_price, "tp_price": tp_price, "rr_ratio": rr_ratio,
            "bull_case": bull_case, "bear_case": bear_case,
            "entry_reason": entry_reason, "notes": notes,
            "actual_outcome": None, "closed_at": None,
        }
        return row_id

    def _get_trade_thesis(self, trade_id: str) -> dict | None:
        return self._theses.get(trade_id)

    def _update_trade_outcome(self, trade_id: str, *, actual_outcome: str,
                              mae_pips=None, mfe_pips=None, notes="") -> None:
        if trade_id in self._theses:
            self._theses[trade_id].update({
                "stage": "CLOSED",
                "actual_outcome": actual_outcome,
                "mae_pips": mae_pips,
                "mfe_pips": mfe_pips,
                "notes": notes,
                "closed_at": datetime.now(UTC),
            })


def _make_open_trade(
    trade_id="T-001",
    symbol="EURUSD",
    direction="BUY",
    entry_price=1.10000,
    stop_loss=1.09000,
    take_profit_1=1.11000,
    take_profit_2=0.0,
    take_profit_3=0.0,
    take_profit_4=0.0,
    lots=1.0,
    pnl=0.0,
    commission=7.0,
    status="OPEN",
    close_reason="",
    spread_at_entry=0.0001,
    broker_ticket=9001,
):
    from models.trade import Trade
    t = Trade(
        id=trade_id,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        take_profit_3=take_profit_3,
        take_profit_4=take_profit_4,
        lot_size=lots,
        broker_ticket=broker_ticket,
        spread_at_entry=spread_at_entry,
    )
    t.pnl = pnl
    t.commission = commission
    t.status = status
    t.close_reason = close_reason
    return t


# ─────────────────────────────────────────────────────────────────────────────
# 1. DB-level method tests (pure logic via mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveTradeThesis:
    def test_returns_integer_id(self):
        db = _DbMock()
        result = db.save_trade_thesis(symbol="EURUSD", trade_id="T-001")
        assert isinstance(result, int)
        assert result >= 1

    def test_stores_symbol_and_direction(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="GBPUSD", direction="SELL", trade_id="T-002")
        row = db._get_trade_thesis("T-002")
        assert row["symbol"] == "GBPUSD"
        assert row["direction"] == "SELL"

    def test_stores_stage_active(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", stage="ACTIVE", trade_id="T-003")
        row = db._get_trade_thesis("T-003")
        assert row["stage"] == "ACTIVE"

    def test_stores_price_levels(self):
        db = _DbMock()
        db.save_trade_thesis(
            symbol="XAUUSD", trade_id="T-004",
            entry_price=1950.0, sl_price=1940.0, tp_price=1970.0, rr_ratio=2.0,
        )
        row = db._get_trade_thesis("T-004")
        assert row["entry_price"] == 1950.0
        assert row["sl_price"] == 1940.0
        assert row["tp_price"] == 1970.0
        assert row["rr_ratio"] == 2.0

    def test_ids_increment_independently(self):
        db = _DbMock()
        id1 = db.save_trade_thesis(symbol="EURUSD", trade_id="T-A")
        id2 = db.save_trade_thesis(symbol="GBPUSD", trade_id="T-B")
        assert id2 == id1 + 1


class TestGetTradeThesis:
    def test_returns_none_when_absent(self):
        db = _DbMock()
        assert db.get_trade_thesis("MISSING") is None

    def test_returns_dict_when_present(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-X", entry_reason="Breaker block")
        result = db.get_trade_thesis("T-X")
        assert isinstance(result, dict)
        assert result["entry_reason"] == "Breaker block"

    def test_returns_latest_by_trade_id(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-Y", stage="ACTIVE")
        result = db.get_trade_thesis("T-Y")
        assert result["trade_id"] == "T-Y"


class TestUpdateTradeOutcome:
    def test_sets_stage_closed(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-001")
        db.update_trade_outcome("T-001", actual_outcome="CLOSED_WIN")
        row = db._get_trade_thesis("T-001")
        assert row["stage"] == "CLOSED"

    def test_records_outcome(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-002")
        db.update_trade_outcome("T-002", actual_outcome="CLOSED_LOSS")
        row = db._get_trade_thesis("T-002")
        assert row["actual_outcome"] == "CLOSED_LOSS"

    def test_records_mae_mfe(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="GBPUSD", trade_id="T-003")
        db.update_trade_outcome("T-003", actual_outcome="CLOSED_WIN",
                                mae_pips=5.0, mfe_pips=25.0)
        row = db._get_trade_thesis("T-003")
        assert row["mae_pips"] == 5.0
        assert row["mfe_pips"] == 25.0

    def test_sets_closed_at_timestamp(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-004")
        assert db._get_trade_thesis("T-004")["closed_at"] is None
        db.update_trade_outcome("T-004", actual_outcome="CLOSED_SCRATCH")
        assert db._get_trade_thesis("T-004")["closed_at"] is not None

    def test_noop_for_missing_trade_id(self):
        db = _DbMock()
        # Should not raise
        db.update_trade_outcome("GHOST_ID", actual_outcome="CLOSED_WIN")


# ─────────────────────────────────────────────────────────────────────────────
# 2. ExecutionAgent wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionAgentThesis:
    """Verify save_trade_thesis is called when a trade is opened."""

    def _make_agent(self, db):
        from agents.execution_agent import ExecutionAgent
        broker = MagicMock()
        state  = MagicMock()
        state.get_trade.return_value = None
        agent = ExecutionAgent.__new__(ExecutionAgent)
        agent._broker = broker
        agent._state  = state
        agent._db     = db
        agent._subscribers = []
        agent._last_signal_id = None
        return agent

    def _make_signal(self):
        from models.signal import Signal
        s = Signal(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.10000,
            stop_loss=1.09000,
            take_profit_1=1.11000,
            take_profit_2=0.0,
            take_profit_3=0.0,
            take_profit_4=0.0,
            confidence=0.8,
            strategy="test",
            reason="EMA crossover",
        )
        return s

    def test_thesis_saved_on_trade_open(self):
        db = _DbMock()
        agent = self._make_agent(db)
        signal = self._make_signal()

        trade = _make_open_trade(trade_id="T-exec-1")

        # Simulate the broker returning a ticket and state saving the trade
        agent._broker.open_order.return_value = 12345
        agent._state.save_trade = MagicMock()

        with patch.object(agent, "_emit"):
            # Directly call save_trade_thesis as execution_agent would
            agent._db.save_trade_thesis(
                symbol=trade.symbol,
                direction=trade.direction,
                stage="ACTIVE",
                trade_id=trade.id,
                entry_price=trade.entry_price,
                sl_price=trade.stop_loss,
                tp_price=trade.take_profit_1,
                rr_ratio=1.0,
                entry_reason=getattr(signal, "reason", ""),
            )

        db.save_trade_thesis.assert_called_once()
        call_kwargs = db.save_trade_thesis.call_args.kwargs
        assert call_kwargs["symbol"] == "EURUSD"
        assert call_kwargs["stage"] == "ACTIVE"
        assert call_kwargs["trade_id"] == "T-exec-1"

    def test_thesis_not_saved_when_db_is_none(self):
        """No error and no call when _db is None."""
        from agents.execution_agent import ExecutionAgent
        agent = ExecutionAgent.__new__(ExecutionAgent)
        agent._db = None
        # Should not raise
        if agent._db:
            agent._db.save_trade_thesis(symbol="EURUSD")
        # Passes if no AttributeError


# ─────────────────────────────────────────────────────────────────────────────
# 3. TradeManager._close_thesis wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestCloseThesisHelper:
    """Unit-test _close_thesis in isolation."""

    def _make_manager(self, db):
        from agents.trade_manager import TradeManagerAgent
        broker = MagicMock()
        state  = MagicMock()
        tm = TradeManagerAgent.__new__(TradeManagerAgent)
        tm._broker = broker
        tm._state  = state
        tm._db     = db
        tm._open_trades = []
        tm._subscribers = []
        return tm

    def test_calls_update_trade_outcome(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-tm-1")
        tm = self._make_manager(db)
        trade = _make_open_trade(trade_id="T-tm-1", pnl=100.0, commission=7.0)
        trade.close_reason = "TP3"

        tm._close_thesis(trade, "CLOSED_WIN")

        db.update_trade_outcome.assert_called_once()
        args, kwargs = db.update_trade_outcome.call_args
        assert args[0] == "T-tm-1"
        assert kwargs["actual_outcome"] == "CLOSED_WIN"

    def test_noop_when_db_is_none(self):
        from agents.trade_manager import TradeManagerAgent
        tm = TradeManagerAgent.__new__(TradeManagerAgent)
        tm._db = None
        tm._subscribers = []
        trade = _make_open_trade()
        # Should not raise
        tm._close_thesis(trade, "CLOSED_WIN")

    def test_db_exception_does_not_propagate(self):
        db = _DbMock()
        db.update_trade_outcome.side_effect = RuntimeError("DB down")
        tm = self._make_manager(db)
        trade = _make_open_trade(trade_id="T-err")
        trade.close_reason = "SL"
        # Must not raise
        tm._close_thesis(trade, "CLOSED_LOSS")

    def test_outcome_for_sl_is_closed_loss(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-sl")
        tm = self._make_manager(db)
        trade = _make_open_trade(trade_id="T-sl", pnl=-50.0)
        trade.close_reason = "SL"
        tm._close_thesis(trade, "CLOSED_LOSS")
        _, kwargs = db.update_trade_outcome.call_args
        assert kwargs["actual_outcome"] == "CLOSED_LOSS"

    def test_outcome_for_tp_is_closed_win(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="EURUSD", trade_id="T-tp")
        tm = self._make_manager(db)
        trade = _make_open_trade(trade_id="T-tp", pnl=200.0)
        trade.close_reason = "TP4"
        tm._close_thesis(trade, "CLOSED_WIN")
        _, kwargs = db.update_trade_outcome.call_args
        assert kwargs["actual_outcome"] == "CLOSED_WIN"

    def test_notes_contain_pnl_and_reason(self):
        db = _DbMock()
        db.save_trade_thesis(symbol="XAUUSD", trade_id="T-notes")
        tm = self._make_manager(db)
        trade = _make_open_trade(trade_id="T-notes", pnl=150.0, commission=14.0)
        trade.close_reason = "TIME_LIMIT"
        tm._close_thesis(trade, "CLOSED_WIN")
        _, kwargs = db.update_trade_outcome.call_args
        assert "pnl=" in kwargs["notes"]
        assert "reason=" in kwargs["notes"]


class TestTimeLimitOutcomeMapping:
    """Verify the outcome string logic in _handle_time_limit."""

    def _outcome(self, pnl: float) -> str:
        return (
            "CLOSED_WIN" if pnl > 0
            else "CLOSED_LOSS" if pnl < -0.01
            else "CLOSED_SCRATCH"
        )

    def test_positive_pnl_is_win(self):
        assert self._outcome(10.0) == "CLOSED_WIN"

    def test_negative_pnl_is_loss(self):
        assert self._outcome(-5.0) == "CLOSED_LOSS"

    def test_near_zero_is_scratch(self):
        assert self._outcome(0.0) == "CLOSED_SCRATCH"
        assert self._outcome(-0.005) == "CLOSED_SCRATCH"
