---
name: prompt-guide
description: "How to write expert prompts for DeepSeek and Claude within the PulseTrade bot — system prompt patterns, signal formatting, chain-of-thought."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Prompt Writing Guide (PulseTrade)

## Where Prompts Are Used

| Location | Model | Purpose |
|---|---|---|
| `agents/deepseek_strategy.py` | DeepSeek Chat | ICT/macro confluence signal generation |
| `agents/council_agent.py` | DeepSeek Chat | Three-expert council vote |
| `filters/crucix_client.py` | (no LLM) | Pure HTTP — no prompt needed |

---

## DeepSeek Strategy Prompt Pattern

### System Prompt Principles

1. **Assign a role** — give the model an expert identity with specific domain vocabulary
2. **Constrain the output format** — always ask for JSON; never free text
3. **State what to return on no-signal** — prevents hallucinated trades
4. **Limit reasoning scope** — focus on the data provided, not invented context

```python
SYSTEM = """You are a professional ICT (Inner Circle Trader) analyst specialising in Smart Money
Concepts. You identify high-probability order flow setups from raw OHLCV data.

Respond ONLY with valid JSON matching this schema:
{
  "signal": "BUY" | "SELL" | "NONE",
  "confidence": 0.0–1.0,
  "reason": "one-sentence ICT rationale",
  "entry": float,
  "stop_loss": float,
  "take_profit_1": float,
  "take_profit_2": float,
  "take_profit_3": float
}

If no high-probability setup exists, return {"signal": "NONE"}.
Never invent data not present in the input. Never add commentary outside the JSON."""
```

### User Message Pattern

Pack only what is needed. Token efficiency matters on a 30-second loop:

```python
user_msg = f"""Symbol: {symbol}
Session: {context.session.value}
Trend (HTF): {context.htf_bias}
ATR: {context.atr:.5f}
Spread: {context.spread:.1f} pips
RSI: {context.rsi:.1f}
Recent candles (last 20, H1):
{format_candles(context.candles[-20:])}
"""
```

### Candle Formatter
```python
def format_candles(candles: list[Candle]) -> str:
    lines = []
    for c in candles:
        lines.append(
            f"{c.timestamp.strftime('%m-%d %H:%M')} "
            f"O={c.open:.5f} H={c.high:.5f} L={c.low:.5f} C={c.close:.5f}"
        )
    return "\n".join(lines)
```

---

## Council Agent Prompt Pattern

The council uses three independent expert personas voting on a signal.

### Persona Definitions

```python
ICT_EXPERT = """You are an ICT/SMC expert. Evaluate the signal for:
- HTF bias alignment (BOS, MSS, CHoCH)
- Liquidity sweep before entry
- Premium/discount zone (entry above/below equilibrium)
- FVG or Order Block confluence
Score 0.0–1.0. Respond with JSON: {"score": float, "reasoning": "one sentence"}"""

DANIAL_EXPERT = """You are DanialFX. Evaluate for:
- Clean price action structure (no chop)
- Session killzone alignment (London/NY open)
- Momentum confirmation (no reversal divergence)
Score 0.0–1.0. JSON: {"score": float, "reasoning": "one sentence"}"""

TRADITIONAL_EXPERT = """You are a classical technical analyst. Evaluate for:
- Trend alignment on multiple timeframes
- Key S/R level confluence
- Volume confirmation if available
Score 0.0–1.0. JSON: {"score": float, "reasoning": "one sentence"}"""
```

### Calling Pattern
```python
responses = await asyncio.gather(
    call_deepseek(ICT_EXPERT, signal_context),
    call_deepseek(DANIAL_EXPERT, signal_context),
    call_deepseek(TRADITIONAL_EXPERT, signal_context),
)
```

---

## Prompt Anti-Patterns (Avoid These)

```
❌  "Analyse this chart and tell me what to do"  — vague, produces verbose text
❌  Asking for prose reasoning without JSON wrapper — hard to parse reliably
❌  Sending all 200 candles — wastes tokens, confuses the model
❌  Not specifying a NONE return path — model will invent a signal
❌  Using "think step by step" with DeepSeek Chat — adds latency, marginal gain
❌  System prompt longer than ~300 tokens for simple scoring — diminishing returns
```

---

## Signal Context Block

When sending a signal to the council, pack a structured context block:

```python
signal_context = f"""Signal to evaluate:
Direction: {signal.direction}
Entry: {signal.entry_price}
SL: {signal.stop_loss} ({sl_pips:.1f} pips)
TP1: {signal.take_profit_1} | TP2: {signal.take_profit_2} | TP3: {signal.take_profit_3}
RR: {rr:.2f}
Strategy: {signal.strategy}
Reason: {signal.reason}

Market context:
Symbol: {context.symbol}
Session: {context.session.value}
HTF bias: {context.htf_bias}
VIX: {macro.vix:.1f}  Risk tier: {macro.risk_tier}
Spread: {context.spread:.1f} pips  ATR: {context.atr:.5f}"""
```

---

## DeepSeek API Call Wrapper

```python
import httpx

async def call_deepseek(system: str, user: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,   # low for deterministic scoring
                "max_tokens": 256,
                "response_format": {"type": "json_object"},
            },
        )
    return resp.json()["choices"][0]["message"]["content"]
```

Key settings:
- `temperature=0.1` — keeps scoring stable across repeated calls
- `max_tokens=256` — JSON responses never need more
- `response_format={"type": "json_object"}` — enforces JSON mode (DeepSeek supports this)

---

## Caching Strategy

DeepSeek calls are expensive (~0.3s latency + API cost). Cache aggressively:

```python
# In deepseek_strategy.py
_cache: dict[str, tuple[Signal, datetime]] = {}

cache_key = f"{symbol}:{context.regime.value}:{round(context.close, 4)}"
if cache_key in _cache:
    signal, cached_at = _cache[cache_key]
    age_min = (datetime.now(UTC) - cached_at).total_seconds() / 60
    if age_min < settings.DEEPSEEK_CACHE_MINUTES:
        return signal   # reuse without API call
```

---

## Tips for Writing New Prompts

1. **One task per prompt** — don't ask the model to both analyse AND score in one call
2. **Mirror ICT vocabulary** — MSS, BOS, FVG, OB, PD Array, killzone — the model knows these
3. **Always include RR** — models score much better when they can see the risk/reward ratio
4. **Keep system prompts under 400 tokens** — beyond that, instruction-following degrades
5. **Test with `temperature=0`** for debugging — then raise to 0.1 for production variance
