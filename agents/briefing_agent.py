"""BriefingAgent — generates a pre-session market brief via DeepSeek."""

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
You are a concise trading intelligence briefing system.
Write exactly 5 sentences. No markdown. No bullet points.
Cover: (1) current macro risk environment, (2) open position exposure,
(3) any anomalies in the last 30 bot events, (4) session bias recommendation,
(5) one specific risk to watch for this session.\
"""


def generate_brief(session: str) -> str:
    """Generate a pre-session brief for *session* using live bot data + DeepSeek."""
    if not settings.DEEPSEEK_API_KEY:
        return "(DeepSeek unavailable: DEEPSEEK_API_KEY not set.)"

    try:
        from openai import OpenAI
    except ImportError:
        return "(DeepSeek unavailable: 'openai' package not installed.)"

    context = {
        "session": session,
        "heartbeat": _read_heartbeat(),
        "open_trades": _open_trades_summary(),
        "macro": _get_macro_snapshot(),
        "recent_events": _tail_event_log(30),
    }
    prompt = (
        f"Pre-{session.upper()} session brief. "
        f"Bot context:\n{json.dumps(context, default=str, indent=2)}"
    )

    try:
        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("BriefingAgent: DeepSeek API failed: %s", exc)
        return f"(Briefing generation failed: {exc})"
