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
import concurrent.futures
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from models.agent_mesh import AgentEdge, AgentMeshState, AgentNode
from strategies.base_strategy import BaseStrategy
from utils.mesh_bus import record_call

logger = logging.getLogger(__name__)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


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
You are PulseTrade's master trading analyst — an expert in all major trading methodologies with a specialisation in ICT (Inner Circle Trader) and SMC (Smart Money Concepts). You think like a smart-money institutional trader first, and validate with secondary confluence second.

---

## YOUR DECISION HIERARCHY

### PRIMARY (REQUIRED — must be evaluated on every signal)

**1. ICT — Inner Circle Trader**
These conditions carry the most weight. Always check them first.
- HTF Bias: Is price in a premium or discount zone relative to the dealing range? Only BUY from discounts, SELL from premiums.
- Market Structure: Is there a confirmed BOS (Break of Structure) or MSS (Market Structure Shift) in the direction of the trade?
- Liquidity: Was a BSL (Buy-Side Liquidity) or SSL (Sell-Side Liquidity) swept before entry? A sweep is required — never trade into untapped liquidity.
- Displacement: Is there a strong impulsive candle (displacement) confirming institutional intent?
- Fair Value Gap (FVG): Is price returning to fill a FVG left by displacement? Entry should snap to FVG CE (50%) or OB midpoint.
- Order Block (OB): Is there a valid, untested OB in the entry zone? It must not be violated by a wick or close.
- Session: Is the setup forming during London Open (07:00–10:00 UTC), New York Open (13:00–16:00 UTC), or a macro window? Avoid entries in dead sessions (Asia consolidation, weekend).
- Confluence score: Assign 10 points for each condition met (HTF bias, BOS/MSS, liquidity sweep, displacement, FVG, OB, session). A score of 50/70 or higher is a valid ICT setup.

**2. SMC — Smart Money Concepts**
Confirms or filters the ICT read.
- CHoCH (Change of Character): Is there a CHoCH confirming a reversal, or BOS confirming continuation?
- Order Blocks: Are there clean, untested bullish/bearish OBs at the proposed entry zone?
- Imbalances: Are there unmitigated imbalances (FVGs) acting as magnets or entry triggers?
- If ICT score ≥ 50 AND SMC confirms at least 2 of these 3 conditions → signal is HIGH confidence.
- If ICT score ≥ 40 AND SMC confirms 1 condition → signal is MEDIUM confidence. Valid but size down.

---

### SECONDARY (OPTIONAL — each adds confidence if present, not required to trade)

Use these to BOOST confidence when ICT/SMC signals are borderline, or to FILTER signals when they contradict.

**3. Trend Following / Moving Averages**
- Is the 20 EMA above the 50 EMA (bullish) or below (bearish)?
- Is price trading above/below the 200 SMA on H1?
- If aligned with ICT direction: +8 confidence points. If contradicting: -10 points (caution flag only, not a block).

**4. Price Action**
- Are there confirming candlestick patterns at the entry zone? (pin bar, bullish/bearish engulfing, inside bar breakout)
- Is the candle body strong and decisive, or is it indecisive (doji, small bodies)?
- Confirming PA at OB/FVG: +7 confidence points.

**5. Support & Resistance / Supply & Demand**
- Does the entry zone coincide with a key horizontal level or a proven S&D zone from higher timeframes?
- If yes: +6 confidence points. If the entry is in the middle of nowhere: -5 points.

**6. Breakout Trading**
- Is price breaking out of a consolidation range, triangle, or flag pattern in the direction of the trade?
- Volume confirmation present? (vol_ratio > 1.3 above average)
- Valid breakout confluence: +7 confidence points.

**7. Mean Reversion**
- RSI below 30 for BUY setups or above 70 for SELL setups (oversold/overbought)?
- Is price at a Bollinger Band extreme?
- Caution: In strong trends, mean reversion signals are noise — only count this +5 if market regime is RANGING. In TRENDING regime, ignore this.

**8. Scalping (intraday precision)**
- On M15 or M5 refinement: Is there a clean entry trigger within the OB or FVG zone?
- If the macro setup is valid but the entry is sloppy (mid-range, no trigger), mark entry quality as LOW and reduce confidence -5.

