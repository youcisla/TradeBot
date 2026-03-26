"""DeepSeek Strategy — LLM-powered primary signal generator.

Replaces the LSTM NeuralStrategy.  On each call it sends the last 20 H1
candles plus all computed indicators to the DeepSeek chat API and parses
a structured JSON trade decision.

Fail-safe: any network / parse error returns None (no signal), so the ICT
and SMA strategies still run as fallbacks.

Cache: each symbol is only re-queried after DEEPSEEK_CACHE_MINUTES have
passed, so the 30-symbol loop doesn't hammer the API.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


# ── Prompt builder ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert forex/commodities/crypto trading analyst.
Given OHLCV candle data and technical indicators, output a trade signal as JSON.
Be conservative — only recommend BUY/SELL when the setup is genuinely high quality.
Otherwise output HOLD.
"""


def _build_prompt(ctx: MarketContext) -> str:
    """Convert MarketContext into a concise, information-dense prompt."""
    candles = ctx.candles[-20:] if ctx.candles else []

    # Candle table (condensed — no second-level precision needed for H1)
    rows = [f"{'Time':>8}  {'Open':>10}  {'High':>10}  {'Low':>10}  {'Close':>10}  {'Vol':>8}"]
    for c in candles:
        rows.append(
            f"{c.timestamp.strftime('%m-%d %H'):>8}  "
            f"{c.open:>10.5f}  {c.high:>10.5f}  "
            f"{c.low:>10.5f}  {c.close:>10.5f}  "
            f"{c.volume:>8.0f}"
        )
    candle_table = "\n".join(rows)

    macro_line = ""
    if ctx.macro and ctx.macro.crucix_available:
        m = ctx.macro
        macro_line = (
            f"\nMacro (Crucix): tier={m.risk_tier}  vix={m.vix:.1f}"
            f"  sentiment={m.osint_sentiment}  lot_scale={m.lot_scale_factor:.2f}x"
        )

    sma_cross = "ABOVE" if ctx.sma_fast > ctx.sma_slow else "BELOW"

    return f"""\
Symbol: {ctx.symbol}  Timeframe: H1
Datetime: {ctx.timestamp.strftime('%Y-%m-%d %H:%M')} UTC
Price: {ctx.current_price:.5f}  Bid: {ctx.bid:.5f}  Ask: {ctx.ask:.5f}  Spread: {ctx.spread:.5f}
Session: {ctx.session}  Day: {ctx.day_of_week}
Regime: {ctx.regime}  Trend: {ctx.trend_direction}
RSI: {ctx.rsi:.1f}  ATR: {ctx.atr:.5f}
SMA_fast({settings.SMA_FAST_PERIOD}): {ctx.sma_fast:.5f}  SMA_slow({settings.SMA_SLOW_PERIOD}): {ctx.sma_slow:.5f}  (fast {sma_cross} slow){macro_line}

Last 20 candles (H1, oldest → newest):
{candle_table}

Respond with ONLY a JSON object — no prose, no markdown:
{{
  "direction": "BUY" | "SELL" | "HOLD",
  "confidence": <float 0.0–1.0>,
  "stop_loss": <price float>,
  "take_profit_1": <price float — 1R target>,
  "take_profit_2": <price float — 2R target>,
  "take_profit_3": <price float — 3R target>,
  "reasoning": "<max 80 words>"
}}

Rules:
- If no clear high-probability setup → direction must be "HOLD"
- stop_loss: place beyond the nearest significant swing high/low (use ≥2×ATR as minimum distance)
- Take profits: TP1=1R, TP2=2R, TP3=3R from entry where R = |entry - stop_loss|
- confidence 0.75+ = high conviction, 0.60–0.74 = moderate, below 0.60 = prefer HOLD
"""


# ── Strategy class ────────────────────────────────────────────────────────

