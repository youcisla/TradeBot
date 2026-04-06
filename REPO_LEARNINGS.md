# PulseTrade TradingBot — Repository Research Synthesis

> Compiled from ~26 GitHub repositories analyzed to extract actionable upgrades for PulseTrade.
> Each finding is labeled: **P0** (immediate/high-impact), **P1** (next sprint), **P2** (future/optional).
> Sources are noted inline. Total research base: ~490k stars across repositories.

---

## Table of Contents

1. [Intelligence Sweep Module (replaces Crucix)](#1-intelligence-sweep-module-replaces-crucix)
2. [ML Model Upgrades](#2-ml-model-upgrades)
3. [Agent Pipeline Redesign](#3-agent-pipeline-redesign)
4. [OpenAlice Architecture Patterns](#4-openalice-architecture-patterns)
5. [Signal Quality Gates](#5-signal-quality-gates)
6. [Backtesting Standards](#6-backtesting-standards)
7. [Data Sources & Feature Engineering](#7-data-sources--feature-engineering)
8. [Risk Management](#8-risk-management)
9. [SKILL.md + MCP Dual Interface Architecture](#9-skillmd--mcp-dual-interface-architecture)

---

## 1. Intelligence Sweep Module (replaces Crucix)

**Source:** `calesthio/Crucix` (8.5k stars, AGPL-3.0, ACTIVE)

Crucix is a 27-source macro intelligence platform in Node.js ESM. Its architecture reveals what a native Python equivalent would look like for PulseTrade.

### Core Architecture Pattern

```
Crucix server.mjs → Promise.allSettled(27 sources in parallel, ~30s timeout per source)
                  → lib/delta/engine.mjs (semantic dedup + severity scoring)
                  → lib/llm/ (8 providers with graceful fallback to rule-based)
                  → lib/alerts/ (Telegram: FLASH/PRIORITY/ROUTINE tiers)
                  → SSE push to dashboard browsers
```

**PulseTrade Python equivalent:**

```python
# filters/intelligence_sweep.py
import asyncio, aiohttp, yfinance as yf

class IntelligenceSweep:
    async def run_all_sources(self) -> dict:
        results = await asyncio.gather(
            self._fetch_fred(),      # 22 macro indicators
            self._fetch_gdelt(),     # global news events
            self._fetch_yfinance(),  # SPY, VIX, BTC, Gold, Silver
            self._fetch_eia(),       # WTI/Brent — free key
            self._fetch_bls(),       # NFP, payrolls
            self._fetch_us_treasury(),
            return_exceptions=True   # equivalent to Promise.allSettled()
        )
        return {k: v for k, v in zip(SOURCE_NAMES, results)
                if not isinstance(v, Exception)}  # graceful degradation

    async def score_delta(self, previous: dict, current: dict) -> list[Alert]:
        """DeltaEngine: compare sweeps and classify changes."""
        alerts = []
        for key in current:
            delta = self._compute_change(previous.get(key), current[key])
            if delta.severity >= 0.8:
                alerts.append(Alert(tier="FLASH", key=key, delta=delta))
            elif delta.severity >= 0.5:
                alerts.append(Alert(tier="PRIORITY", key=key, delta=delta))
            else:
                alerts.append(Alert(tier="ROUTINE", key=key, delta=delta))
        return alerts
```

### 27 Data Sources — Tier Classification

| Tier | Source | Free Key? | Python Library |
|------|---------|-----------|----------------|
| **Macro** | FRED API — 22 indicators (CPI, VIX, yield curve, Fed funds, M2) | `FRED_API_KEY` (free, 60s signup) | `fredapi` |
| **Macro** | US Treasury | No key needed | `requests` |
| **Macro** | BLS (NFP, payrolls) | `BLS_API_KEY` (free) | `requests` |
| **Energy** | EIA (WTI/Brent oil) | `EIA_API_KEY` (free, 60s signup) | `requests` |
| **Market** | Yahoo Finance (SPY, QQQ, BTC, Gold, WTI, VIX, Silver) | **No key** | `yfinance` |
| **News** | GDELT (100+ languages, real-time) | No key needed | `requests` |
| **News** | Reddit OAuth | Reddit app credentials | `praw` |
| **Geo** | GDELT + ACLED conflict events | No key / `ACLED_EMAIL` | `requests` |
| **Geo** | ReliefWeb, WHO, OFAC, OpenSanctions | No key, rate-limited | `requests` |
| **Supply Chain** | Global Supply Chain Pressure Index (GSCPI) | No key | `requests` |
| **Trade** | UN Comtrade | Free tier available | `comtradeapicall` |

### Delta Memory Pattern (from `runs/memory/`)

```
runs/memory/hot.json   ← last 3 sweeps (fast compare)
runs/memory/cold/      ← YYYY-MM-DD.json archives
```

Adopt in `state/intelligence_memory.py` using PostgreSQL:
- Table: `intelligence_sweeps(id, ts, source, payload, delta_score, tier)`
- Query last sweep per source for delta computation

### Telegram Two-Way Command Interface

```python
# Register commands from Crucix pattern:
COMMANDS = {
    "/brief":     lambda: generate_current_briefing(),
    "/sweep":     lambda: run_manual_sweep(),
    "/status":    lambda: get_bot_status(),
    "/portfolio": lambda: get_portfolio_snapshot(),
    "/alerts":    lambda: get_recent_alerts(),
    "/mute 2h":   lambda h: mute_alerts(hours=int(h)),
    "/unmute":    lambda: unmute_alerts(),
}
```

### Briefing Template Pattern

Crucix uses `BRIEFING_TEMPLATE.md` — a structured output format that Claude populates. Add to PulseTrade:

```markdown
# Intelligence Briefing — {timestamp}

## FLASH ALERTS (act within 1h)
{flash_alerts}

## MACRO CONTEXT
- CPI YoY: {fred_cpi}  | Trend: {cpi_trend}
- VIX: {vix} ({vix_regime})  | 10Y Yield: {treasury_10y}
- WTI: ${eia_wti}  | Supply: {eia_supply_trend}

## MARKET SENTIMENT (Yahoo Finance)
SPY: {spy_pct:+.2f}% | QQQ: {qqq_pct:+.2f}% | BTC: {btc_pct:+.2f}%
VIX Level: {vix_level} — Regime: {risk_on_off}

## GDELT NEWS SCORE
Global tension index: {gdelt_tone_avg:.2f} (–10=negative, +10=positive)
Top themes: {gdelt_themes}

## RECOMMENDED POSTURE
{llm_recommendation | rule_based_fallback}
```

### LLM Fallback Chain (from Crucix `lib/llm/`)

```python
PROVIDER_ORDER = ["anthropic", "openrouter", "rule_based"]

async def get_intelligence_summary(context: dict) -> str:
    for provider in PROVIDER_ORDER:
        try:
            return await call_llm(provider, context)
        except Exception:
            continue
    return rule_based_summary(context)  # always succeeds
```

### Implementation Priority

| Item | Priority | Effort |
|------|----------|--------|
| `IntelligenceSweep` class with `asyncio.gather()` | **P0** | 2 days |
| FRED API integration (22 macro indicators) | **P0** | 1 day |
| Yahoo Finance (`yfinance`) market context | **P0** | 0.5 days |
| `DeltaEngine` (FLASH/PRIORITY/ROUTINE scoring) | **P0** | 1 day |
| Telegram two-way command interface | **P1** | 1 day |
| GDELT integration | **P1** | 1 day |
| EIA/BLS integrations | **P1** | 1 day |
| `BRIEFING_TEMPLATE.md` structured output | **P1** | 0.5 days |
| Delta memory in PostgreSQL | **P1** | 1 day |
| Rename Settings "Crucix" card → "Intelligence Suite" | **P0** | 15 min |

---

## 2. ML Model Upgrades

**Sources:** `huseinzol05/Stock-Prediction-Models` (9.3k stars), `stefan-jansen/machine-learning-for-trading` (17k stars, 150+ notebooks), `tensortrade-org/tensortrade` (6.1k stars, **v1.0.4 Feb 2026 ACTIVE**)

### Model Benchmark (from huseinzol05)

| Model | Accuracy | Time/epoch | Priority |
|-------|----------|------------|----------|
| **Dilated-CNN-Seq2seq** | **95.86%** | **0:14 (FASTEST)** | **P1 — evaluate now** |
| LSTM (current) | 95.693% | 1:09 | ✅ in use |
| LSTM Seq2seq VAE | 95.42% | 1:48 | P2 |
| Attention/Transformer | 94.25% | 1:41 | P2 |
| GRU | 94.63% | 2:10 | P2 |

**Action (P1):** Benchmark Dilated-CNN-Seq2seq on EURUSD H1. If it matches LSTM accuracy at 5× speed, it becomes the production model — faster inference = more symbols covered per inference cycle.

```python
# models/dilated_cnn_seq2seq.py
import tensorflow as tf

def build_dilated_cnn_seq2seq(input_shape, n_features):
    inputs = tf.keras.Input(shape=input_shape)
    x = inputs
    for dilation in [1, 2, 4, 8, 16]:
        x = tf.keras.layers.Conv1D(64, 3, dilation_rate=dilation,
                                    padding='causal', activation='relu')(x)
        x = tf.keras.layers.LayerNormalization()(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    outputs = tf.keras.layers.Dense(3, activation='softmax')(x)  # up/down/unchanged
    return tf.keras.Model(inputs, outputs)
```

### 3-Class Output (from huseinzol05 + HFT-price-prediction)

Replace binary BUY/SELL with **3-class output**: `up / unchanged / down`

```python
# Current: binary
signal = 1 if prediction > 0.5 else -1

# Improved: 3-class
class_probs = model.predict(features)  # [p_down, p_unchanged, p_up]
if class_probs[2] > CONFIDENCE_THRESHOLD:   # strong up
    signal = SignalType.BUY
elif class_probs[0] > CONFIDENCE_THRESHOLD: # strong down
    signal = SignalType.SELL
else:
    signal = SignalType.HOLD               # unchanged — don't force a trade
```

**Why:** The "unchanged" class prevents the model from forcing binary decisions in sideways markets — the most common source of false signals.

### Kalman Filter for Price Denoising (from ML-for-Trading Ch4)

Apply **before** LSTM input, not as a signal itself:

```python
# utils/kalman_filter.py
from pykalman import KalmanFilter
import numpy as np

def kalman_smooth(prices: np.ndarray) -> np.ndarray:
    kf = KalmanFilter(
        transition_matrices=[1],
        observation_matrices=[1],
        initial_state_mean=prices[0],
        initial_state_covariance=1,
        observation_covariance=1,
        transition_covariance=0.01
    )
    state_means, _ = kf.filter(prices)
    return state_means.flatten()

# In model_manager.py — apply to close prices before feature engineering:
smoothed_close = kalman_smooth(df['close'].values)
df['close_kalman'] = smoothed_close
```

**Priority: P1** — can be added as a preprocessing step without changing model architecture.

### GARCH Volatility Regime (from ML-for-Trading Ch9)

Use GARCH(1,1) to forecast next-bar volatility — a regime indicator, not a price direction signal:

```python
# models/garch_regime.py
from arch import arch_model

def fit_garch_regime(returns: np.ndarray) -> dict:
    model = arch_model(returns * 100, vol='GARCH', p=1, q=1)
    result = model.fit(disp='off', last_obs=len(returns)-1)
    forecast = result.forecast(horizon=1)
    predicted_vol = np.sqrt(forecast.variance.values[-1, 0])
    
    # Regime classification
    vol_percentile = np.percentile(result.conditional_volatility, 75)
    regime = "HIGH_VOL" if predicted_vol > vol_percentile else "LOW_VOL"
    return {"predicted_vol": predicted_vol, "regime": regime}
```

**Use:** Gate RL/neural entries — reduce position size by 50% in `HIGH_VOL` regime.

### SHAP Feature Explainability (from ML-for-Trading Ch12)

Add a SHAP layer to understand which features drive each LSTM prediction:

```python
# agents/model_manager.py — after training
import shap

def explain_prediction(model, features_df, last_n=100):
    explainer = shap.DeepExplainer(model, features_df[-last_n:].values)
    shap_values = explainer.shap_values(features_df[-1:].values)
    
    feature_importance = pd.DataFrame({
        'feature': features_df.columns,
        'shap_mean': np.abs(shap_values[0]).mean(axis=0)
    }).sort_values('shap_mean', ascending=False)
    
    # Log top 5 drivers for this prediction
    return feature_importance.head(5)
```

**Why:** When the bot issues a signal, the council agent can read the top SHAP drivers and include them in its reasoning. Also surfaces when a feature becomes noise.

### WorldQuant 101 Formulaic Alphas (from ML-for-Trading Ch24)

A library of 101 quantitative alpha factors with empirically measured holding periods (avg 0.6–6.4 days). Treat as a feature engineering library, not a signal source:

```python
# features/worldquant_alphas.py
# Alpha 1: sign(delta(return(close, 1), 5)) * (-1 * delta(close, 3))
# Alpha 12: sign(delta(volume, 1)) * (-1 * delta(close, 1))
# Alpha 28: scale(correlation(adv20, low, 5), 1) + rank(open - hloc)
# ... etc. (full list in 101 Formulaic Alphas paper, SSRN 2601015)

def compute_alpha_set(df: pd.DataFrame, alphas: list[int]) -> pd.DataFrame:
    """Compute selected WorldQuant alphas as ML features."""
    result = {}
    for alpha_id in alphas:
        result[f'wq_alpha_{alpha_id}'] = ALPHA_FUNCTIONS[alpha_id](df)
    return pd.DataFrame(result)
```

**Priority: P2** — add during next feature engineering pass.

### TimeGAN for Synthetic Training Data (from ML-for-Trading Ch21, NeurIPS 2019)

When training data is scarce (rare market regimes, new symbols), TimeGAN generates synthetic OHLCV sequences that preserve temporal dynamics:

```python
# P2: Install: pip install ydata-sdk
# Use when: <2 years of H1 data for a new symbol
from ydata_synthetic.synthesizers.timeseries import TimeGAN

model = TimeGAN(model_parameters={
    "batch_size": 128, "lr": 5e-4, "betas": (0.5, 0.9),
    "latent_dim": 24, "gam": 1, "gamma": 1
})
model.fit(real_data, train_steps=10000, seq_len=24)
synthetic = model.sample(n_samples=1000)
```

**Priority: P2** — valuable for scarce-data symbols; use in backtesting/research only.

### TensorTrade Key Insight — Commission Destroys Profitability

From tensortrade research (v1.0.4, Feb 2026, Python 3.12+):

| Scenario | Result |
|----------|--------|
| RL Agent (0% commission) | **+$239 / +$594 profit** |
| RL Agent (0.1% commission) | **-$650 / -$295 loss** |
| Buy-and-Hold baseline | -$355 |

**Lesson:** Any RL agent or neural signal that looks profitable in zero-commission simulation will likely be loss-making in production. **Always include the spread in simulation.** For MT5 live: typical EURUSD spread = 0.7–1.5 pips = 0.007%–0.015% per side. Still meaningful over many trades.

```python
# backtesting/engine.py — required field
class BacktestConfig:
    commission_pct: float = 0.0001  # 1 pip per side on EURUSD — NEVER use 0.0
    slippage_pips: float = 0.5      # realistic MT5 slippage
```

### Stacking Ensemble Pattern (from huseinzol05)

Two validated ensembles from Stock-Prediction-Models:
- **Ensemble A:** AutoEncoder + DRNN + ARIMA + XGBoost
- **Ensemble B:** AdaBoost + Bagging + ExtraTrees + GBM + RF + XGBoost

For PulseTrade: run LightGBM alongside LSTM. If both agree → high-confidence signal. If they disagree → HOLD.

```python
# Ensemble vote in strategy_agent.py
lstm_signal = neural_strategy.predict(features)     # +1, 0, -1
lgbm_signal = lgbm_model.predict(features)          # +1, 0, -1

if lstm_signal == lgbm_signal and lstm_signal != 0:
    confidence = "HIGH"
    final_signal = lstm_signal
elif lstm_signal != 0 and lgbm_signal == 0:
    confidence = "MEDIUM"
    final_signal = lstm_signal
else:
    confidence = "LOW"
    final_signal = 0  # disagreement → HOLD
```

---

## 3. Agent Pipeline Redesign

**Sources:** `TauricResearch/TradingAgents` (47.4k stars, ACTIVE — updated yesterday), `MSL135/GODMOD3` (88 stars)

### LangGraph Multi-Specialist Pipeline (from TradingAgents v0.2.3)

The current PulseTrade pipeline is linear. TradingAgents proves that a specialist debate model produces better decisions:

```
Current PulseTrade:
market → analysis → strategy → neural → council → risk → execution

Improved (TradingAgents pattern):
Fundamentals Analyst ─┐
Sentiment Analyst     ├→ Researcher Team ─→ Trader Agent → Risk Mgmt → Portfolio Manager
News Analyst          │   (Bull vs Bear         (proposes)   (validates)  (final gatekeeper)
Technical Analyst ────┘    debate rounds)
```

**Implementation via LangGraph:**

```python
# pip install langgraph

from langgraph.graph import StateGraph, END

workflow = StateGraph(TradingState)
workflow.add_node("fundamentals", fundamentals_analyst)
workflow.add_node("sentiment", sentiment_analyst)
workflow.add_node("news", news_analyst)
workflow.add_node("technical", technical_analyst)
workflow.add_node("bull_researcher", bull_researcher)
workflow.add_node("bear_researcher", bear_researcher)
workflow.add_node("trader", trader_agent)
workflow.add_node("risk_mgmt", risk_agent)
workflow.add_node("portfolio_mgr", portfolio_manager)  # gatekeeper

# Analysts run in parallel, then debate begins
workflow.add_edges(["fundamentals", "sentiment", "news", "technical"],
                   "bull_researcher")
workflow.add_conditional_edges("bull_researcher",
    lambda s: "bear_researcher" if s["debate_round"] < MAX_DEBATE_ROUNDS else "trader")

app = workflow.compile()
decision = app.invoke({"symbol": "EURUSD", "date": "2026-01-15"})
```

**Config:**

```python
config = {
    "llm_provider": "anthropic",
    "deep_think_llm": "claude-sonnet-4-6",   # analysts + debate
    "quick_think_llm": "claude-haiku-3-5",    # routing + summaries
    "max_debate_rounds": 2,                    # empirically optimal
    "online_tools": True                       # live data during debate
}
```

**Cost optimization:** `quick_think_llm` handles all classification and routing (90% of calls). `deep_think_llm` only for complex analysis and final debate. This cuts LLM cost by ~70%.

### OpenRouter as Unified LLM Gateway (from GODMOD3)

```python
# config/settings.py
LLM_PROVIDERS = {
    "primary":   "anthropic/claude-sonnet-4-6",
    "secondary": "google/gemini-2.5-flash",
    "fallback":  "meta-llama/llama-3.3-70b-instruct",
}

# Single API key, multiple models:
import openai
client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"]
)
```

**Priority: P1** — especially useful when Anthropic API is down or rate-limited.

### Model Committee Vote (from GODMOD3's ULTRAPLINIAN pattern)

For major trading decisions, query 3 LLMs and take the majority consensus:

```python
async def committee_vote(prompt: str, models: list[str]) -> tuple[str, float]:
    responses = await asyncio.gather(*[call_llm(m, prompt) for m in models])
    signals = [parse_signal(r) for r in responses]
    
    counts = Counter(signals)
    majority_signal, votes = counts.most_common(1)[0]
    confidence = votes / len(models)
    
    return majority_signal, confidence  # (BUY/SELL/HOLD, 0.33/0.67/1.0)
```

**Use for:** Council decisions only (once per bar, high-stakes). Not for fast inference loops.

### Strip Hedging Language (from GODMOD3's Hedge Reducer / "STM")

Before any LLM output reaches the decision layer, strip epistemic hedges:

```python
HEDGE_PATTERNS = [
    r'\bI think\b', r'\bmaybe\b', r'\bperhaps\b', r'\bpossibly\b',
    r'\bit seems\b', r'\bit appears\b', r'\bmight\b', r'\bcould be\b',
    r'\bprobably\b', r'\bI believe\b', r'\bI\'m not sure\b'
]

def strip_hedges(text: str) -> str:
    for pattern in HEDGE_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return ' '.join(text.split())  # normalize whitespace
```

**Why:** When the council agent reads "maybe buy EURUSD", the word "maybe" adds ambiguity to an already uncertain decision. Remove it. The confidence score lives in the structured output, not the prose.

---

## 4. OpenAlice Architecture Patterns

**Source:** `TraderAlice/OpenAlice` (3.1k stars, AGPL-3.0, EXTREMELY ACTIVE — updated 10h ago, built WITH Claude)

OpenAlice is the most architecturally relevant repository in this research. It represents "what PulseTrade wants to become" — a 24/7 autonomous trading agent with proper auditability and human oversight.

### Trading-as-Git: Order Lifecycle

Every order goes through a git-like commit flow:

```python
# Current PulseTrade order flow:
execution_agent.place_order(symbol, lots, direction)  # opaque, no audit trail

# OpenAlice pattern:
uta = UnifiedTradingAccount(broker=mt5_connector)
uta.stage_order(symbol="EURUSD", lots=0.1, direction="BUY",
                reason="LSTM confidence=0.87, council=APPROVE")  # stage
commit_hash = uta.commit("Neural signal confirmed by council")    # commit
result = uta.push()                                               # push → runs guards → MT5
# Result: { hash: "a3f12b9c", timestamp: ..., guards_passed: [...], broker_response: ... }
```

**Implement in:** `agents/execution_agent.py` + `state/trade_git.py`

**PostgreSQL table:**

```sql
CREATE TABLE trade_commits (
    hash        CHAR(8) PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol      VARCHAR(20) NOT NULL,
    direction   VARCHAR(10) NOT NULL,
    lots        DECIMAL(10,2) NOT NULL,
    reason      TEXT NOT NULL,
    guards      JSONB,          -- list of passed/failed guards
    broker_resp JSONB,          -- MT5 response
    parent_hash CHAR(8)         -- for trade modifications (trailing stop, partial close)
);
```

**Priority: P0** — this is foundational auditability. Every production trade should have a hash.

### Guard Pipeline (Pre-Execution Safety Layer)

Guards run BEFORE orders reach MT5. They are the last safety gate:

```python
# agents/guards.py
class GuardPipeline:
    GUARDS = [
        MaxPositionSizeGuard(max_lots=1.0),
        SymbolWhitelistGuard(allowed=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]),
        CooldownGuard(min_seconds_between_trades=300),        # 5 min per symbol
        DailyDrawdownGuard(max_daily_loss_pct=0.05),          # 5% daily limit
        MarketHoursGuard(avoid_hours=[22, 23, 0, 1]),         # no Asian open/close
        VolatilityGuard(max_vix_for_entry=35.0),              # risk-off gate
        FeedFreshnessGuard(max_staleness_seconds=30),         # MT5 data latency
    ]

    def run(self, order: Order) -> GuardResult:
        for guard in self.GUARDS:
            result = guard.check(order)
            if not result.passed:
                return GuardResult(passed=False, blocker=guard.name,
                                   reason=result.reason)
        return GuardResult(passed=True)
```

**FeedFreshnessGuard** is from HFT-Arbitrage-EA research: if MT5 feed timestamp delta > threshold, the data is stale — don't trade.

**Priority: P0** — add immediately. Current execution agent has no pre-execution validation layer.

### EventLog: Append-Only JSONL Bus

All system events flow through a single append-only log:

```python
# state/event_log.py
import json
from pathlib import Path
from datetime import datetime, timezone

class EventLog:
    def __init__(self, path="logs/events.jsonl"):
        self.path = Path(path)

    def emit(self, event_type: str, payload: dict):
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **payload
        }
        with open(self.path, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def replay_since(self, ts: str) -> list[dict]:
        """Crash recovery: replay all events since timestamp."""
        events = []
        with open(self.path) as f:
            for line in f:
                event = json.loads(line)
                if event['ts'] >= ts:
                    events.append(event)
        return events
```

**Event types to emit:** `ORDER_STAGED`, `GUARD_BLOCKED`, `ORDER_EXECUTED`, `TRADE_CLOSED`, `SWEEP_COMPLETED`, `ALERT_FIRED`, `AGENT_ERROR`, `CONTEXT_COMPACTED`

**Priority: P1** — foundational for debugging 24/7 operations.

### HEARTBEAT Protocol

The bot should not interrupt humans unless necessary:

```python
# state/heartbeat.py
class HeartbeatDecision(str, Enum):
    OK = "HEARTBEAT_OK"        # all good, no action needed
    CHAT_NO = "CHAT_NO"        # notable event but not urgent
    CHAT_YES = "CHAT_YES"      # requires human decision

def evaluate_heartbeat(state: BotState) -> HeartbeatDecision:
    if state.daily_pnl < -state.config.heartbeat_loss_threshold:
        return HeartbeatDecision.CHAT_YES          # loss limit approaching
    if state.has_pending_trade_requiring_approval:
        return HeartbeatDecision.CHAT_YES          # governance gate
    if state.pending_flash_alerts > 0:
        return HeartbeatDecision.CHAT_NO           # log but don't interrupt
    return HeartbeatDecision.OK
```

**Priority: P1** — prevents alert fatigue. Telegram `/mute` + `CHAT_YES` override.

### Brain Domain: Persistent Working Memory

From OpenAlice's `domain/brain/` — the bot maintains persistent working memory between restarts:

```sql
-- PostgreSQL: agent_memory table
CREATE TABLE agent_memory (
    id          SERIAL PRIMARY KEY,
    agent_name  VARCHAR(50) NOT NULL,
    memory_type VARCHAR(30) NOT NULL,  -- 'market_context', 'trade_thesis', 'regime'
    key         VARCHAR(100) NOT NULL,
    value       JSONB NOT NULL,
    version     INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_name, memory_type, key)
);
```

Agents write their working state to this table. On restart, they reload their prior context. No more "amnesiac agent" restarts.

### Auto-Compaction for 24/7 Agents

When context window approaches limit (from OpenAlice `compaction.json`):

```python
# agents/compaction.py
COMPACTION_THRESHOLD = 0.85  # compact at 85% context fill

def maybe_compact(context: AgentContext) -> AgentContext:
    if context.fill_ratio() < COMPACTION_THRESHOLD:
        return context
    
    summary = call_llm("Summarize this agent context in 500 words, "
                        "preserving all active trade theses, risk levels, "
                        "and pending decisions: " + context.serialize())
    
    new_context = AgentContext()
    new_context.add_permanent(context.system_prompt)  # never compress
    new_context.add_summary(summary)
    new_context.add_recent(context.last_n_events(20))  # keep very recent
    
    event_log.emit("CONTEXT_COMPACTED", {"ratio": context.fill_ratio(),
                                          "summary_tokens": len(summary)})
    return new_context
```

**Critical for 24/7 bots.** Without compaction, an agent that runs for 24h will hit context limit mid-operation.

### Evolution Mode Tiers

From OpenAlice — control AI access level at runtime:

| Mode | Access | Use Case |
|------|--------|----------|
| `SANDBOX` | Read-only `data/` directory | Normal 24/7 operation |
| `REVIEW` | Read + write to `data/`, no system access | Human-supervised improvements |
| `ADMIN` | Full Bash + project access (AI can edit own source) | Supervised evolution sessions |

**Never run ADMIN mode unattended.**

---

## 5. Signal Quality Gates

**Source:** `tradermonty/claude-trading-skills` (655 stars, VERY ACTIVE — updated 16h ago)

This repo proves that a SKILL.md-based quality gate system dramatically improves signal precision. The following gates should wrap the PulseTrade execution pipeline.

### ExposureCoach — Master Gate (highest priority)

```python
class ExposureDecision(str, Enum):
    NEW_ENTRY_ALLOWED = "NEW_ENTRY_ALLOWED"   # market is healthy, proceed
    REDUCE_ONLY = "REDUCE_ONLY"               # only reduce existing positions
    CASH_PRIORITY = "CASH_PRIORITY"           # move to cash, no new entries

def evaluate_exposure(breadth_score: float, distribution_days: int,
                       vix: float, regime: str) -> ExposureDecision:
    """
    Market breadth score 0-100 (6 components):
    - % stocks above 50MA, 200MA
    - New 52-week highs vs lows ratio
    - Advance/decline ratio
    - Sector participation breadth
    - Volume distribution (up vs down volume)
    """
    if breadth_score < 40 or distribution_days >= 5 or regime == "CASH_PRIORITY":
        return ExposureDecision.CASH_PRIORITY
    if breadth_score < 60 or distribution_days >= 3 or vix > 25:
        return ExposureDecision.REDUCE_ONLY
    return ExposureDecision.NEW_ENTRY_ALLOWED
```

**Run this before every entry signal.** If `CASH_PRIORITY`, skip regardless of neural confidence.

### Follow-Through Day (FTD) State Machine — O'Neil

```python
class FTDState(str, Enum):
    NO_BASE = "NO_BASE"
    IN_DECLINE = "IN_DECLINE"
    ATTEMPTED_RALLY = "ATTEMPTED_RALLY"       # day 1-3 of rally attempt
    FTD_CONFIRMED = "FTD_CONFIRMED"           # day 4+ with volume surge ≥+1.25%
    DISTRIBUTION_WARNING = "DISTRIBUTION_WARNING"

# FTD requires: day ≥4 of rally, close gain ≥1.25%, volume > prior day
# Market top signal: 4-5 Distribution Days in 4 weeks
```

**Priority: P1** for equity/index signals. Less critical for pure forex but VIX proxy works.

### Signal Postmortem — Classify Every Closed Trade

```python
class PostmortemClass(str, Enum):
    TRUE_POSITIVE = "TRUE_POSITIVE"           # signal + profitable
    FALSE_POSITIVE = "FALSE_POSITIVE"         # signal + loss (model error)
    MISSED_OPPORTUNITY = "MISSED_OPPORTUNITY" # no signal + would have been profitable
    REGIME_MISMATCH = "REGIME_MISMATCH"       # correct signal, wrong market regime

def classify_trade(trade: ClosedTrade, regime_at_entry: str) -> PostmortemClass:
    if trade.pnl > 0 and trade.signal_confidence > 0.7:
        return PostmortemClass.TRUE_POSITIVE
    if trade.pnl < 0 and regime_at_entry in ["BEAR", "HIGH_VOL"]:
        return PostmortemClass.REGIME_MISMATCH  # don't penalize model
    if trade.pnl < 0:
        return PostmortemClass.FALSE_POSITIVE
    ...
```

**Store postmortem in PostgreSQL. Review weekly. Feed FALSE_POSITIVE patterns back to fine-tuning.**

### Trader Memory Core (from claude-trading-skills)

```sql
-- PostgreSQL: trade_theses
CREATE TABLE trade_theses (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    direction   VARCHAR(10) NOT NULL,
    state       VARCHAR(20) NOT NULL,  -- IDEA, ENTRY_READY, ACTIVE, CLOSED
    thesis      TEXT NOT NULL,
    entry_price DECIMAL(15,5),
    exit_price  DECIMAL(15,5),
    mae         DECIMAL(15,5),  -- Maximum Adverse Excursion
    mfe         DECIMAL(15,5),  -- Maximum Favorable Excursion
    postmortem  VARCHAR(30),    -- PostmortemClass
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**MAE/MFE analysis** reveals: if trades regularly show large MFE before turning to MAE, stops are too tight. If MAE is large, stops are too loose. Quantitative stop calibration.

---

## 6. Backtesting Standards

**Sources:** `mementum/backtrader` (21k stars, GPL-3.0), `QuantConnect/Lean` (18.3k stars), `tensortrade-org/tensortrade` (v1.0.4, ACTIVE), `Yvictor/TradingGym` (1.9k stars, archived)

### backtrader: Cerebro + SQN as Primary Metric

```python
import backtrader as bt

cerebro = bt.Cerebro()
cerebro.addstrategy(PulseTradeStrategy)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                    riskfreerate=0.05, annualize=True)
cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')           # PRIMARY METRIC
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

# Commission — ALWAYS set, NEVER skip
cerebro.broker.setcommission(commission=0.0001,               # 1 pip per side
                              margin=None, mult=1.0)
cerebro.broker.set_slippage_perc(0.0001)                      # 1 pip slippage

results = cerebro.run()
sqn = results[0].analyzers.sqn.get_analysis()['sqn']

# SQN interpretation:
# < 1.6 = below average | 1.6-1.9 = average | 2.0-2.4 = good
# 2.5-2.9 = excellent | 3.0+ = superb | >7.0 = impossible (overfit)
```

**Why SQN over Sharpe?** SQN accounts for consistency of wins across ALL trades, not just volatility of returns. A strategy with SQN > 2.5 is genuinely robust.

### Cheat-on-Close Discipline

Never use the closing price of bar N to generate a signal that executes AT the close of bar N:

```python
# WRONG — lookahead bias:
if self.data.close[0] > self.sma[0]:  # uses current bar's close to decide NOW
    self.buy()

# CORRECT — use close of prior bar:
if self.data.close[-1] > self.sma[-1]:  # signal from completed bar
    self.buy()                            # executed at next open
```

### Walk-Forward Optimization (from Lean + tensortrade)

NOT optional. Walk-Forward is the minimum standard for validating a production strategy:

```python
# backtesting/walk_forward.py
def walk_forward_test(strategy_class, data, n_folds=5, test_pct=0.2):
    fold_size = len(data) // n_folds
    results = []
    
    for i in range(n_folds):
        train_end = fold_size * (i + 1)
        test_start = train_end
        test_end = min(test_start + int(fold_size * test_pct), len(data))
        
        train_data = data[:train_end]
        test_data = data[test_start:test_end]
        
        # Fit on train, evaluate on out-of-sample test
        opt_params = optimize(strategy_class, train_data)
        oos_result = evaluate(strategy_class, test_data, params=opt_params)
        results.append(oos_result)
    
    # Strategy is valid only if MEDIAN OOS SQN > 1.6
    return {
        "median_sqn": np.median([r['sqn'] for r in results]),
        "worst_drawdown": max(r['max_drawdown'] for r in results),
        "consistency": len([r for r in results if r['sqn'] > 0]) / n_folds
    }
```

### TradingGym: RL Environment with Fee

Always include fee and bid/ask spread as features in RL environments:

```python
# RL training — mandatory fee parameter
env = TradingEnv(
    obs_data_len=256,           # lookback window
    step_len=128,               # steps per episode
    df=df,
    fee=0.0001,                 # NEVER use 0.0 — commission destroys RL profitability
    max_position=3,
    feature_names=[
        'close', 'volume',
        'bid_price', 'ask_price',    # explicit bid/ask — not inferred from close
        'ask_deal_vol', 'bid_deal_vol',
        'bid_ask_ratio',             # microstructure signal
        'price_direction'
    ]
)
```

### Four-Layer Algorithm Framework (from Lean/QuantConnect)

For any new strategy, design against this 4-layer model:

```
Layer 1: Alpha ──────────── Generates raw signals (LSTM, dilated CNN, indicators)
Layer 2: Portfolio ───────── Sizes positions, manages exposure (Kelly + constraints)
Layer 3: Risk Mgmt ───────── Caps losses (daily limit, max drawdown, guard pipeline)
Layer 4: Execution ───────── Order routing, timing, slippage minimization
```

Each layer is independently testable and swappable.

---

## 7. Data Sources & Feature Engineering

**Sources:** Crucix analysis, `hzjken/HFT-price-prediction` (76-78% OOS accuracy), `Mathieu2301/TradingView-API` (2.9k stars), `staskh/trading_skills` (77 stars), `HKUDS/AI-Trader` (12.2k stars)

### Complete Free Data Source Inventory

| Source | What | Key/Cost | Python |
|--------|------|----------|--------|
| **FRED API** | 22 macro indicators: CPI, Fed funds rate, VIX, M2, yield curve, unemployment | Free key (60s signup) | `fredapi` |
| **Yahoo Finance** | SPY, QQQ, BTC, GLD, SLV, WTI, VIX, Silver | **No key** | `yfinance` |
| **EIA** | WTI/Brent crude, natural gas, petroleum supply | Free key (60s signup) | `requests` |
| **BLS** | NFP, CPI, unemployment, PCE | Free key | `requests` |
| **US Treasury** | 2Y/5Y/10Y/30Y yields in real-time | No key | `requests` |
| **GDELT** | Real-time global news event scoring (100+ languages) | No key | `requests` |
| **Reddit OAuth** | subreddit sentiment (r/wallstreetbets, r/forex, r/investing) | App credentials | `praw` |
| **TradingView MCP** | Live RSI/MACD/BB/EMA from TV charts | TV Desktop + MCP | MCP tools |
| **Polygon.io** | Institutional options flow (whale hunting) | Free tier | `polygon-api-client` |

### Microstructure Features (from HFT-price-prediction)

These features are available from MT5 tick data and are strong predictors even at H1:

```python
# features/microstructure.py
def compute_microstructure_features(ticks_df: pd.DataFrame) -> pd.DataFrame:
    features = {}
    
    # Time between bid price changes — bid liquidity pressure
    bid_changes = ticks_df['bid'].diff().ne(0)
    features['bid_advance_time'] = ticks_df.index.to_series().diff()[bid_changes].mean()
    
    # Time between ask price changes — ask liquidity pressure
    ask_changes = ticks_df['ask'].diff().ne(0)
    features['ask_advance_time'] = ticks_df.index.to_series().diff()[ask_changes].mean()
    
    # Time of last trade — how recent was the last execution
    features['last_trade_time'] = ticks_df['last_trade_ts'].iloc[-1]
    
    # Bid/ask imbalance
    features['bid_ask_vol_ratio'] = ticks_df['bid_vol'].sum() / ticks_df['ask_vol'].sum()
    
    return pd.DataFrame([features])
```

### Genetic Algorithm for Feature Selection (from HFT-price-prediction)

Don't manually tune features. Let GA select the best combination:

```python
# features/ga_selector.py
from sklearn.feature_selection import SelectFromModel
from genetic_selection import GeneticSelectionCV

selector = GeneticSelectionCV(
    estimator=LGBMClassifier(),
    cv=5,
    verbose=1,
    scoring="accuracy",
    max_features=30,
    n_population=50,
    crossover_proba=0.5,
    mutation_proba=0.2,
    n_generations=40,
    crossover_independent_proba=0.5,
    mutation_independent_proba=0.05,
    tournament_size=3,
    n_gen_no_change=10,    # stop if no improvement for 10 generations
    caching=True
)
selector.fit(X_train, y_train)
selected_features = X_train.columns[selector.support_]
```

**Run GA selection once per quarter per symbol. Cache results.**

### TradingView MCP Bridge (from tradingview-mcp)

⚠️ Requires: TradingView Desktop + paid subscription. Undocumented internal APIs — may break.

```python
# Add to Claude Code MCP config (.claude/settings.json):
{
    "mcpServers": {
        "tradingview": {
            "command": "npx",
            "args": ["-y", "tradingview-mcp"],
            "env": {"PLAYWRIGHT_HEADLESS": "false"}
        }
    }
}
```

**Available MCP tools:**
- `chart_get_state` — current chart symbol, timeframe, visible bars
- `data_get_study_values` — RSI, MACD, Bollinger Bands, EMA values
- `quote_get` — last price + bid/ask for any symbol
- `tv stream quote` — real-time JSONL stream

**Use:** Cross-validate MT5 OHLCV data against TradingView in research/debugging sessions.

### Piotroski F-Score Filter (from staskh/trading_skills)

9-point fundamental quality filter. For PulseTrade: apply to any equity signals as pre-entry filter. Not directly applicable to pure forex, but use for SPY/QQQ macro positioning:

```python
def piotroski_score(financials: dict) -> int:
    score = 0
    # Profitability (4 points)
    score += 1 if financials['roa'] > 0 else 0
    score += 1 if financials['operating_cf'] > 0 else 0
    score += 1 if financials['roa_delta'] > 0 else 0
    score += 1 if financials['accruals'] < 0 else 0  # CF > Net Income
    # Leverage (3 points)
    score += 1 if financials['leverage_delta'] < 0 else 0
    score += 1 if financials['liquidity_delta'] > 0 else 0
    score += 1 if financials['no_new_shares'] else 0
    # Efficiency (2 points)
    score += 1 if financials['gross_margin_delta'] > 0 else 0
    score += 1 if financials['asset_turnover_delta'] > 0 else 0
    return score  # ≥7 = HIGH QUALITY, ≤2 = LOW QUALITY (avoid)
```

---

## 8. Risk Management

**Sources:** `tradermonty/claude-trading-skills`, `abdlhannan/MT5_Trade_Connector`, `staskh/trading_skills`, `HKUDS/AI-Trader`, `HKUDS/HFT-Arbitrage-EA`

### Kelly Criterion with Portfolio Constraints

Replace fixed lot size with dynamic Kelly sizing:

```python
# agents/risk_agent.py
def kelly_position_size(win_rate: float, avg_win: float, avg_loss: float,
                         portfolio_value: float, max_kelly_pct: float = 0.25) -> float:
    """
    Kelly fraction: f* = (p/q) * (b/a) where
    p = win_rate, q = 1 - win_rate
    b = avg_win, a = avg_loss
    
    Use HALF-KELLY for real trading (reduces drawdown at small cost to returns).
    """
    if avg_loss == 0:
        return 0.0
    
    kelly_fraction = (win_rate / (1 - win_rate)) * (avg_win / avg_loss)
    kelly_fraction = kelly_fraction / 2.0              # half-Kelly
    kelly_fraction = min(kelly_fraction, max_kelly_pct)  # cap at 25%
    kelly_fraction = max(kelly_fraction, 0.01)           # minimum position
    
    position_value = portfolio_value * kelly_fraction
    return position_value

# Portfolio-level constraints (from claude-trading-skills)
class PositionConstraints:
    max_per_symbol_pct: float = 0.10      # 10% max in one symbol
    max_correlated_sector_pct: float = 0.20  # 20% in correlated pairs
    max_total_exposure_pct: float = 0.50  # 50% max deployed
```

### MT5 RiskManagement Integration

From MT5_Trade_Connector:

```python
from broker.mt5_connector import RiskManagement_v1

risk = RiskManagement_v1(
    login=os.environ["MT5_LOGIN"],
    password=os.environ["MT5_PASSWORD"],
    server=os.environ["MT5_SERVER"],
    daily_limit=0.05,      # 5% max daily loss
    monthly_limit=0.10     # 10% max monthly loss
)

# Check before every trade:
if not risk.check_daily_limit():
    logger.warning("Daily loss limit reached — no new entries")
    return SignalType.HOLD
```

### Feed Freshness Guard (from HFT-Arbitrage-EA research)

MT5 data feeds can go stale without raising an error. Always validate:

```python
class FeedFreshnessGuard:
    def __init__(self, max_staleness_seconds: int = 30):
        self.max_staleness = max_staleness_seconds

    def check(self, order: Order) -> GuardResult:
        last_tick = mt5.symbol_info_tick(order.symbol)
        if last_tick is None:
            return GuardResult(passed=False, reason="No tick data available")
        
        staleness = time.time() - last_tick.time
        if staleness > self.max_staleness:
            return GuardResult(passed=False,
                               reason=f"Feed stale: {staleness:.0f}s > {self.max_staleness}s")
        return GuardResult(passed=True)
```

### Delta-Adjusted Notional Exposure

From staskh/trading_skills — display portfolio exposure in meaningful terms:

```python
def compute_exposure(positions: list[Position]) -> dict:
    """
    For forex: exposure = lots * contract_size * current_price
    Display: grouped by currency, not by pair
    """
    exposure = {
        "total_notional_usd": sum(p.lots * p.contract_size * p.price 
                                   for p in positions),
        "usd_exposure": ...,   # net USD position across all pairs
        "eur_exposure": ...,   # net EUR position
        "by_pair": {p.symbol: p.notional for p in positions}
    }
    return exposure
```

---

## 9. SKILL.md + MCP Dual Interface Architecture

**Sources:** `tradermonty/claude-trading-skills` (655 stars), `staskh/trading_skills` (77 stars), `HKUDS/AI-Trader` (12.2k stars)

### Expose Bot Capabilities as SKILL.md

Every PulseTrade capability should be registered as a Claude-readable SKILL.md:

```
.claude/skills/
├── trading-bot-overview.md        ← existing
├── implement-agent.md             ← existing
├── add-strategy.md                ← existing
├── trade-execution.md             ← existing
├── learning-system.md             ← existing
├── configure-infra.md             ← existing
├── coding-standards.md            ← existing
├── prompt-guide.md                ← existing
│
├── intelligence-sweep.md          ← NEW: IntelligenceSweep API
├── signal-quality-gates.md        ← NEW: ExposureCoach + FTD + Postmortem
├── model-evaluation.md            ← NEW: How to benchmark LSTM variants
├── backtest-standards.md          ← NEW: SQN, walk-forward, commission requirements
└── feature-engineering.md        ← NEW: WorldQuant alphas, Kalman, microstructure
```

**SKILL.md format** (each file):

```markdown
# [Skill Name]

## When to use
[Trigger conditions]

## Key files
[File paths and their role]

## API surface
[Key functions, class names, parameters]

## Examples
[Concrete code examples]

## Anti-patterns
[What NOT to do]
```

### Dual Interface: SKILL.md + FastMCP Server (from staskh/trading_skills)

Expose the same bot functions simultaneously as Claude skills AND as a FastMCP server. This lets Claude Code *directly call bot functions* during development/debugging:

```python
# tools/mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP("PulseTrade Trading Tools")

@mcp.tool()
async def get_portfolio_snapshot() -> dict:
    """Get current open positions, P&L, and exposure."""
    return await portfolio_service.snapshot()

@mcp.tool()
async def run_intelligence_sweep() -> dict:
    """Trigger a manual intelligence sweep across all 27 sources."""
    return await IntelligenceSweep().run_all_sources()

@mcp.tool()
async def backtest_strategy(symbol: str, days: int = 90) -> dict:
    """Run walk-forward backtest on a strategy for the given symbol."""
    return await BacktestEngine().run(symbol, days)

@mcp.tool()
async def get_signal_postmortems(n: int = 20) -> list[dict]:
    """Get the last N trade postmortems with classification."""
    return await db.fetch_postmortems(n)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Claude Code config:**

```json
// .claude/settings.json
{
    "mcpServers": {
        "PulseTrade": {
            "command": "python",
            "args": ["tools/mcp_server.py"],
            "env": { "PYTHONPATH": "." }
        }
    }
}
```

**Result:** Claude Code can call `get_portfolio_snapshot()`, `run_intelligence_sweep()` etc. directly during development sessions. Same functions also serve the dashboard API.

### Signal as Structured Event (from AI-Trader)

Every trading signal is a typed DB record, not just a buy/sell flag:

```sql
CREATE TABLE signals (
    id              SERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(20) NOT NULL,
    signal_type     VARCHAR(20) NOT NULL,  -- 'STRATEGY', 'NEURAL', 'COUNCIL'
    direction       VARCHAR(10),            -- 'BUY', 'SELL', 'HOLD'
    confidence      DECIMAL(5,4),
    sources         JSONB,                  -- which agents contributed
    reasoning       TEXT,                   -- council explanation
    metadata        JSONB,                  -- SHAP values, indicator values
    trade_id        INTEGER REFERENCES trade_commits(id),
    postmortem      VARCHAR(30)             -- filled after trade closes
);
```

---

## Implementation Priority Matrix

### P0 — Implement Immediately (high impact, low risk)

| # | Action | Source | Effort |
|---|--------|--------|--------|
| 1 | Rename Settings "Crucix Intelligence" card → "Intelligence Suite" | Crucix removal | 15 min |
| 2 | `GuardPipeline` pre-execution safety layer in execution_agent | OpenAlice | 1 day |
| 3 | Add `commission=0.0001` to ALL backtest configs | tensortrade research | 1h |
| 4 | `FeedFreshnessGuard` — validate MT5 data timestamp before trading | HFT-Arbitrage-EA | 2h |
| 5 | 3-class output (up/unchanged/down) in neural_strategy | huseinzol05 | 1 day |
| 6 | Trade commit hash (`trade_commits` table) — audit trail | OpenAlice | 1 day |
| 7 | `IntelligenceSweep` skeleton class with `asyncio.gather()` | Crucix | 2 days |
| 8 | FRED API — 22 macro indicators as LSTM features | Crucix/ML4Trading | 1 day |

### P1 — Next Sprint (meaningful upgrade, moderate effort)

| # | Action | Source | Effort |
|---|--------|--------|--------|
| 9 | Kalman filter for price denoising before LSTM | ML4Trading Ch4 | 1 day |
| 10 | GARCH volatility regime gate | ML4Trading Ch9 | 1 day |
| 11 | SHAP feature explainability layer | ML4Trading Ch12 | 1 day |
| 12 | Dilated-CNN-Seq2seq benchmark on EURUSD H1 | huseinzol05 | 2 days |
| 13 | `ExposureCoach` gate — market breadth before entries | claude-trading-skills | 1 day |
| 14 | `SignalPostmortem` classification for every closed trade | claude-trading-skills | 1 day |
| 15 | `trader-memory-core` PostgreSQL table (MAE/MFE tracking) | claude-trading-skills | 0.5 days |
| 16 | `EventLog` append-only JSONL bus | OpenAlice | 0.5 days |
| 17 | `HeartbeatProtocol` — contact human only on CHAT_YES | OpenAlice | 0.5 days |
| 18 | Walk-Forward Optimization in backtesting engine | Lean/tensortrade | 2 days |
| 19 | LightGBM + LSTM ensemble vote (agree=high confidence) | huseinzol05 | 2 days |
| 20 | Telegram two-way commands (`/brief`, `/sweep`, `/mute`) | Crucix | 1 day |
| 21 | OpenRouter as LLM fallback gateway | GODMOD3 | 0.5 days |

### P2 — Future Improvements (research/experiment)

| # | Action | Source | Notes |
|---|--------|--------|-------|
| 22 | LangGraph multi-specialist debate pipeline | TradingAgents | Major refactor |
| 23 | TradingView MCP bridge for live indicator validation | tradingview-mcp | Requires TV Desktop |
| 24 | TimeGAN synthetic data for scarce-data symbols | ML4Trading Ch21 | Research phase |
| 25 | WorldQuant 101 Formulaic Alphas as feature set | ML4Trading Ch24 | Feature engineering |
| 26 | Genetic Algorithm feature selection | HFT-price-prediction | Quarterly run |
| 27 | GDELT global news event scoring | Crucix | Needs eval on forex |
| 28 | Kelly Criterion position sizing (replace fixed lots) | claude-trading-skills | Requires win-rate history |
| 29 | `AutoCompaction` for 24/7 agent context management | OpenAlice | When running 24/7 |
| 30 | `Evolution Mode` tiers (sandbox / review / admin) | OpenAlice | Advanced feature |
| 31 | FastMCP server exposing bot functions to Claude Code | trading_skills | DX upgrade |
| 32 | SKILL.md for all new capabilities | tradermonty | Ongoing |

---

## Quick Reference: Library Inventory

```bash
# Install all new dependencies from research
pip install fredapi          # FRED API — macro indicators
pip install yfinance         # Yahoo Finance — market data (no key)
pip install arch             # GARCH volatility models
pip install pykalman         # Kalman filter
pip install shap             # SHAP explainability
pip install lightgbm         # LightGBM ensemble
pip install langgraph        # LangGraph agent state machine
pip install fastmcp          # FastMCP server for tool exposure
pip install backtrader       # Backtesting with SQN analyzer
pip install praw             # Reddit API
pip install polygon-api-client  # Polygon.io options flow
# pip install ydata-sdk      # TimeGAN — install only if needed (heavy)
```

---

## Source Quality Index

| Repository | Stars | Activity | Quality | Primary Value |
|-----------|-------|----------|---------|---------------|
| TauricResearch/TradingAgents | 47.4k | Yesterday | ⭐⭐⭐⭐⭐ | Agent pipeline architecture |
| stefan-jansen/ML-for-Trading | 17k | 3y ago | ⭐⭐⭐⭐⭐ | ML techniques + research base |
| mementum/backtrader | 21k | 3y ago | ⭐⭐⭐⭐⭐ | Backtesting standard + SQN |
| QuantConnect/Lean | 18.3k | Active | ⭐⭐⭐⭐⭐ | 4-layer framework + walk-forward |
| TraderAlice/OpenAlice | 3.1k | 10h ago | ⭐⭐⭐⭐⭐ | Architecture patterns (built w/ Claude) |
| tradermonty/claude-trading-skills | 655 | 16h ago | ⭐⭐⭐⭐⭐ | Signal quality gates + SKILL.md |
| calesthio/Crucix | 8.5k | Active | ⭐⭐⭐⭐⭐ | Intelligence sweep architecture |
| HKUDS/AI-Trader | 12.2k | Active | ⭐⭐⭐⭐ | Signal typing + SKILL.md |
| huseinzol05/Stock-Prediction-Models | 9.3k | Archived | ⭐⭐⭐⭐ | Model benchmarks |
| tensortrade-org/tensortrade | 6.1k | 2mo ago | ⭐⭐⭐⭐ | Commission insight + RL env |
| hzjken/HFT-price-prediction | 181 | - | ⭐⭐⭐⭐ | Microstructure features + GA |
| staskh/trading_skills | 77 | 3d ago | ⭐⭐⭐⭐ | Dual SKILL.md + MCP pattern |
| tradingview-mcp | 1.1k | 2d ago | ⭐⭐⭐ | TV indicator access (fragile) |
| abdlhannan/MT5_Trade_Connector | 14 | - | ⭐⭐⭐⭐ | MT5 API patterns |
| MSL135/GODMOD3 | 88 | - | ⭐⭐⭐ | OpenRouter + committee vote |
| Yvictor/TradingGym | 1.9k | Archived | ⭐⭐⭐ | RL env fee parameter |
