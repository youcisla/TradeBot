"""Command processor — extracted from main.py's _process_commands()."""

import json
import logging
import time
from typing import Callable

from database.db import Database
from agents.trade_manager import TradeManagerAgent
from state.persistence import StatePersistence
from utils import telegram_bot
from utils.tool_system import AutonomousToolSystem, result_to_text

logger = logging.getLogger(__name__)


def process_commands(
    db: Database,
    trade_manager: TradeManagerAgent,
    request_shutdown: Callable[[], None],
    tool_system: AutonomousToolSystem | None = None,
    state: StatePersistence | None = None,
) -> None:
    """Poll the bot_commands table and Telegram kill flag for pending commands."""

    def _extract_trace_id(payload: object) -> str:
        if isinstance(payload, dict):
            meta = payload.get("_meta")
            if isinstance(meta, dict):
                trace_id = meta.get("traceId")
                if isinstance(trace_id, str) and trace_id.strip():
                    return trace_id
        return f"cmd-{int(time.time() * 1000)}"

    def _final_result_message(base: str, *, trace_id: str, duration_ms: float) -> str:
        return f"{base} | trace={trace_id} | duration_ms={duration_ms:.1f}"

    # ── Check Telegram kill flag ─────────────────────────────────────────
    if telegram_bot.is_kill_requested():
        telegram_bot.pause()
        trade_manager.close_all("KILL_SWITCH")
        telegram_bot.send_message("All positions closed. Bot stopped.")
        request_shutdown()
        return

    # ── Process DB command queue (web dashboard) ─────────────────────
    claim_fn = getattr(db, "claim_pending_commands", None)
    if callable(claim_fn):
        pending_commands = claim_fn(limit=25)
        already_marked_running = True
    else:
        pending_commands = db.get_pending_commands()
        already_marked_running = False

    for cmd in pending_commands:
        cmd_name = cmd["command"]
        payload = cmd.get("payload") if isinstance(cmd.get("payload"), dict) else {}
        trace_id = _extract_trace_id(payload)
        started_at = time.perf_counter()

        if not already_marked_running:
            db.update_command(
                cmd["id"],
                "running",
                f"Started {cmd_name}",
                set_executed=False,
            )
        db.log_agent_event(
            "logging",
            "info",
            f"Command started: {cmd_name}",
            {"command_id": cmd["id"], "command": cmd_name, "trace_id": trace_id},
        )

        try:
            if cmd_name == "kill":
                telegram_bot.pause()
                trade_manager.close_all("UI_KILL")
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                db.update_command(
                    cmd["id"],
                    "done",
                    _final_result_message(
                        "All trades closed, shutting down",
                        trace_id=trace_id,
                        duration_ms=duration_ms,
                    ),
                )
                telegram_bot.send_message("KILL from dashboard — all positions closed, shutting down.")
                request_shutdown()

            elif cmd_name == "pause":
                telegram_bot.pause()
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                db.update_command(
                    cmd["id"],
                    "done",
                    _final_result_message("Bot paused", trace_id=trace_id, duration_ms=duration_ms),
                )
                telegram_bot.send_message("Bot PAUSED (from dashboard)")

            elif cmd_name == "resume":
                telegram_bot.resume()
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                db.update_command(
                    cmd["id"],
                    "done",
                    _final_result_message("Bot resumed", trace_id=trace_id, duration_ms=duration_ms),
                )
                telegram_bot.send_message("Bot RESUMED (from dashboard)")

            elif cmd_name == "close_all":
                trade_manager.close_all("UI_CLOSE_ALL")
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                db.update_command(
                    cmd["id"],
                    "done",
                    _final_result_message(
                        "All open trades closed",
                        trace_id=trace_id,
                        duration_ms=duration_ms,
                    ),
                )
                telegram_bot.send_message("All open trades closed (from dashboard)")

            elif cmd_name == "close_trade":
                trade_id = payload.get("trade_id") or payload.get("tradeId") or ""
                trade_manager.close_trade(trade_id, "UI_CLOSE")
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                db.update_command(
                    cmd["id"],
                    "done",
                    _final_result_message(
                        f"Trade {trade_id} closed",
                        trace_id=trace_id,
                        duration_ms=duration_ms,
                    ),
                )
                telegram_bot.send_message(f"Trade {trade_id} closed (from dashboard)")

            elif cmd_name == "skill":
                from utils.skill_manager import SkillManager
                action = payload.get("action", "")
                skill_name = payload.get("skill", "")
                sm = SkillManager(db=db)
                if action == "list":
                    result = sm.list_skills()
                    db.log_agent_event("skill_manager", "info",
                                       f"Skills listed: {len(result)} found",
                                       {"skills": result})
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message(str(result), trace_id=trace_id, duration_ms=duration_ms),
                    )
                elif action == "read" and skill_name:
                    content = sm.read_skill(skill_name)
                    db.log_agent_event("skill_manager", "info",
                                       f"Skill read: {skill_name}",
                                       {"content": content[:500]})
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message(content[:2000], trace_id=trace_id, duration_ms=duration_ms),
                    )
                elif action == "apply" and skill_name:
                    argument = payload.get("argument", "")
                    rendered = sm.apply_skill(skill_name, argument)
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message(rendered[:2000], trace_id=trace_id, duration_ms=duration_ms),
                    )
                else:
                    db.update_command(cmd["id"], "failed",
                                     f"Unknown skill action: {action}")

            elif cmd_name == "tool":
                action = payload.get("action", "")
                if tool_system is None:
                    db.update_command(cmd["id"], "failed", "Tool system not initialized")
                elif action == "list":
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message(
                            json.dumps({"tools": tool_system.list_tools()}, ensure_ascii=True),
                            trace_id=trace_id,
                            duration_ms=duration_ms,
                        ),
                    )
                elif action == "run":
                    tool_name = str(payload.get("tool", "")).strip()
                    result = tool_system.execute_tool(tool_name, payload)
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message(result_to_text(result), trace_id=trace_id, duration_ms=duration_ms),
                    )
                else:
                    db.update_command(cmd["id"], "failed", f"Unknown tool action: {action}")

            elif cmd_name == "sync_mt5":
                if state is None:
                    db.update_command(cmd["id"], "failed", "State persistence not available")
                else:
                    state.sync_mt5_to_db()
                    duration_ms = (time.perf_counter() - started_at) * 1000.0
                    db.update_command(
                        cmd["id"],
                        "done",
                        _final_result_message("MT5→DB sync complete", trace_id=trace_id, duration_ms=duration_ms),
                    )
                    logger.info("Manual MT5→DB sync triggered from dashboard")

            else:
                db.update_command(cmd["id"], "failed", f"Unknown command: {cmd_name}")

            duration_ms = (time.perf_counter() - started_at) * 1000.0
            db.log_agent_event(
                "logging",
                "info",
                f"Command completed: {cmd_name}",
                {
                    "command_id": cmd["id"],
                    "command": cmd_name,
                    "trace_id": trace_id,
                    "duration_ms": round(duration_ms, 2),
                },
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - started_at) * 1000.0
            db.update_command(
                cmd["id"],
                "failed",
                _final_result_message(str(exc), trace_id=trace_id, duration_ms=duration_ms),
            )
            db.log_agent_event(
                "logging",
                "error",
                f"Command failed: {cmd_name}",
                {
                    "command_id": cmd["id"],
                    "command": cmd_name,
                    "trace_id": trace_id,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                },
            )