class DeepSeekStrategy(BaseStrategy):
    """LLM-driven signal generator powered by the DeepSeek chat API."""

    name = "deepseek"

    def __init__(self) -> None:
        self._client = None          # lazy-initialised on first call
        self._cache:  dict[str, tuple[float, Optional[Signal]]] = {}
        # symbol → (monotonic_time_of_last_call, signal_or_None)

    # ── BaseStrategy abstract methods ─────────────────────────────────────
    # DeepSeek derives SL and TPs directly from the LLM response inside
    # detect(), so these are only called by external code that needs them.

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        """Fallback SL: 2×ATR from current price."""
        atr = context.atr or 0.001
        if direction == "BUY":
            return round(context.current_price - 2 * atr, 5)
        return round(context.current_price + 2 * atr, 5)

    def calculate_tps(
        self,
        context: MarketContext,
        entry: float,
        sl: float,
        direction: str,
    ) -> tuple[float, float, float]:
        """Fallback TPs: 1R / 2R / 3R."""
        risk = abs(entry - sl)
        if direction == "BUY":
            return (round(entry + risk, 5),
                    round(entry + 2 * risk, 5),
                    round(entry + 3 * risk, 5))
        return (round(entry - risk, 5),
                round(entry - 2 * risk, 5),
                round(entry - 3 * risk, 5))

    def _get_client(self):
        """Lazy-init the OpenAI-compatible DeepSeek client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url="https://api.deepseek.com",
                )
            except ImportError:
                logger.error("DeepSeekStrategy: 'openai' package not installed — pip install openai")
        return self._client

    # ── BaseStrategy interface ────────────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        if not settings.DEEPSEEK_API_KEY:
            logger.debug("DeepSeekStrategy: DEEPSEEK_API_KEY not set — skipping")
            return None

        if not context.candles or len(context.candles) < 20:
            return None

        # Cache check — avoid hammering the API every 30-second loop
        now_mono = time.monotonic()
        cached_at, cached_signal = self._cache.get(context.symbol, (0.0, None))
        cache_ttl = settings.DEEPSEEK_CACHE_MINUTES * 60
        if now_mono - cached_at < cache_ttl:
            logger.debug("DeepSeekStrategy: %s cache hit (%.0fs remaining)",
                         context.symbol, cache_ttl - (now_mono - cached_at))
            return cached_signal

        client = self._get_client()
        if client is None:
            return None

        signal = self._call_api(client, context)
        self._cache[context.symbol] = (now_mono, signal)
        return signal

    # ── Internal ─────────────────────────────────────────────────────────

    def _call_api(self, client, context: MarketContext) -> Optional[Signal]:
        try:
            prompt = _build_prompt(context)
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,      # low temp for consistent, structured output
                max_tokens=300,
                timeout=15,           # seconds — don't block the loop
            )
            raw = response.choices[0].message.content
            return self._parse(raw, context)

        except Exception as exc:
            logger.warning("DeepSeekStrategy: API call failed for %s: %s",
                           context.symbol, exc)
            return None

    def _parse(self, raw: str, ctx: MarketContext) -> Optional[Signal]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("DeepSeekStrategy: JSON parse error for %s: %s — raw=%r",
                           ctx.symbol, exc, raw[:200])
            return None

        direction = str(data.get("direction", "HOLD")).upper()
        if direction not in ("BUY", "SELL"):
            logger.debug("DeepSeekStrategy: %s → HOLD", ctx.symbol)
            return None

        confidence = float(data.get("confidence", 0.0))
        if confidence < settings.DEEPSEEK_MIN_CONFIDENCE:
            logger.debug("DeepSeekStrategy: %s confidence %.2f < threshold %.2f — skip",
                         ctx.symbol, confidence, settings.DEEPSEEK_MIN_CONFIDENCE)
            return None

        entry      = ctx.current_price
        stop_loss  = float(data.get("stop_loss", 0.0))
        tp1        = float(data.get("take_profit_1", 0.0))
        tp2        = float(data.get("take_profit_2", 0.0))
        tp3        = float(data.get("take_profit_3", 0.0))
        reasoning  = str(data.get("reasoning", ""))

        # Sanity: SL must be on the correct side
        if direction == "BUY" and stop_loss >= entry:
            logger.warning("DeepSeekStrategy: %s BUY but SL %.5f >= entry %.5f — skip",
                           ctx.symbol, stop_loss, entry)
            return None
        if direction == "SELL" and stop_loss <= entry:
            logger.warning("DeepSeekStrategy: %s SELL but SL %.5f <= entry %.5f — skip",
                           ctx.symbol, stop_loss, entry)
            return None
        if stop_loss == 0.0 or tp1 == 0.0:
            logger.warning("DeepSeekStrategy: %s missing SL/TP in response — skip", ctx.symbol)
            return None

        rsi         = ctx.rsi or 50.0
        rsi_aligned = (40 <= rsi <= 70) if direction == "BUY" else (30 <= rsi <= 60)

        snap = EntrySnapshot(
            spread=ctx.spread,
            rsi_aligned=rsi_aligned,
            trend_aligned=(ctx.trend_direction == "bullish" and direction == "BUY")
                        or (ctx.trend_direction == "bearish" and direction == "SELL"),
            volume_sufficient=ctx.volume > 0,
            near_news_event=ctx.near_news_event,
            market_condition=ctx.regime,
            session=ctx.session,
            day_of_week=ctx.day_of_week,
        )

        logger.info("[deepseek] %s %s conf=%.0f%% entry=%.5f sl=%.5f | %s",
                    direction, ctx.symbol, confidence * 100, entry, stop_loss,
                    reasoning[:80])

        return Signal(
            strategy=self.name,
            symbol=ctx.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=confidence,
            timestamp=datetime.now(UTC),
            reason=reasoning,
            entry_snapshot=snap,
        )
