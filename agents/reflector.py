"""Post-trade Reflector — generates structured lessons from closed trade outcomes.

Adapted from the TradingAgents (youcisla/TradingAgents) Reflector pattern.

After each trade closes the Reflector:
1.  Builds a *situation summary* — all context that existed when the signal
    was generated (symbol, session, regime, MTF bias, indicators, etc.).
2.  Builds a *decision summary* — what each agent decided and why.
3.  Calls the DeepSeek API (same client already used by DeepSeekStrategy)
    with a structured reflection prompt.
4.  Stores the resulting lesson in each relevant agent's ``AgentMemory``.

The memories are then recalled at the *next* decision for similar market
conditions, giving every agent a lightweight form of online learning without
any neural-network retraining.

Agents with memory
------------------
``neural``   — LSTM direction + confidence call
``council``  — Council vote (ICT / DanialFX / Traditional / World weights)
``risk``     — Risk agent accept/reject + sizing decision
``learning`` — Meta-learning: overall bot improvement notes
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from config import settings
from utils.memory import AgentMemory

if TYPE_CHECKING:
    from models.trade import Trade

logger = logging.getLogger(__name__)

# ── Memory directory (persisted across restarts) ──────────────────────────

_MEMORY_DIR = Path(__file__).resolve().parent.parent / "models" / "memories"

# ── Reflection system prompt (adapted from TradingAgents) ────────────────

_SYSTEM_PROMPT = """\
You are an expert trading analyst reviewing a completed forex/commodity trade.
Your task is to deliver a concise, actionable post-trade analysis that improves
future decision-making.

Follow these steps:

1. VERDICT — Was the trade decision correct? (Correct = closed profitably via TP;
   Incorrect = stopped out or closed at a loss.)

2. CONTRIBUTING FACTORS — Analyse which factors drove the outcome:
   - LSTM direction confidence and feature quality
   - Multi-timeframe alignment (M30/H1/H4/D1 agreement)
   - Market regime (trending/ranging/volatile) at entry
   - Session and day-of-week liquidity profile
   - Council consensus and dissenting voices
   - RSI, ATR, spread conditions at entry
   - Macro / news environment (if available)

3. LESSON — One to three concise, actionable sentences explaining what the bot
   should do differently in a similar future situation.
   Examples:
   - "In a ranging regime with H4 counter-trend, reduce lot size by 50% and
     target TP1 only."
   - "When D1 trend contradicts H1 signal during NFP week, skip entirely."

4. QUERY — Compress the lesson into a single sentence (≤ 100 words) that can be
   stored as a memory key for future BM25 retrieval.