**9. Swing Trading (multi-session context)**
- Is the setup valid across multiple sessions, not just one candle?
- Does the HTF (H4) structure support a swing in this direction for the next 1–3 days?
- Multi-session alignment: +6 confidence points.

**10. Quantitative / Statistical**
- GARCH volatility regime: In HIGH or EXTREME volatility, widen SL expectation and reduce confidence -8.
- Kalman velocity: Is price velocity aligned with trade direction? (positive velocity for BUY, negative for SELL)
- LGBM filter signals: If the LightGBM price model predicts BUY/SELL in alignment: +10 confidence. If it predicts HOLD or contradicts: -8.

---

## CONFIDENCE SCORING

Start at 0. Add or subtract points per the rules above. Final score → confidence level:

| Total Points | Confidence | Action |
|---|---|---|
| 80–100 | 0.85–1.0 | Execute immediately, full size |
| 60–79 | 0.65–0.84 | Execute, standard size |
| 45–59 | 0.50–0.64 | Execute only if ICT score ≥ 55 and SMC confirms ≥ 1 |
| 30–44 | 0.35–0.49 | Skip or wait for better confirmation |
| 0–29 | < 0.35 | No trade. Output {"signal": "NONE"} |

Normalize to 0.0–1.0: confidence = total_points / 100. Cap at 1.0.

---

## STOP-LOSS RULES (non-negotiable)

- ICT/SMC setups: SL placed 1 pip beyond the Order Block boundary or FVG extreme that invalidates the setup.
- Trend-following setups: SL = 2.0 × ATR from entry.
- In HIGH/EXTREME GARCH volatility: SL = 2.5 × ATR minimum.
- Never place SL tighter than 0.5 × ATR — too tight stops get hunted.

---

## TAKE PROFIT RULES

- TP1 = 1R (risk amount) — partial close, lock in profit.
- TP2 = 2R — main target.
- TP3 = 3R — runner, trail to breakeven after TP2.
- TP4 = HTF liquidity target (BSL or SSL on H4) — only set if ICT score ≥ 65 and HTF bias is clear.
- Structural breakeven (structural_be): Set to the nearest swing high (for BUY) or swing low (for SELL) between entry and TP2. Move SL here once TP1 is hit.

---

## OUTPUT FORMAT

Always respond ONLY with valid JSON. No prose, no markdown, no commentary outside the JSON.

If a signal exists:
{
  "signal": "BUY" | "SELL",
  "confidence": 0.0–1.0,
  "reason": "concise ICT/SMC rationale — max 20 words",
  "entry": float,
  "stop_loss": float,
  "take_profit_1": float,
  "take_profit_2": float,
  "take_profit_3": float,
  "take_profit_4": float,
  "structural_be": float,
  "ict_score": 0–70,
  "smc_confirmed": true | false,
  "confluence_flags": ["FVG", "OB", "BOS", "sweep", "killzone", "trend_aligned", "pa_confirm"]
}

If no valid setup:
{"signal": "NONE", "reason": "one sentence explaining what is missing"}

