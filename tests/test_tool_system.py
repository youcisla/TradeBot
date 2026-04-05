from __future__ import annotations

from pathlib import Path

from utils import telegram_bot
from utils.tool_system import AutonomousToolSystem


class _FakeDoctorReport:
    def __init__(self, has_failures: bool, has_warnings: bool = False):
        self.has_failures = has_failures
        self.has_warnings = has_warnings
        self.checks = []
        self.recommendations = []


class _FakeDB:
    def __init__(self) -> None:
        self.events = []
        self.faults = {
            "EURUSD": {"fail_count": 0, "disabled_until": None},
            "BTCUSD": {"fail_count": 2, "disabled_until": None},
        }
        self.confidence = {"sma_crossover": 0.5}

    def log_agent_event(self, agent: str, level: str, message: str, data=None) -> None:
        self.events.append({"agent": agent, "level": level, "message": message, "data": data})

    def load_symbol_faults(self):
        return dict(self.faults)

    def save_symbol_fault(self, symbol: str, fail_count: int, disabled_until):
        if fail_count == 0 and disabled_until is None:
            self.faults.pop(symbol, None)

    def get_recent_strategy_regime_stats(self, lookback_hours: int = 48, min_trades: int = 3):
        return [
            {
                "strategy": "sma_crossover",
                "market_condition": "trending",
                "trades": 10,
                "wins": 7,
                "avg_score": 72.0,
                "avg_pnl": 12.0,
            }
        ]

    def get_confidence(self, strategy: str) -> float:
        return float(self.confidence.get(strategy, 0.5))

    def upsert_confidence(self, strategy: str, confidence: float, total_trades: int, total_score: int):
        self.confidence[strategy] = float(confidence)


class _FakeBroker:
    def get_balance(self) -> float:
        return 10000.0

    def get_equity(self) -> float:
        return 10020.0


class _FakeTradeManager:
    def __init__(self) -> None:
        self.reconcile_calls = 0

    def reconcile(self) -> None:
        self.reconcile_calls += 1


class _FakeRiskAgent:
    def __init__(self) -> None:
        self.caps = None

    def set_emergency_caps(self, *, max_risk_per_trade: float, max_open_trades: int):
        self.caps = {
            "max_risk_per_trade": max_risk_per_trade,
            "max_open_trades": max_open_trades,
        }

    def clear_emergency_caps(self):
        self.caps = None


def test_tool_catalog_has_core_tools(tmp_path: Path):
    system = AutonomousToolSystem(
        repo_root=tmp_path,
        db=_FakeDB(),
        broker=_FakeBroker(),
        trade_manager=_FakeTradeManager(),
    )

    names = {t["name"] for t in system.list_tools()}
    assert "ops_doctor_scan" in names
    assert "broker_health_check" in names
    assert "pause_if_critical" in names


def test_pause_when_doctor_reports_critical(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("utils.tool_system.run_doctor", lambda _: _FakeDoctorReport(has_failures=True))
    monkeypatch.setattr(telegram_bot, "send_message", lambda _: None)

    system = AutonomousToolSystem(
        repo_root=tmp_path,
        db=_FakeDB(),
        broker=_FakeBroker(),
        trade_manager=_FakeTradeManager(),
    )

    telegram_bot.resume()
    doctor_result = system.execute_tool("ops_doctor_scan")
    pause_result = system.execute_tool("pause_if_critical")

    assert doctor_result.ok is False
    assert pause_result.ok is True
    assert telegram_bot.is_paused() is True


def test_resume_when_healthy(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("utils.tool_system.run_doctor", lambda _: _FakeDoctorReport(has_failures=False))
    monkeypatch.setattr(telegram_bot, "send_message", lambda _: None)

    system = AutonomousToolSystem(
        repo_root=tmp_path,
        db=_FakeDB(),
        broker=_FakeBroker(),
        trade_manager=_FakeTradeManager(),
    )

    telegram_bot.pause()
    doctor_result = system.execute_tool("ops_doctor_scan")
    resume_result = system.execute_tool("resume_if_healthy")

    assert doctor_result.ok is True
    assert resume_result.ok is True
    assert telegram_bot.is_paused() is False


def test_strategy_reweight_updates_confidence(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(telegram_bot, "send_message", lambda _: None)
    db = _FakeDB()
    system = AutonomousToolSystem(
        repo_root=tmp_path,
        db=db,
        broker=_FakeBroker(),
        trade_manager=_FakeTradeManager(),
    )

    before = db.get_confidence("sma_crossover")
    result = system.execute_tool("strategy_reweight_recent_regime")
    after = db.get_confidence("sma_crossover")

    assert result.ok is True
    assert after > before


def test_emergency_mode_activate_deactivate(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(telegram_bot, "send_message", lambda _: None)
    symbols = ["EURUSD", "BTCUSD", "XAUUSD", "ETHUSD", "USDJPY"]

    def get_symbols():
        return symbols[:]

    def set_symbols(new_symbols):
        symbols.clear()
        symbols.extend(new_symbols)

    risk = _FakeRiskAgent()
    system = AutonomousToolSystem(
        repo_root=tmp_path,
        db=_FakeDB(),
        broker=_FakeBroker(),
        trade_manager=_FakeTradeManager(),
        risk_agent=risk,
        get_active_symbols=get_symbols,
        set_active_symbols=set_symbols,
        base_symbols=["EURUSD", "BTCUSD", "XAUUSD", "ETHUSD", "USDJPY"],
    )

    on_result = system.execute_tool("emergency_mode_activate", {"reason": "test"})
    assert on_result.ok is True
    assert len(symbols) <= 4
    assert risk.caps is not None

    off_result = system.execute_tool("emergency_mode_deactivate", {"reason": "test"})
    assert off_result.ok is True
    assert "USDJPY" in symbols
    assert risk.caps is None