Keep the total response under 400 words. Be direct and specific — avoid generic
advice. Focus on the exact conditions present in this trade.\
"""


def _build_situation(trade: "Trade", context: dict | None) -> str:
    """Construct a rich situation string from the closed trade + stored context."""
    ctx = context or {}
    parts = [
        f"Symbol: {trade.symbol}",
        f"Direction: {trade.direction}",
        f"Strategy: {trade.strategy}",
        f"Session: {ctx.get('session') or trade.snap_session or 'unknown'}",
        f"Regime: {ctx.get('regime', 'unknown')}",
        f"MTF bias: {ctx.get('mtf_bias', 'unknown')} alignment={ctx.get('mtf_alignment', 0):.0%}",
        f"D1 trend: {ctx.get('d1_trend', 'neutral')}  H4: {ctx.get('h4_trend', 'neutral')}  M30: {ctx.get('m30_trend', 'neutral')}",
        f"RSI: {ctx.get('rsi', 50):.1f}  ATR: {ctx.get('atr', 0):.5f}  ADX: {ctx.get('adx', 0):.1f}",
        f"Spread at entry: {trade.spread_at_entry:.5f}",
        f"Day of week: {ctx.get('day_of_week') or trade.snap_day_of_week or 'unknown'}",
        f"Near news event: {trade.snap_near_news_event}",
        f"RSI aligned: {trade.snap_rsi_aligned}  Trend aligned: {trade.snap_trend_aligned}",
    ]
    if ctx.get("macro_tier"):
        parts.append(f"Macro risk tier: {ctx['macro_tier']}")
    return "\n".join(parts)


def _build_decision(trade: "Trade", context: dict | None) -> str:
    """Summarise what each agent decided for this trade."""
    ctx = context or {}
    lines = [
        f"LSTM signal: {trade.direction} confidence={ctx.get('confidence', '?')}",
        f"Council vote: {ctx.get('council_vote', 'not recorded')}",
        f"Risk agent: PASSED (lot_size={trade.lot_size:.4f})",
        f"Entry: {trade.entry_price:.5f}  SL: {trade.stop_loss:.5f}",
        f"Trade outcome: {trade.close_reason}  PnL: {trade.pnl:+.2f}",
        f"TP1 hit: {trade.tp1_hit}  TP2 hit: {trade.tp2_hit}  TP3 hit: {trade.tp3_hit}",
    ]
    return "\n".join(lines)


class Reflector:
    """Generates post-trade lessons and stores them in per-agent BM25 memories.

    All DeepSeek API calls run in a background thread — the main bot loop is
    never blocked.
    """

    # One memory store per agent role
    AGENT_ROLES = ("neural", "council", "risk", "learning")

    def __init__(self) -> None:
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.memories: dict[str, AgentMemory] = {
            role: AgentMemory(
                name=role,
                persist_path=_MEMORY_DIR / f"{role}_memory.json",
            )
            for role in self.AGENT_ROLES
        }
        self._client = None   # lazy-initialised

    # ── public API ───────────────────────────────────────────────────────

    def reflect_async(self, trade: "Trade", context: dict | None = None) -> None:
        """Trigger reflection in a background thread (non-blocking)."""
        thread = threading.Thread(
            target=self._reflect,
            args=(trade, context),
            daemon=True,
            name=f"reflector-{trade.id[:8]}",
        )
        thread.start()

    def recall(self, role: str, situation: str, n: int = 2) -> list[dict]:
        """Retrieve the top-n most relevant memories for ``role``."""
        mem = self.memories.get(role)
        return mem.recall(situation, n=n) if mem else []

    def recall_as_text(self, role: str, situation: str, n: int = 2) -> str:
        """Return recalled memories formatted as an injectable context string."""
        hits = self.recall(role, situation, n=n)
        if not hits:
            return ""
        lines = [f"[Past lesson {i + 1} (similarity={h['score']:.2f})]:\n{h['lesson']}"
                 for i, h in enumerate(hits)]
        return "\n\n".join(lines)

    def memory_sizes(self) -> dict[str, int]:
        return {role: mem.size() for role, mem in self.memories.items()}

    # ── internals ────────────────────────────────────────────────────────

    def _reflect(self, trade: "Trade", context: dict | None) -> None:
        """Synchronous reflection — runs in background thread."""
        client = self._get_client()
        if client is None:
            return

        situation = _build_situation(trade, context)
        decision  = _build_decision(trade, context)

        prompt = (
            f"MARKET SITUATION AT ENTRY:\n{situation}\n\n"
            f"AGENT DECISIONS:\n{decision}"
        )

        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            lesson = message.content[0].text.strip()
        except Exception as exc:
            logger.warning("Reflector: Anthropic API failed for trade %s: %s", trade.id, exc)
            # Fall back to a structured rule-based lesson so memory still grows
            lesson = self._fallback_lesson(trade)

        # Store in all agent memories — each agent benefits from the same lesson
        for role, mem in self.memories.items():
            mem.add(situation, lesson)

        logger.info(
            "Reflector: lesson stored for trade %s (%s %s %+.2f) — memories: %s",
            trade.id, trade.direction, trade.symbol, trade.pnl or 0.0,
            {r: m.size() for r, m in self.memories.items()},
        )

        # Push a summary to Telegram (non-blocking — we're already in a daemon thread)
        try:
            from utils.telegram_bot import send_message
            verdict_line = lesson.split("\n")[0]          # first line = VERDICT
            pnl_sign = "✅" if (trade.pnl or 0) > 0 else "❌"
            send_message(
                f"{pnl_sign} *Trade closed* — {trade.direction} {trade.symbol} "
                f"({trade.pnl:+.2f})\n\n{verdict_line}",
                priority="normal",
                dedupe_key=f"reflect:{trade.id}",
            )
        except Exception as exc:
            logger.debug("Reflector: Telegram delivery failed: %s", exc)

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not settings.ANTHROPIC_API_KEY:
            logger.debug("Reflector: ANTHROPIC_API_KEY not set — skipping LLM reflection")
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except ImportError:
            logger.error("Reflector: 'anthropic' package not installed")
        return self._client

    @staticmethod
    def _fallback_lesson(trade: "Trade") -> str:
        """Rule-based lesson when the API is unavailable."""
        outcome = "profitable" if (trade.pnl or 0) > 0 else "a loss"
        tp_level = ("TP3" if trade.tp3_hit else
                    "TP2" if trade.tp2_hit else
                    "TP1" if trade.tp1_hit else "none")
        return (
            f"Trade {trade.direction} {trade.symbol} closed at {trade.close_reason} "
            f"({outcome}, P&L={trade.pnl:+.2f}, highest TP={tp_level}). "
            f"Session={trade.snap_session} regime={trade.snap_market_condition}. "
            f"RSI_aligned={trade.snap_rsi_aligned} trend_aligned={trade.snap_trend_aligned}."
        )
