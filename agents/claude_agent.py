"""ClaudeAgent — answers operator queries using MCP tool data (DeepSeek)."""

import json
import logging

from config import settings
from tools.mcp_server import (
    _read_heartbeat,
    _tail_event_log,
    _open_trades_summary,
    _get_macro_snapshot,
)

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are the operator assistant for TradeBot, an ICT-strategy MT5 trading bot.
Answer in plain English — no markdown, no bullet symbols (Telegram renders these poorly).
Be concise: 3-5 sentences max unless asked for detail.
Always ground your answer in the live data from tools; never invent numbers.\
"""

_FUNCTIONS = [
    {
        "name": "bot_status",
        "description": "Return bot heartbeat: uptime, last-seen agents, iteration count.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "open_trades",
        "description": "Return all currently open broker positions.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "agent_feed",
        "description": "Return the last N events from the bot event log.",
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Number of events (default 20)"}},
            "required": [],
        },
    },
    {
        "name": "macro_snapshot",
        "description": "Return the latest macro environment data (VIX, DXY, FRED).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "pause_bot",
        "description": "Pause new trade entries. Does NOT close open positions.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "resume_bot",
        "description": "Resume normal trade entry after a pause.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

_FUNCTION_MAP = {
    "bot_status":     lambda _: _read_heartbeat(),
    "open_trades":    lambda _: _open_trades_summary(),
    "agent_feed":     lambda inp: _tail_event_log(int(inp.get("n", 20))),
    "macro_snapshot": lambda _: _get_macro_snapshot(),
    "pause_bot":      lambda _: {"_pending": True, "action": "pause_bot",
                                  "_warning": "⚠️ About to PAUSE the bot. Reply /confirm to proceed."},
    "resume_bot":     lambda _: {"_pending": True, "action": "resume_bot",
                                  "_warning": "⚠️ About to RESUME the bot. Reply /confirm to proceed."},
}


def answer(user_message: str) -> tuple[str, dict | None] | str:
    """Run a single-turn agentic loop: DeepSeek -> function calls -> final reply.

    Returns:
        str — plain reply (read query)
        tuple[str, dict] — reply text and pending action to confirm (write query)
    """
    if not settings.DEEPSEEK_API_KEY:
        return "DeepSeek agent unavailable: DEEPSEEK_API_KEY not set.", None

    try:
        from openai import OpenAI
    except ImportError:
        return "DeepSeek agent unavailable: 'openai' package not installed.", None

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):   # max 5 function-call rounds
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            tools=[{"type": "function", "function": f} for f in _FUNCTIONS],
            tool_choice="auto",
            max_tokens=600,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if msg.function_call is None:
            return msg.content or "(no text response)", None

        # Process function_call blocks
        tool_results = []
        pending: dict | None = None
        fc = msg.function_call
        fn = _FUNCTION_MAP.get(fc.name)
        if fn:
            args = json.loads(fc.arguments) if isinstance(fc.arguments, str) else fc.arguments
            result_dict = fn(args)
        else:
            result_dict = {"error": f"unknown function: {fc.name}"}

        if isinstance(result_dict, dict) and result_dict.get("_pending"):
            pending = result_dict
            result_text = result_dict.get("_warning", "⚠️ Confirm this action.")
        else:
            result_text = json.dumps(result_dict)

        tool_results.append({
            "role": "tool",
            "tool_call_id": fc.id,
            "name": fc.name,
            "content": result_text,
        })
        messages.append(tool_results[0])

        if pending:
            warning = pending.get("_warning", "⚠️ Confirm this action.")
            return warning, pending

    return "Sorry, I couldn't complete that query.", None