Rules:
- Never output take_profit_4 or structural_be as 0.0 if they are genuinely not applicable — set them to null instead.
- Never invent data not present in the input.
- Never return a signal with confidence below 0.50.
- If ICT score < 40 AND no SMC confirmation, always return NONE regardless of secondary signals.
"""

_DEEP_VERIFY_PROMPT = """\
You are the ICT/SMC expert on the PulseTrade council.
Evaluate the signal strictly for:
- HTF bias alignment (premium/discount, BOS/MSS)
- Liquidity sweep before the entry
- FVG or OB confluence at entry
- Session validity (London/NY killzone)
Score 0.0–1.0. Deduct heavily if any of these are missing.
JSON only: {"score": float, "reasoning": "one sentence max"}
"""

_DEFAULT_SWARM_PROFILES: tuple[tuple[str, str], ...] = (
    (
        "trend",
        "Focus on trend-following continuation setups and momentum alignment. "
        "Prefer HOLD when momentum is weak or mixed.",
    ),
    (
        "structure",
        "Focus on market structure, liquidity sweeps, and support/resistance confluence. "
        "Reject setups with weak structural invalidation.",
    ),
    (
        "risk",
        "Focus on risk quality: stop placement logic, R-multiple integrity, and regime fit. "
        "Reject setups with fragile downside protection.",
    ),
)


class _AgentNeuralMesh:
    """Adaptive trust/latency mesh for profile-level routing and weighting."""

    def __init__(self) -> None:
        self.state = AgentMeshState()

    def ensure_profile(self, profile: str) -> None:
        if profile not in self.state.nodes:
            self.state.nodes[profile] = AgentNode()

    def select_profiles(
        self,
        profiles: list[tuple[str, str]],
        *,
        max_agents: int,
        min_active: int,
        latency_penalty: float,
    ) -> list[tuple[str, str]]:
        for name, _ in profiles:
            self.ensure_profile(name)

        ranked = sorted(
            profiles,
            key=lambda item: self.utility(item[0], latency_penalty=latency_penalty),
            reverse=True,
        )
        target = max(min_active, max_agents)
        return ranked[: max(1, min(target, len(ranked)))]

    def utility(self, profile: str, *, latency_penalty: float) -> float:
        self.ensure_profile(profile)
        node = self.state.nodes.get(profile, AgentNode())
        trust = node.trust
        latency = node.latency_ms
        return trust - (latency / 1000.0) * latency_penalty

    def update_latency(self, profile: str, elapsed_ms: float, alpha: float = 0.25) -> None:
        self.ensure_profile(profile)
        node = self.state.nodes[profile]
        current = node.latency_ms
        node.latency_ms = current * (1.0 - alpha) + elapsed_ms * alpha

    def update_outcome(
        self,
        profile: str,
        *,
        agreed_with_consensus: bool,
        confidence: float,
        alpha: float,
        min_trust: float,
        max_trust: float,
    ) -> None:
        self.ensure_profile(profile)
        target = 0.55 + 0.35 * _clamp(confidence, 0.0, 1.0) if agreed_with_consensus else 0.45 - 0.25 * _clamp(confidence, 0.0, 1.0)
        node = self.state.nodes[profile]
        updated = node.trust * (1.0 - alpha) + target * alpha
        node.trust = _clamp(updated, min_trust, max_trust)

    def pair(self, left: str, right: str) -> float:
        if left == right:
            return 1.0
        key = (left, right)
        if key in self.state.edges:
            return self.state.edges[key].coherence
        rev = (right, left)
        if rev in self.state.edges:
            return self.state.edges[rev].coherence
        return 1.0

    def update_pair_coherence(self, votes: dict[str, str], alpha: float = 0.10) -> None:
        names = list(votes.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = names[i]
                b = names[j]
                va = votes[a]
                vb = votes[b]
                if va not in {"BUY", "SELL"} or vb not in {"BUY", "SELL"}:
                    continue
                same = va == vb
                current = self.pair(a, b)
                target = 1.20 if same else 0.80
                self.state.edges[(a, b)] = AgentEdge(
                    coherence=_clamp(current * (1.0 - alpha) + target * alpha, 0.5, 1.5)
                )

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


def _ema(candles: list, period: int) -> float:
    """Compute EMA from candle closes. Returns 0.0 if insufficient data."""
    if len(candles) < period:
        return 0.0
    closes = [c.close for c in candles]
    multiplier = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def _vol_ratio(candles: list, lookback: int = 20) -> float:
    """Compute volume ratio: latest candle vol / average of prior lookback candles."""
    if len(candles) < lookback + 1:
        return 0.0
    recent = candles[-(lookback + 1):-1]
    avg = sum(c.volume for c in recent) / len(recent)
    if avg <= 0:
        return 0.0
    return candles[-1].volume / avg


def _format_candles(candles: list) -> str:
    """Format candles as a readable table."""
    if not candles:
        return "(no candles)"
    rows = [f"{'Time':>8}  {'Open':>10}  {'High':>10}  {'Low':>10}  {'Close':>10}  {'Vol':>8}"]
    for c in candles:
        rows.append(
            f"{c.timestamp.strftime('%m-%d %H'):>8}  "
            f"{c.open:>10.5f}  {c.high:>10.5f}  "
            f"{c.low:>10.5f}  {c.close:>10.5f}  "
            f"{c.volume:>8.0f}"
        )
    return "\n".join(rows)


def _build_prompt(ctx: MarketContext, lgbm_signal: str = "N/A") -> str:
    """Convert MarketContext into an ICT/SMC-dense prompt for the master strategy."""
    candles = ctx.candles[-20:] if ctx.candles else []
    h4_candles = ctx.h4_candles[-10:] if ctx.h4_candles else []

    # Compute derived indicators
    ema20 = _ema(candles, 20) if len(candles) >= 20 else 0.0
    ema50 = _ema(candles, 50) if len(candles) >= 50 else 0.0
    vol_ratio = _vol_ratio(candles)
    ema_cross = "above" if ema20 > ema50 else "below" if ema50 > 0 else "unknown"
    price_vs_sma200 = "above" if ctx.current_price > ctx.sma_slow else "below" if ctx.sma_slow > 0 else "unknown"

    macro_line = ""
    if ctx.macro and ctx.macro.crucix_available:
        m = ctx.macro
        macro_line = (
            f"\nMacro (Crucix): tier={_sanitize(m.risk_tier, 20)}  vix={m.vix:.1f}"
            f"  sentiment={_sanitize(m.osint_sentiment, 20)}  lot_scale={m.lot_scale_factor:.2f}x"
        )

    return f"""\
