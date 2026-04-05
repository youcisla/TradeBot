"""DeepSeek Strategy — LLM-powered signal generator.

On each call it sends the last 20 H1 candles plus computed indicators to
the DeepSeek chat API and parses a structured JSON trade decision.

Fail-safe: any network / parse error returns None (no signal), so the ICT
and SMA strategies still run as fallbacks.

Cache: each symbol is only re-queried after DEEPSEEK_CACHE_MINUTES have
passed, so the 30-symbol loop doesn't hammer the API.
"""

from __future__ import annotations

import json
import logging
import math
import time
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


def _is_mock_value(value: object) -> bool:
    return type(value).__module__.startswith("unittest.mock")


def _as_int(value: object, default: int) -> int:
    if _is_mock_value(value):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float) -> float:
    if _is_mock_value(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candle_volume_sufficient(candles: list, lookback: int = 20, threshold: float = 0.5) -> bool:
    if not candles or len(candles) < 2:
        return False
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    avg = sum(c.volume for c in recent[:-1]) / max(1, len(recent) - 1)
    return avg > 0 and candles[-1].volume >= avg * threshold


# ── Prompt builder ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert forex/commodities/crypto trading analyst.
Given OHLCV candle data and technical indicators, output a trade signal as JSON.
Be conservative — only recommend BUY/SELL when the setup is genuinely high quality.
Otherwise output HOLD.
"""

_DEEP_VERIFY_PROMPT = """\
You are a strict trading risk verifier.
Given a candidate BUY/SELL signal with confidence and levels, decide if it should be approved.
Return JSON only:
{
    "approved": true | false,
    "confidence_adjustment": <float between -0.20 and 0.10>,
    "reasoning": "<short reason under 40 words>"
}
Rules:
- Reject if setup quality is doubtful or levels are inconsistent with trend/regime.
- Use negative confidence adjustment when approved but quality is marginal.
- Keep output compact and deterministic.
"""

# Characters that could be used to inject instructions into the prompt.
_PROMPT_INJECT_CHARS = str.maketrans("", "", "\n\r\x00\x1b")


def _sanitize(value: str, max_len: int = 80) -> str:
    """Strip control characters and truncate to prevent prompt injection."""
    return str(value).translate(_PROMPT_INJECT_CHARS)[:max_len]


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
            f"\nMacro (Crucix): tier={_sanitize(m.risk_tier, 20)}  vix={m.vix:.1f}"
            f"  sentiment={_sanitize(m.osint_sentiment, 20)}  lot_scale={m.lot_scale_factor:.2f}x"
        )

    sma_cross = "ABOVE" if ctx.sma_fast > ctx.sma_slow else "BELOW"

    return f"""\
Symbol: {_sanitize(ctx.symbol, 20)}  Timeframe: H1
Datetime: {ctx.timestamp.strftime('%Y-%m-%d %H:%M')} UTC
Price: {ctx.current_price:.5f}  Bid: {ctx.bid:.5f}  Ask: {ctx.ask:.5f}  Spread: {ctx.spread:.5f}
Session: {_sanitize(ctx.session)}  Day: {_sanitize(ctx.day_of_week)}
Regime: {_sanitize(ctx.regime)}  Trend: {_sanitize(ctx.trend_direction)}
RSI: {ctx.rsi:.1f}  ATR: {ctx.atr:.5f}
SMA_fast({settings.SMA_FAST_PERIOD}): {ctx.sma_fast:.5f}  SMA_slow({settings.SMA_SLOW_PERIOD}): {ctx.sma_slow:.5f}  (fast {sma_cross} slow){macro_line}

Last 20 candles (H1, oldest → newest):
{candle_table}

Respond with ONLY a JSON object — no prose, no markdown:
{{
    "schema_version": "{settings.DEEPSEEK_SCHEMA_VERSION}",
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
        self._cache: dict[str, tuple[float, Optional[Signal], tuple[str, str, str, str]]] = {}
        # symbol → (monotonic_time_of_last_call, signal_or_None, context_signature)
        self._metrics: dict[str, int] = {
            "detect_calls": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "api_failures": 0,
            "parse_failures": 0,
            "schema_failures": 0,
            "validation_failures": 0,
            "below_confidence": 0,
            "holds": 0,
            "accepted": 0,
        }

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
        self._metrics["detect_calls"] += 1
        if not settings.DEEPSEEK_API_KEY:
            logger.debug("DeepSeekStrategy: DEEPSEEK_API_KEY not set — skipping")
            self._maybe_log_metrics()
            return None

        if not context.candles or len(context.candles) < 20:
            self._maybe_log_metrics()
            return None

        # Cache check — avoid hammering the API every 30-second loop
        now_mono = time.monotonic()
        sig = self._cache_signature(context)
        cached_entry = self._cache.get(context.symbol, (0.0, None, ("", "", "", "")))
        if isinstance(cached_entry, tuple) and len(cached_entry) == 3:
            cached_at, cached_signal, cached_sig = cached_entry
        elif isinstance(cached_entry, tuple) and len(cached_entry) == 2:
            # Backward compatibility for old cache layout (ts, signal).
            cached_at, cached_signal = cached_entry
            cached_sig = sig
        else:
            cached_at, cached_signal, cached_sig = (0.0, None, ("", "", "", ""))

        cache_minutes = _as_int(getattr(settings, "DEEPSEEK_CACHE_MINUTES", 30), 30)
        cache_ttl = cache_minutes * 60
        if now_mono - cached_at < cache_ttl and cached_sig == sig:
            self._metrics["cache_hits"] += 1
            logger.debug("DeepSeekStrategy: %s cache hit (%.0fs remaining)",
                         context.symbol, cache_ttl - (now_mono - cached_at))
            self._maybe_log_metrics()
            return cached_signal
        if now_mono - cached_at < cache_ttl and cached_sig != sig:
            logger.debug(
                "DeepSeekStrategy: %s cache bypass (market signature changed)",
                context.symbol,
            )

        client = self._get_client()
        if client is None:
            self._maybe_log_metrics()
            return None

        signal = self._call_api(client, context)
        self._cache[context.symbol] = (now_mono, signal, sig)
        self._maybe_log_metrics()
        return signal

    @staticmethod
    def _cache_signature(ctx: MarketContext) -> tuple[str, str, str, str]:
        latest = _ensure_utc(ctx.candles[-1].timestamp).isoformat()
        return (
            latest,
            _sanitize(ctx.session, 20),
            _sanitize(ctx.regime, 20),
            _sanitize(ctx.trend_direction, 20),
        )

    def _maybe_log_metrics(self) -> None:
        every = max(1, _as_int(getattr(settings, "DEEPSEEK_METRICS_LOG_EVERY", 25), 25))
        calls = self._metrics["detect_calls"]
        if calls % every != 0:
            return
        m = self._metrics
        logger.info(
            "[deepseek-metrics] calls=%d cache_hits=%d api_calls=%d accepted=%d "
            "holds=%d below_conf=%d parse_fail=%d schema_fail=%d validation_fail=%d api_fail=%d",
            m["detect_calls"],
            m["cache_hits"],
            m["api_calls"],
            m["accepted"],
            m["holds"],
            m["below_confidence"],
            m["parse_failures"],
            m["schema_failures"],
            m["validation_failures"],
            m["api_failures"],
        )

    # ── Internal ─────────────────────────────────────────────────────────

    def _call_api(self, client, context: MarketContext) -> Optional[Signal]:
        try:
            self._metrics["api_calls"] += 1
            prompt = _build_prompt(context)
            quick_model = getattr(settings, "DEEPSEEK_QUICK_MODEL", settings.DEEPSEEK_MODEL)
            quick_timeout = _as_float(getattr(settings, "DEEPSEEK_QUICK_TIMEOUT_SECONDS", 10), 10.0)
            response = client.chat.completions.create(
                model=quick_model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,      # low temp for consistent, structured output
                max_tokens=300,
                timeout=quick_timeout,
            )
            raw = response.choices[0].message.content
            signal = self._parse(raw, context)
            if signal is None:
                return None

            # Dual-speed path: quick model proposes, deep model verifies only
            # high-confidence actionable candidates.
            if (
                bool(getattr(settings, "DEEPSEEK_ENABLE_DEEP_VERIFY", True))
                and signal.confidence >= _as_float(
                    getattr(settings, "DEEPSEEK_DEEP_VERIFY_MIN_CONFIDENCE", 0.78),
                    0.78,
                )
            ):
                verified = self._deep_verify(client, context, signal)
                if verified is None:
                    self._metrics["holds"] += 1
                    logger.info(
                        "[deepseek] %s %s rejected by deep verifier",
                        signal.direction,
                        signal.symbol,
                    )
                    return None
                return verified

            return signal

        except Exception as exc:
            self._metrics["api_failures"] += 1
            logger.warning("DeepSeekStrategy: API call failed for %s: %s",
                           context.symbol, exc)
            return None

    def _deep_verify(self, client, ctx: MarketContext, signal: Signal) -> Optional[Signal]:
        try:
            candidate = {
                "symbol": signal.symbol,
                "direction": signal.direction,
                "confidence": signal.confidence,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit_1": signal.take_profit_1,
                "take_profit_2": signal.take_profit_2,
                "take_profit_3": signal.take_profit_3,
                "reasoning": signal.reason,
                "regime": ctx.regime,
                "trend": ctx.trend_direction,
                "rsi": ctx.rsi,
                "atr": ctx.atr,
            }

            response = client.chat.completions.create(
                model=getattr(settings, "DEEPSEEK_DEEP_MODEL", settings.DEEPSEEK_MODEL),
                messages=[
                    {"role": "system", "content": _DEEP_VERIFY_PROMPT},
                    {"role": "user", "content": json.dumps(candidate, ensure_ascii=True)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=180,
                timeout=_as_float(getattr(settings, "DEEPSEEK_DEEP_TIMEOUT_SECONDS", 8), 8.0),
            )
            payload = json.loads(response.choices[0].message.content)
            approved = bool(payload.get("approved", False))
            if not approved:
                return None

            adjustment = float(payload.get("confidence_adjustment", 0.0))
            verifier_reason = str(payload.get("reasoning", "")).strip()
            signal.confidence = max(0.0, min(1.0, signal.confidence + adjustment))
            if verifier_reason:
                signal.reason = f"{signal.reason} | verifier: {verifier_reason}"[:240]
            return signal
        except Exception as exc:
            # Fail-open: if deep verification fails, keep quick candidate.
            logger.warning(
                "DeepSeekStrategy: deep verify failed for %s: %s — keeping quick decision",
                ctx.symbol,
                exc,
            )
            return signal

    def _parse(self, raw: str, ctx: MarketContext) -> Optional[Signal]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._metrics["parse_failures"] += 1
            logger.warning("DeepSeekStrategy: JSON parse error for %s: %s — raw=%r",
                           ctx.symbol, exc, raw[:200])
            return None

        schema_version = str(data.get("schema_version", ""))
        expected_schema = getattr(settings, "DEEPSEEK_SCHEMA_VERSION", "v1")
        if _is_mock_value(expected_schema):
            expected_schema = "v1"
        expected_schema = str(expected_schema)
        if schema_version and schema_version != expected_schema:
            self._metrics["schema_failures"] += 1
            logger.warning(
                "DeepSeekStrategy: %s schema mismatch got=%r expected=%r",
                ctx.symbol,
                schema_version,
                expected_schema,
            )
            return None

        direction = str(data.get("direction", "HOLD")).upper()
        if direction not in ("BUY", "SELL"):
            self._metrics["holds"] += 1
            logger.debug("DeepSeekStrategy: %s normalized to HOLD", ctx.symbol)
            return None

        confidence = float(data.get("confidence", 0.0))
        min_conf = _as_float(getattr(settings, "DEEPSEEK_MIN_CONFIDENCE", 0.65), 0.65)
        if confidence < min_conf:
            self._metrics["below_confidence"] += 1
            logger.debug("DeepSeekStrategy: %s confidence %.2f < threshold %.2f — skip",
                         ctx.symbol, confidence, min_conf)
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
            self._metrics["validation_failures"] += 1
            logger.warning("DeepSeekStrategy: %s missing SL/TP in response — skip", ctx.symbol)
            return None

        valid, reason = self._validate_payload(
            direction=direction,
            entry=entry,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            atr=ctx.atr,
        )
        if not valid:
            self._metrics["validation_failures"] += 1
            logger.warning("DeepSeekStrategy: %s invalid payload — %s", ctx.symbol, reason)
            return None

        rsi         = ctx.rsi or 50.0
        rsi_aligned = (40 <= rsi <= 70) if direction == "BUY" else (30 <= rsi <= 60)

        snap = EntrySnapshot(
            spread=ctx.spread,
            rsi_aligned=rsi_aligned,
            trend_aligned=(ctx.trend_direction == "bullish" and direction == "BUY")
                        or (ctx.trend_direction == "bearish" and direction == "SELL"),
            volume_sufficient=_candle_volume_sufficient(ctx.candles),
            near_news_event=ctx.near_news_event,
            market_condition=ctx.regime,
            session=ctx.session,
            day_of_week=ctx.day_of_week,
        )

        logger.info("[deepseek] %s %s conf=%.0f%% entry=%.5f sl=%.5f | %s",
                    direction, ctx.symbol, confidence * 100, entry, stop_loss,
                    reasoning[:80])

        self._metrics["accepted"] += 1

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

    @staticmethod
    def _on_correct_side(direction: str, entry: float, target: float) -> bool:
        if direction == "BUY":
            return target > entry
        return target < entry

    def _validate_payload(
        self,
        direction: str,
        entry: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        atr: float,
    ) -> tuple[bool, str]:
        values = [entry, stop_loss, tp1, tp2, tp3]
        if any(not math.isfinite(v) for v in values):
            return False, "non-finite numeric value"

        risk = abs(entry - stop_loss)
        if risk <= 0:
            return False, "zero/negative risk distance"

        # Enforce minimum SL distance requested in prompt: >= 2 * ATR.
        if atr > 0 and risk < (2.0 * atr * 0.95):
            return False, f"risk {risk:.5f} too small for ATR {atr:.5f}"

        if not self._on_correct_side(direction, entry, tp1):
            return False, "TP1 on wrong side of entry"
        if not self._on_correct_side(direction, entry, tp2):
            return False, "TP2 on wrong side of entry"
        if not self._on_correct_side(direction, entry, tp3):
            return False, "TP3 on wrong side of entry"

        # Monotonic TP ladder away from entry.
        if direction == "BUY" and not (tp1 < tp2 < tp3):
            return False, "BUY TP ladder is not monotonic"
        if direction == "SELL" and not (tp1 > tp2 > tp3):
            return False, "SELL TP ladder is not monotonic"

        tol = max(
            0.01,
            _as_float(getattr(settings, "DEEPSEEK_R_MULT_TOLERANCE", 0.25), 0.25),
        )
        expected_tp1 = entry + risk if direction == "BUY" else entry - risk
        expected_tp2 = entry + 2 * risk if direction == "BUY" else entry - 2 * risk
        expected_tp3 = entry + 3 * risk if direction == "BUY" else entry - 3 * risk

        for idx, (actual, expected) in enumerate(
            [(tp1, expected_tp1), (tp2, expected_tp2), (tp3, expected_tp3)],
            start=1,
        ):
            rel_err = abs(actual - expected) / risk
            if rel_err > tol:
                return False, f"TP{idx} deviates from {idx}R by {rel_err:.2f}"

        return True, "ok"
