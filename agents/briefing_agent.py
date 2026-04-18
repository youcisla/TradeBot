"""BriefingAgent — generates a pre-session market brief via Claude."""

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
    """Generate a pre-session brief for *session* using live bot data + Claude."""
    if not settings.ANTHROPIC_API_KEY:
        return "(Claude unavailable: ANTHROPIC_API_KEY not set.)"

    try:
        import anthropic
    except ImportError:
        return "(Claude unavailable: 'anthropic' package not installed.)"

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
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.warning("BriefingAgent: Claude API failed: %s", exc)
        return f"(Briefing generation failed: {exc})"