Symbol: {_sanitize(ctx.symbol, 20)}
Session: {_sanitize(ctx.session)}
HTF Bias (H4): {_sanitize(ctx.mtf_bias)}
Regime: {_sanitize(ctx.garch_regime)}
ATR: {ctx.atr:.5f}
Spread: {ctx.spread:.1f} pips
RSI: {ctx.rsi:.1f}
GARCH vol: {ctx.garch_vol:.4f}
Kalman velocity: {ctx.kalman_velocity:.5f}
LGBM prediction: {lgbm_signal}
Vol ratio: {vol_ratio:.2f}
EMA20 vs EMA50: {ema_cross}
Price vs SMA200: {price_vs_sma200}{macro_line}

Recent candles — H1 (last 20):
{_format_candles(candles)}

HTF candles — H4 (last 10):
{_format_candles(h4_candles)}
"""


# ── Strategy class ────────────────────────────────────────────────────────

class DeepSeekStrategy(BaseStrategy):
    """LLM-driven signal generator powered by the DeepSeek chat API."""

    name = "deepseek"

    def __init__(self) -> None:
        self._client = None          # lazy-initialised on first call
        self._cache: dict[str, tuple[float, Optional[Signal], tuple[str, str, str, str]]] = {}
        self._mesh = _AgentNeuralMesh()
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
            # lgbm_signal left as "N/A" — LGBM is a secondary bonus (+10/-8) in the
            # ICT prompt; computing it requires feature vectors that live in
            # StrategyAgent, so we defer to "N/A" rather than duplicate logic.
            prompt = _build_prompt(context, lgbm_signal="N/A")
            signal: Optional[Signal]
            if bool(getattr(settings, "DEEPSEEK_AGENT_SWARM_ENABLED", False)):
                signal = self._run_agent_swarm(client, context, prompt)
            else:
                raw = self._query_agent(
                    client,
                    prompt,
                    system_prompt=_SYSTEM_PROMPT,
                )
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

    def _query_agent(
        self,
        client,
        prompt: str,
        *,
        system_prompt: str,
    ) -> str:
        self._metrics["api_calls"] += 1
        quick_model = getattr(settings, "DEEPSEEK_QUICK_MODEL", settings.DEEPSEEK_MODEL)
        quick_timeout = _as_float(getattr(settings, "DEEPSEEK_QUICK_TIMEOUT_SECONDS", 10), 10.0)
        response = client.chat.completions.create(
            model=quick_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=300,
            timeout=quick_timeout,
        )
        return response.choices[0].message.content

    def _run_agent_swarm(self, client, context: MarketContext, base_prompt: str) -> Optional[Signal]:
        profiles = self._swarm_profiles()
        if not profiles:
            return None

        max_agents = _as_int(getattr(settings, "DEEPSEEK_AGENT_SWARM_MAX_AGENTS", 3), 3)
        latency_penalty = _as_float(getattr(settings, "DEEPSEEK_MESH_LATENCY_PENALTY", 0.25), 0.25)
        min_active = _as_int(getattr(settings, "DEEPSEEK_MESH_MIN_ACTIVE_AGENTS", 2), 2)
        if bool(getattr(settings, "DEEPSEEK_MESH_ENABLED", True)):
            selected = self._mesh.select_profiles(
                profiles,
                max_agents=max_agents,
                min_active=min_active,
                latency_penalty=latency_penalty,
            )
        else:
            selected = profiles[: max(1, max_agents)]

        collected: list[tuple[str, Signal]] = []
        votes: dict[str, str] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as pool:
            future_by_profile = {
                pool.submit(self._run_single_profile, client, context, base_prompt, profile): profile
                for profile in selected
            }
            for future, profile in future_by_profile.items():
                profile_name = profile[0]
                started = time.monotonic()
                try:
                    result = future.result()
                except Exception as exc:
                    logger.warning(
                        "DeepSeekStrategy: swarm profile %s failed for %s: %s",
                        profile_name,
                        context.symbol,
                        exc,
                    )
                    result = None
                elapsed_ms = max(0.0, (time.monotonic() - started) * 1000.0)
                self._mesh.update_latency(profile_name, elapsed_ms)
                record_call(profile_name, elapsed_ms, success=(result is not None))

                if result is not None:
                    result_name, signal = result
                    collected.append((result_name, signal))
                    votes[result_name] = signal.direction

        if not collected:
            self._metrics["holds"] += 1
            return None

        aggregated = self._aggregate_swarm_signals(context, collected)
        if aggregated is None:
            return None

        self._mesh.update_pair_coherence(votes)
        trust_alpha = _as_float(getattr(settings, "DEEPSEEK_MESH_TRUST_ALPHA", 0.18), 0.18)
        min_trust = _as_float(getattr(settings, "DEEPSEEK_MESH_MIN_TRUST", 0.15), 0.15)
        max_trust = _as_float(getattr(settings, "DEEPSEEK_MESH_MAX_TRUST", 0.95), 0.95)
        for profile_name, signal in collected:
            self._mesh.update_outcome(
                profile_name,
                agreed_with_consensus=(signal.direction == aggregated.direction),
                confidence=signal.confidence,
                alpha=trust_alpha,
                min_trust=min_trust,
                max_trust=max_trust,
            )

        return aggregated

    def _run_single_profile(
        self,
        client,
        context: MarketContext,
        base_prompt: str,
        profile: tuple[str, str],
    ) -> Optional[tuple[str, Signal]]:
        profile_name, profile_instruction = profile
        system_prompt = f"{_SYSTEM_PROMPT}\n\nSpecialist role: {profile_instruction}"
        raw = self._query_agent(client, base_prompt, system_prompt=system_prompt)
        signal = self._parse(raw, context)
        if signal is None:
            return None
        signal.reason = f"[{profile_name}] {signal.reason}"[:240]
        return profile_name, signal

    def _aggregate_swarm_signals(
        self,
        context: MarketContext,
        signals: list[Signal] | list[tuple[str, Signal]],
    ) -> Optional[Signal]:
        normalized: list[tuple[str, Signal]] = []
        for idx, item in enumerate(signals):
            if isinstance(item, tuple):
                name, signal = item
            else:
                name, signal = (f"agent_{idx}", item)
            self._mesh.ensure_profile(name)
            normalized.append((name, signal))

        buy_signals = [(name, signal) for name, signal in normalized if signal.direction == "BUY"]
        sell_signals = [(name, signal) for name, signal in normalized if signal.direction == "SELL"]

        def _side_score(rows: list[tuple[str, Signal]], direction: str) -> float:
            total = 0.0
            names = [name for name, _ in rows]
            for name, signal in rows:
                coherence = 1.0
                peers = [peer for peer in names if peer != name]
                if peers:
                    coherence = sum(self._mesh.pair(name, peer) for peer in peers) / len(peers)
                node = self._mesh.state.nodes.get(name)
                trust = node.trust if node is not None else 0.5
                total += signal.confidence * trust * coherence
            return total

        buy_weight = _side_score(buy_signals, "BUY")
        sell_weight = _side_score(sell_signals, "SELL")

        selected: list[tuple[str, Signal]]
        direction: str
        if buy_weight == sell_weight:
            selected = normalized
            direction = max(selected, key=lambda row: row[1].confidence)[1].direction
            selected = [row for row in selected if row[1].direction == direction]
        elif buy_weight > sell_weight:
            selected = buy_signals
            direction = "BUY"
        else:
            selected = sell_signals
            direction = "SELL"

        if not selected:
            self._metrics["holds"] += 1
            return None

        def _row_weight(name: str) -> float:
            node = self._mesh.state.nodes.get(name)
            trust = node.trust if node is not None else 0.5
            return _clamp(trust, 0.1, 1.5)

        weighted = [(name, signal, _row_weight(name)) for name, signal in selected]
        total_w = sum(weight for _, _, weight in weighted) or 1.0

        best = max(weighted, key=lambda row: row[1].confidence)[1]
        count = len(weighted)
        avg_conf = sum(signal.confidence * w for _, signal, w in weighted) / total_w
        avg_sl = sum(signal.stop_loss * w for _, signal, w in weighted) / total_w
        avg_tp1 = sum(signal.take_profit_1 * w for _, signal, w in weighted) / total_w
        avg_tp2 = sum(signal.take_profit_2 * w for _, signal, w in weighted) / total_w
        avg_tp3 = sum(signal.take_profit_3 * w for _, signal, w in weighted) / total_w
        reason = f"swarm consensus {direction} ({count}/{len(normalized)} agents)"

        return Signal(
            strategy=f"{self.name}_swarm",
            symbol=context.symbol,
            direction=direction,
            entry_price=best.entry_price,
            stop_loss=round(avg_sl, 5),
            take_profit_1=round(avg_tp1, 5),
            take_profit_2=round(avg_tp2, 5),
            take_profit_3=round(avg_tp3, 5),
            confidence=max(0.0, min(1.0, avg_conf)),
            timestamp=datetime.now(UTC),
            reason=reason,
            entry_snapshot=best.entry_snapshot,
        )

    @staticmethod
    def _swarm_profiles() -> list[tuple[str, str]]:
        raw = str(getattr(settings, "DEEPSEEK_AGENT_SWARM_PROFILES", "")).strip()
        if not raw:
            return list(_DEFAULT_SWARM_PROFILES)

        profiles: list[tuple[str, str]] = []
        for item in raw.split(";"):
            if not item.strip():
                continue
            if ":" in item:
                name, instruction = item.split(":", 1)
            else:
                name, instruction = item, "General trading specialist role"
            name = _sanitize(name, 20).lower()
            instruction = _sanitize(instruction, 200)
            if name and instruction:
                profiles.append((name, instruction))

        return profiles or list(_DEFAULT_SWARM_PROFILES)

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

        # Handle both new format ("signal") and legacy format ("direction")
        direction = str(data.get("signal", data.get("direction", "HOLD"))).upper()
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

        # New format provides explicit entry; fall back to market price
        entry      = float(data["entry"]) if data.get("entry") else ctx.current_price
        stop_loss  = float(data.get("stop_loss", 0.0))
        tp1        = float(data.get("take_profit_1", 0.0))
        tp2        = float(data.get("take_profit_2", 0.0))
        tp3        = float(data.get("take_profit_3", 0.0))
        tp4        = float(data["take_profit_4"]) if data.get("take_profit_4") not in (None, 0, 0.0, "0", "null") else 0.0
        structural_be = float(data["structural_be"]) if data.get("structural_be") not in (None, 0, 0.0, "0", "null") else 0.0
        reasoning  = str(data.get("reason", data.get("reasoning", "")))

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

        # Extract ICT/SMC fields from response
        ict_score = int(data.get("ict_score", 0))
        smc_confirmed = bool(data.get("smc_confirmed", False))
        confluence_flags = data.get("confluence_flags", [])

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
            ict_score=ict_score,
            smc_confirmed=smc_confirmed,
            confluence_flags=confluence_flags,
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
            take_profit_4=tp4,
            structural_be=structural_be,
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
