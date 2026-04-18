"""ClaudeAgent — answers operator queries using MCP tool data."""

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

_TOOLS = [
    {
        "name": "bot_status",
        "description": "Return bot heartbeat: uptime, last-seen agents, iteration count.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "open_trades",
        "description": "Return all currently open broker positions.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "agent_feed",
        "description": "Return the last N events from the bot event log.",
        "input_schema": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Number of events (default 20)"}},
            "required": [],
        },
    },
    {
        "name": "macro_snapshot",
        "description": "Return the latest macro environment data (VIX, DXY, FRED).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "pause_bot",
        "description": "Pause new trade entries. Does NOT close open positions.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "resume_bot",
        "description": "Resume normal trade entry after a pause.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

_TOOL_DISPATCH = {
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
    """Run a single-turn agentic loop: Claude -> tool calls -> final reply.

    Returns:
        str — plain reply (read query)
        tuple[str, dict] — reply text and pending action to confirm (write query)
    """
    if not settings.ANTHROPIC_API_KEY:
        return "Claude agent unavailable: ANTHROPIC_API_KEY not set.", None

    try:
        import anthropic
    except ImportError:
        return "Claude agent unavailable: 'anthropic' package not installed.", None

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):   # max 5 tool-call rounds
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extract final text block
            for block in response.content:
                if block.type == "text":
                    return block.text, None
            return "(no text response)", None

        # Process tool_use blocks
        tool_results = []
        pending: dict | None = None
        for block in response.content:
            if block.type == "tool_use":
                fn = _TOOL_DISPATCH.get(block.name)
                result_dict = fn(block.input) if fn else {"error": "unknown tool"}
                if isinstance(result_dict, dict) and result_dict.get("_pending"):
                    pending = result_dict
                    result_text = result_dict.get("_warning", "⚠️ Confirm this action.")
                else:
                    result_text = json.dumps(result_dict)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

        if pending:
            # Return the warning as the reply; caller queues the pending action
            warning = pending.get("_warning", "⚠️ Confirm this action.")
            return warning, pending

    return "Sorry, I couldn't complete that query.", None
