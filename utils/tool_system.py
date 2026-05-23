from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config import settings
from adapters.db.db import Database
from utils import telegram_bot
from utils.ops_doctor import run_doctor

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    name: str
    ok: bool
    message: str
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
            "data": self.data,
        }


class AutonomousToolSystem:
    """Built-in tool registry for autonomous diagnostics and self-healing.

    This is an internal runtime tool layer for the bot itself (not editor tools).
    It provides a controlled set of actions that can be run:
    - automatically on a schedule
    - on-demand through the bot command queue
    """

    def __init__(
        self,
        *,
        repo_root: Path,
        db: Database,
        broker: Any,
        trade_manager: Any,
        risk_agent: Any | None = None,
        get_active_symbols: Callable[[], list[str]] | None = None,
        set_active_symbols: Callable[[list[str]], None] | None = None,
        base_symbols: list[str] | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._db = db
        self._broker = broker
        self._trade_manager = trade_manager
        self._risk_agent = risk_agent
        self._get_active_symbols = get_active_symbols
        self._set_active_symbols = set_active_symbols
        self._base_symbols = list(base_symbols or [])
        self._last_doctor_has_failures = False
        self._last_doctor_warning_count = 0
        self._warning_spike_streak = 0
        self._healthy_streak = 0
        self._emergency_mode = False
        self._registry: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
            "catalog": self._tool_catalog,
            "ops_doctor_scan": self._tool_ops_doctor_scan,
            "strategy_reweight_recent_regime": self._tool_strategy_reweight_recent_regime,
            "broker_health_check": self._tool_broker_health_check,
            "reconcile_trades": self._tool_reconcile_trades,
            "pause_if_critical": self._tool_pause_if_critical,
            "resume_if_healthy": self._tool_resume_if_healthy,
            "symbol_fault_cleanup": self._tool_symbol_fault_cleanup,
            "emergency_mode_guard": self._tool_emergency_mode_guard,
            "emergency_mode_activate": self._tool_emergency_mode_activate,
            "emergency_mode_deactivate": self._tool_emergency_mode_deactivate,
        }

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {
                "name": "catalog",
                "category": "meta",
                "description": "Return built-in tool catalog",
            },
            {
                "name": "ops_doctor_scan",
                "category": "diagnostics",
                "description": "Run preflight and log diagnostics",
            },
            {
                "name": "broker_health_check",
                "category": "runtime",
                "description": "Check broker balance/equity connectivity",
            },
            {
                "name": "strategy_reweight_recent_regime",
                "category": "learning",
                "description": "Auto-reweight strategy confidence by recent win-rate regime",
            },
            {
                "name": "reconcile_trades",
                "category": "recovery",
                "description": "Run trade reconciliation immediately",
            },
            {
                "name": "pause_if_critical",
                "category": "safety",
                "description": "Pause new trades if doctor reports critical errors",
            },
            {
                "name": "resume_if_healthy",
                "category": "safety",
                "description": "Resume if bot is paused and health is clean",
            },
            {
                "name": "symbol_fault_cleanup",
                "category": "maintenance",
                "description": "Remove stale symbol fault entries",
            },
            {
                "name": "emergency_mode_guard",
                "category": "safety",
                "description": "Auto-toggle emergency mode when doctor warnings spike",
            },
            {
                "name": "emergency_mode_activate",
                "category": "safety",
                "description": "Force emergency mode (narrow symbols and risk caps)",
            },
            {
                "name": "emergency_mode_deactivate",
                "category": "safety",
                "description": "Disable emergency mode and restore normal limits",
            },
        ]

    def execute_tool(self, name: str, payload: dict[str, Any] | None = None) -> ToolResult:
        fn = self._registry.get(name)
        if fn is None:
            return ToolResult(
                name=name,
                ok=False,
                message=f"Unknown tool: {name}",
                data={"available": [t["name"] for t in self.list_tools()]},
            )

        data = payload or {}
        try:
            result = fn(data)
            self._emit_event(
                "info" if result.ok else "warn",
                f"Tool executed: {name} → {result.message}",
                result.as_dict(),
            )
            return result
        except Exception as exc:
            logger.exception("Tool execution crashed: %s", name)
            result = ToolResult(
                name=name,
                ok=False,
                message=f"Tool crashed: {exc}",
                data={},
            )
            self._emit_event("error", f"Tool crashed: {name}", result.as_dict())
            return result

    def run_cycle(self, loop_count: int, metrics: dict[str, float] | None = None) -> list[ToolResult]:
        """Run scheduled tools for one autonomous maintenance cycle."""
        plan: list[str] = [
            "ops_doctor_scan",
            "emergency_mode_guard",
            "pause_if_critical",
            "strategy_reweight_recent_regime",
            "broker_health_check",
            "reconcile_trades",
            "resume_if_healthy",
            "symbol_fault_cleanup",
        ]
        max_actions = max(1, settings.TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE)
        plan = plan[:max_actions]

        payload = {
            "loop": loop_count,
            "metrics": metrics or {},
        }
        results = [self.execute_tool(name, payload) for name in plan]
        failed = [r.name for r in results if not r.ok]
        self._emit_event(
            "info" if not failed else "warn",
            "Autonomous tool cycle completed",
            {
                "loop": loop_count,
                "failed_tools": failed,
                "executed_tools": [r.name for r in results],
                "emergency_mode": self._emergency_mode,
                "doctor_warning_count": self._last_doctor_warning_count,
            },
        )
        return results

    def _tool_catalog(self, _: dict[str, Any]) -> ToolResult:
        return ToolResult(
            name="catalog",
            ok=True,
            message="Built-in tool catalog",
            data={"tools": self.list_tools()},
        )

    def _tool_ops_doctor_scan(self, _: dict[str, Any]) -> ToolResult:
        report = run_doctor(self._repo_root)
        self._last_doctor_has_failures = report.has_failures
        self._last_doctor_warning_count = sum(1 for c in report.checks if c.status == "warn")
        return ToolResult(
            name="ops_doctor_scan",
            ok=not report.has_failures,
            message=(
                "Critical failures detected"
                if report.has_failures
                else "Doctor checks clean"
            ),
            data={
                "has_failures": report.has_failures,
                "has_warnings": report.has_warnings,
                "warning_count": self._last_doctor_warning_count,
                "checks": [
                    {"name": c.name, "status": c.status, "detail": c.detail}
                    for c in report.checks
                ],
                "recommendations": report.recommendations,
            },
        )

    def _tool_strategy_reweight_recent_regime(self, _: dict[str, Any]) -> ToolResult:
        lookback_hours = max(1, settings.TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS)
        min_trades = max(1, settings.TOOL_SYSTEM_REWEIGHT_MIN_TRADES)
        rows = self._db.get_recent_strategy_regime_stats(
            lookback_hours=lookback_hours,
            min_trades=min_trades,
        )
        if not rows:
            return ToolResult(
                name="strategy_reweight_recent_regime",
                ok=True,
                message="No sufficient trade-score data for reweighting",
                data={"updated": []},
            )

        # Keep one dominant regime row per strategy (highest trade count).
        per_strategy: dict[str, dict[str, Any]] = {}
        for row in rows:
            strategy = str(row.get("strategy", "")).strip()
            if not strategy:
                continue
            existing = per_strategy.get(strategy)
            if existing is None or int(row.get("trades", 0)) > int(existing.get("trades", 0)):
                per_strategy[strategy] = row

        updates: list[dict[str, Any]] = []
        for strategy, row in per_strategy.items():
            trades = int(row.get("trades", 0))
            wins = int(row.get("wins", 0))
            win_rate = (wins / trades) if trades > 0 else 0.0
            regime = str(row.get("market_condition", "unknown"))
            avg_score = float(row.get("avg_score", 0.0))
            current_conf = float(self._db.get_confidence(strategy))

            # Small bounded adjustments by quality profile.
            delta = 0.0
            if win_rate >= 0.65:
                delta += 0.05
            elif win_rate >= 0.55:
                delta += 0.02
            elif win_rate <= 0.35:
                delta -= 0.05
            elif win_rate <= 0.45:
                delta -= 0.02

            if regime == "trending" and win_rate >= 0.55:
                delta += 0.01
            if regime == "ranging" and win_rate <= 0.45:
                delta -= 0.01

            if avg_score >= 70:
                delta += 0.01
            elif avg_score <= 45:
                delta -= 0.01

            new_conf = max(0.20, min(0.95, round(current_conf + delta, 4)))
            if abs(new_conf - current_conf) < 0.005:
                continue

            self._db.upsert_confidence(strategy, new_conf, 0, 0)
            updates.append(
                {
                    "strategy": strategy,
                    "regime": regime,
                    "trades": trades,
                    "win_rate": round(win_rate, 4),
                    "avg_score": round(avg_score, 2),
                    "old_confidence": round(current_conf, 4),
                    "new_confidence": new_conf,
                }
            )

        return ToolResult(
            name="strategy_reweight_recent_regime",
            ok=True,
            message=f"Updated {len(updates)} strategy confidence weights",
            data={
                "lookback_hours": lookback_hours,
                "min_trades": min_trades,
                "updated": updates,
            },
        )

    def _tool_broker_health_check(self, _: dict[str, Any]) -> ToolResult:
        balance = float(self._broker.get_balance())
        equity = float(self._broker.get_equity())
        ok = balance > 0 and equity > 0
        return ToolResult(
            name="broker_health_check",
            ok=ok,
            message=f"balance={balance:.2f}, equity={equity:.2f}",
            data={"balance": balance, "equity": equity},
        )

    def _tool_reconcile_trades(self, _: dict[str, Any]) -> ToolResult:
        self._trade_manager.reconcile()
        return ToolResult(
            name="reconcile_trades",
            ok=True,
            message="Reconciliation completed",
            data={},
        )

    def _tool_pause_if_critical(self, _: dict[str, Any]) -> ToolResult:
        if not settings.TOOL_SYSTEM_STRICT_CRITICAL:
            return ToolResult(
                name="pause_if_critical",
                ok=True,
                message="Strict critical mode disabled",
                data={"paused": telegram_bot.is_paused()},
            )

        if self._last_doctor_has_failures and not telegram_bot.is_paused():
            telegram_bot.pause()
            telegram_bot.send_message(
                "⏸️ Tool System: critical diagnostics detected, bot paused for safety."
            )
            return ToolResult(
                name="pause_if_critical",
                ok=True,
                message="Bot paused due to critical diagnostics",
                data={"paused": True},
            )

        return ToolResult(
            name="pause_if_critical",
            ok=True,
            message="No critical pause needed",
            data={"paused": telegram_bot.is_paused()},
        )

    def _tool_resume_if_healthy(self, _: dict[str, Any]) -> ToolResult:
        if telegram_bot.is_paused() and not self._last_doctor_has_failures:
            telegram_bot.resume()
            telegram_bot.send_message("▶️ Tool System: diagnostics healthy, bot resumed.")
            return ToolResult(
                name="resume_if_healthy",
                ok=True,
                message="Bot resumed",
                data={"paused": False},
            )
        return ToolResult(
            name="resume_if_healthy",
            ok=True,
            message="Resume not needed",
            data={"paused": telegram_bot.is_paused()},
        )

    def _tool_symbol_fault_cleanup(self, _: dict[str, Any]) -> ToolResult:
        faults = self._db.load_symbol_faults()
        removed = 0
        for symbol, payload in faults.items():
            fail_count = int(payload.get("fail_count", 0))
            disabled_until = payload.get("disabled_until")
            if fail_count <= 0 and disabled_until is None:
                self._db.save_symbol_fault(symbol, 0, None)
                removed += 1

        return ToolResult(
            name="symbol_fault_cleanup",
            ok=True,
            message=f"Cleanup complete (removed={removed})",
            data={"removed": removed, "total_faults": len(faults)},
        )

    def _tool_emergency_mode_guard(self, _: dict[str, Any]) -> ToolResult:
        threshold = max(1, settings.TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD)
        recovery_cycles = max(1, settings.TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES)

        if self._last_doctor_warning_count >= threshold:
            self._warning_spike_streak += 1
            self._healthy_streak = 0
        else:
            self._warning_spike_streak = 0
            if self._last_doctor_warning_count == 0 and not self._last_doctor_has_failures:
                self._healthy_streak += 1
            else:
                self._healthy_streak = 0

        if self._warning_spike_streak >= 1 and not self._emergency_mode:
            result = self._activate_emergency_mode("doctor warning spike")
            return ToolResult(
                name="emergency_mode_guard",
                ok=result.ok,
                message=result.message,
                data={
                    "warning_count": self._last_doctor_warning_count,
                    "threshold": threshold,
                    "emergency_mode": self._emergency_mode,
                },
            )

        if self._emergency_mode and self._healthy_streak >= recovery_cycles:
            result = self._deactivate_emergency_mode("doctor recovered")
            return ToolResult(
                name="emergency_mode_guard",
                ok=result.ok,
                message=result.message,
                data={
                    "healthy_streak": self._healthy_streak,
                    "recovery_cycles": recovery_cycles,
                    "emergency_mode": self._emergency_mode,
                },
            )

        return ToolResult(
            name="emergency_mode_guard",
            ok=True,
            message="No emergency mode change",
            data={
                "warning_count": self._last_doctor_warning_count,
                "warning_spike_streak": self._warning_spike_streak,
                "healthy_streak": self._healthy_streak,
                "emergency_mode": self._emergency_mode,
            },
        )

    def _tool_emergency_mode_activate(self, payload: dict[str, Any]) -> ToolResult:
        reason = str(payload.get("reason", "manual activation"))
        return self._activate_emergency_mode(reason)

    def _tool_emergency_mode_deactivate(self, payload: dict[str, Any]) -> ToolResult:
        reason = str(payload.get("reason", "manual deactivation"))
        return self._deactivate_emergency_mode(reason)

    def _activate_emergency_mode(self, reason: str) -> ToolResult:
        emergency_symbols = [
            s.strip()
            for s in settings.TOOL_SYSTEM_EMERGENCY_SYMBOLS.split(",")
            if s.strip()
        ]
        if self._set_active_symbols is not None:
            if self._base_symbols:
                emergency_symbols = [s for s in emergency_symbols if s in set(self._base_symbols)]
            if emergency_symbols:
                self._set_active_symbols(emergency_symbols)

        if self._risk_agent is not None:
            self._risk_agent.set_emergency_caps(
                max_risk_per_trade=settings.TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE,
                max_open_trades=settings.TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES,
            )

        self._emergency_mode = True
        telegram_bot.pause()
        telegram_bot.send_message(
            "🚨 Tool System: EMERGENCY MODE ON (symbols narrowed + risk caps tightened)."
        )

        return ToolResult(
            name="emergency_mode_activate",
            ok=True,
            message=f"Emergency mode activated ({reason})",
            data={
                "reason": reason,
                "symbols": self._get_active_symbols() if self._get_active_symbols else emergency_symbols,
                "max_risk_per_trade": settings.TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE,
                "max_open_trades": settings.TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES,
                "paused": telegram_bot.is_paused(),
            },
        )

    def _deactivate_emergency_mode(self, reason: str) -> ToolResult:
        if self._set_active_symbols is not None and self._base_symbols:
            self._set_active_symbols(list(self._base_symbols))

        if self._risk_agent is not None:
            self._risk_agent.clear_emergency_caps()

        self._emergency_mode = False
        self._warning_spike_streak = 0
        self._healthy_streak = 0
        if not self._last_doctor_has_failures:
            telegram_bot.resume()
            telegram_bot.send_message("✅ Tool System: emergency mode cleared, normal mode restored.")

        return ToolResult(
            name="emergency_mode_deactivate",
            ok=True,
            message=f"Emergency mode deactivated ({reason})",
            data={
                "reason": reason,
                "symbols": self._get_active_symbols() if self._get_active_symbols else self._base_symbols,
                "paused": telegram_bot.is_paused(),
            },
        )

    def _emit_event(self, level: str, message: str, data: dict[str, Any]) -> None:
        try:
            self._db.log_agent_event("tool_system", level, message, data)
        except Exception:
            logger.debug("Failed to write tool_system event", exc_info=True)


def result_to_text(result: ToolResult) -> str:
    return json.dumps(result.as_dict(), ensure_ascii=True)