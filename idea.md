# NeuralFX — Research Landscape & Feature Roadmap

> Compiled from analysis of 40 open-source repositories across trading AI, backtesting,
> ML finance, and Claude/MCP ecosystems. Every idea maps to at least one real implementation.

---

## Table of Contents

1. [Repository Catalogue](#1-repository-catalogue)
2. [Priority Feature Matrix](#2-priority-feature-matrix)
3. [Feature Designs — Tier 1 (High Value, Feasible)](#3-feature-designs--tier-1)
4. [Feature Designs — Tier 2 (Medium Effort)](#4-feature-designs--tier-2)
5. [Feature Designs — Tier 3 (Long-term)](#5-feature-designs--tier-3)
6. [Implementation Order Recommendation](#6-implementation-order-recommendation)

---

## 1. Repository Catalogue

### 1.1 Claude / MCP / Skill Ecosystem

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 1 | `tradermonty/claude-trading-skills` | 662 | Exposure Coach (0–100% exposure ceiling), Trader Memory Core (thesis lifecycle IDEA→ENTRY_READY→ACTIVE→CLOSED), Edge Pipeline (Candidate→Designer→Reviewer→Orchestrator→Aggregator), skill self-improvement loop (auto-scores, auto-fixes, auto-PR) |
| 2 | `tradesdontlie/tradingview-mcp` | 1.1k | 78 MCP tools: `chart_get_state`, `data_get_ohlcv`, `pine_smart_compile`, `replay_start`, `batch_run`, `tv stream`; CDP-based automation of TradingView Desktop on port 9222 |
| 3 | `staskh/trading_skills` | 77 | 24 MCP tools: `whale-hunting` (institutional options flow via Massive/Polygon.io), `ib-find-short-roll`, `ib-collar`, Black-Scholes greeks, VaR/Sharpe/drawdown risk assessment |
| 4 | `letta-ai/claude-subconscious` | 2.6k | 8 persistent memory blocks; hooks: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`; background Letta agent with tool-use memory that survives session resets |
| 5 | `anthropics/claude-code` | 109k | Official Claude Code CLI; slash-command system, CLAUDE.md, permission model, custom tools |
| 6 | `affaan-m/everything-claude-code` | 140k | Optimization guide: compact contexts, parallel subagents, CLAUDE.md memory architecture, slash commands for workflows |
| 7 | `shareAI-lab/learn-claude-code` | 48.6k | Harness engineering; prompt scaffolding; system prompt injection patterns; multi-file context loading |
| 8 | `ultraworkers/claw-code` | 171k | Rust CLI agent harness; multi-session management; workspace isolation |

---

### 1.2 Multi-Agent & Orchestration Frameworks

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 9 | `TauricResearch/TradingAgents` | **47.4k** | Multi-agent debate framework on LangGraph: Fundamentals+Sentiment+News+Technical analysts produce reports → Bull Researcher and Bear Researcher debate → Trader Agent synthesizes → Risk Management gating. Supports GPT/Gemini/Claude/Grok/Ollama. |
| 10 | `HKUDS/AI-Trader` | 12.2k | Agent swarm marketplace; copy trading; strategy publishing; multi-market. "Best trader" routing per symbol. |
| 11 | `TraderAlice/OpenAlice` | 3.1k | "Trading-as-Git": stage→commit→push paradigm; guard pipeline (position size limit, cooldown, whitelist, max open positions); cognitive brain with persistent memory+emotion state; CCXT/Alpaca/IBKR connectors |

---

### 1.3 Backtesting Infrastructure

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 12 | `mementum/backtrader` | **21k** | 122 built-in indicators; Sharpe/SQN analyzers; commission/slippage models; supports live trading (IB/Oanda); cerebro architecture; analyzers produce structured metrics |
| 13 | `quantopian/zipline` | 19.6k | *(archived)* — event-driven; `zipline ingest` + `zipline run`; PyData integration; methodology reference only. Active fork: `zipline-reloaded` |
| 14 | `Yvictor/TradingGym` | 1.9k | OpenAI Gym-compatible RL trading environment for tick data; observation space = OHLCV window + position state |
| 15 | `tensortrade-org/tensortrade` | 6.1k | PPO on BTC/USD; composable `ActionScheme`/`RewardScheme`; walk-forward validation; portfolio management with multiple instruments |
| 16 | `askmike/gekko` | 10.2k | *(archived)* — Bitcoin TA bot in Node.js; historically significant strategy plugin pattern |

---

### 1.4 ML Finance — Books & Research Code

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 17 | `stefan-jansen/machine-learning-for-trading` | **17k** | Ch.12: LightGBM/XGBoost intraday with SHAP feature importance → directly applicable to our LGBM models; Ch.09: ARCH+cointegration pairs trading; Ch.19: LSTM/GRU multivariate; Ch.21: Autoencoders for factor discovery; Ch.22: TimeGAN synthetic training data; Ch.23: Deep RL trading agent (OpenAI Gym) |
| 18 | `huseinzol05/Stock-Prediction-Models` | 9.3k | *(archived 2023)* — 18 DL models: **Dilated-CNN-Seq2seq 95.86%** (best), LSTM 95.69%; 23 RL agents (Double Duel Q, Actor-Critic, Curiosity Q, Neuro-evolution); stacking: Autoencoder+LSTM+ARIMA+XGB |
| 19 | `grananqvist/Awesome-Quant-ML-Trading` | 3.5k | Curated: López de Prado "Advances in Financial ML", mlfinlab (feature engineering), PGPortfolio (deep RL portfolio), de Prado "10 Reasons ML Funds Fail" |
| 20 | `hzjken/HFT-price-prediction` | *(small)* | LightGBM + Random Forest for HFT; 76–78% directional accuracy; feature key: order book imbalance |
| 21 | `stavros0/bitcoin-price-prediction` | *(small, archived)* | Bayesian regression for BTC; uncertainty quantification via posterior predictive |

---

### 1.5 MT5 / Broker Integration

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 22 | `abdlhannan/MT5_Trade_Connector` | 14 | **Daily loss limit 5% / monthly loss limit 10%** enforcement; trailing stop with thread-safe locking; multi-timeframe M1→D1; position sizing by account equity % |
| 23 | `HFTHaidra/HFT-Arbitrage-EA-MQL4-MQL5` | 110 | Two-broker arbitrage: fast feed vs. slow broker; latency-based entry; spread comparison per tick |
| 24 | `EarnForex/Point-and-Figure` | 7 | MT5 P&F chart indicator; box size auto-calculation from ATR; intraday/daily modes |

---

### 1.6 Market Data & TradingView

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 25 | `Mathieu2301/TradingView-API` | 2.9k | Node.js real-time TradingView socket: prices, indicator values, screener top values, hotlists, invite-only indicators, backtesting API |
| 26 | `koreainvestment/open-trading-api` | *(institutional)* | Korea Investment open brokerage API with LLM support; KIS API reference for regulated brokerage patterns |

---

### 1.7 Exchange & Portfolio Libraries

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 27 | `knowm/XChange` | *(Java, large)* | Unified Java interface for 60+ crypto exchanges; order book, trades, account data; candle OHLCV streaming |
| 28 | `Superalgos/Superalgos` | *(large)* | Visual strategy designer (node graph); community-shared strategies; slippage simulation; multi-exchange crypto |

---

### 1.8 Specialized Tools

| # | Repo | Stars | Key Takeaway for NeuralFX |
|---|---|---|---|
| 29 | `tiero/claw-cash` | *(small)* | Bitcoin wallet primitives for AI agent payment flows; PSBT signing |
| 30 | `MSL135/GODMOD3` | *(small)* | AI red-teaming; not relevant to NeuralFX |
| 31 | `public-apis/public-apis` | *(large)* | Directory of free APIs: Alpha Vantage (financial), Quandl, Polygon.io, CoinGecko, OpenFIGI |

---

## 2. Priority Feature Matrix

Scored on: **Impact** (how much it improves P&L or risk), **Effort** (dev days), **Risk** (chance of breaking existing pipeline).

| Feature | Source Inspiration | Impact | Effort | Risk | Tier |
|---|---|---|---|---|---|
| Daily/Monthly Loss Limit Guard | MT5_Trade_Connector | ★★★★★ | 1d | Low | **1** |
| Walk-Forward Backtesting Engine | backtrader + tensortrade | ★★★★★ | 3d | Low | **1** |
| SHAP Feature Importance on LGBM | ML4T Ch.12 | ★★★★ | 0.5d | Low | **1** |
| Bull/Bear Debate Agent | TradingAgents | ★★★★ | 2d | Medium | **1** |
| Trader Memory Core (thesis lifecycle) | claude-trading-skills | ★★★★ | 2d | Low | **1** |
| Exposure Coach | claude-trading-skills | ★★★ | 1d | Low | **2** |
| RL Agent (PPO) on live data | tensortrade / TradingGym | ★★★★ | 5d | High | **2** |
| Dilated-CNN-Seq2seq model | Stock-Prediction-Models | ★★★ | 3d | Medium | **2** |
| Synthetic training data (TimeGAN) | ML4T Ch.22 | ★★★ | 4d | Medium | **2** |
| Walk-forward optimization loop | backtrader + zipline-reloaded | ★★★★ | 4d | Medium | **2** |
| Persistent memory (Letta-style) | claude-subconscious | ★★★ | 2d | Low | **2** |
| GARCH-X (exogenous) extension | ML4T Ch.09 | ★★ | 1d | Low | **2** |
| TradingView MCP integration | tradingview-mcp | ★★★ | 3d | Medium | **3** |
| Institutional whale flow detection | staskh/trading_skills | ★★★ | 2d | Medium | **3** |
| Copy-trading signal publisher | AI-Trader | ★★ | 5d | High | **3** |
| Multi-broker arbitrage | HFT-Arbitrage-EA | ★★ | 5d | High | **3** |

---

## 3. Feature Designs — Tier 1

### 3.1 Daily / Monthly Loss Limit Guard

**Source:** `abdlhannan/MT5_Trade_Connector`

**What it does:** Before any execution, check if today's realized P&L loss exceeds 5% of equity or the month's loss exceeds 10%. If so, block all new trades and optionally close all open positions.

**Integration point:** `agents/risk_agent.py → RiskAgent.check()` — add a `_check_drawdown_limits()` call before the position-size gate.

**Implementation sketch:**

```python
# agents/risk_agent.py addition

DAILY_LOSS_LIMIT_PCT  = 0.05   # 5%
MONTHLY_LOSS_LIMIT_PCT = 0.10  # 10%

def _check_drawdown_limits(self, account_equity: float) -> tuple[bool, str]:
    """Returns (allowed, reason). Queries closed trades from DB."""
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    
    daily_pnl   = self.db.get_closed_pnl_since(today)
    monthly_pnl = self.db.get_closed_pnl_since(month_start)
    
    daily_loss_pct   = abs(min(daily_pnl, 0))   / account_equity
    monthly_loss_pct = abs(min(monthly_pnl, 0)) / account_equity
    
    if daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
        return False, f"Daily loss limit hit ({daily_loss_pct:.1%})"
    if monthly_loss_pct >= MONTHLY_LOSS_LIMIT_PCT:
        return False, f"Monthly loss limit hit ({monthly_loss_pct:.1%})"
    return True, "OK"
```

**DB query needed:** `SELECT SUM(pnl) FROM trades WHERE closed_at >= %s AND pnl IS NOT NULL`

**Time estimate:** ~4 hours including DB method + test.

---

### 3.2 Walk-Forward Backtesting Engine

**Source:** `mementum/backtrader` + `tensortrade`

**What it does:** Splits historical H1 data into rolling windows (e.g., 6-month train / 1-month test). Runs the full signal pipeline (ICT → LSTM → LGBM) on each test window. Reports Sharpe, max drawdown, win rate, and expectancy per window and in aggregate.

**Why it matters:** Exposes overfitting. If Sharpe degrades consistently in later walk-forward periods, the model is curve-fit to early data.

**Architecture:**

```
backtesting/
  engine.py        ← main WF loop (already exists as stub)
  walk_forward.py  ← NEW: rolling-window orchestrator
  metrics.py       ← NEW: Sharpe, SQN, drawdown, expectancy
  report.py        ← already exists; extend with WF summary
```

**Walk-forward core:**

```python
# backtesting/walk_forward.py

def walk_forward(symbol: str, train_months: int = 6, test_months: int = 1):
    """Yield (train_df, test_df) sliding windows."""
    full_df = load_h1_history(symbol, years=2)
    periods = split_walk_forward(full_df, train_months, test_months)
    
    results = []
    for train_df, test_df in periods:
        model = train_lgbm_on(train_df)       # retrain price LGBM
        signals = run_signal_pipeline(test_df, model)
        pnl_series = simulate_trades(signals, test_df)
        results.append(compute_metrics(pnl_series))
    
    return aggregate_wf_results(results)
```

**Metrics to compute:** Sharpe ratio, Sortino ratio, max drawdown %, total return, win rate, profit factor, SQN (System Quality Number).

**Time estimate:** ~3 days.

---

### 3.3 SHAP Feature Importance on LGBM Models

**Source:** `stefan-jansen/machine-learning-for-trading` Ch.12

**What it does:** After training either LGBM model, compute SHAP values to rank which features drive predictions. Logs top-5 features to the dashboard agent feed so the trader understands what the model is looking at.

**Implementation:**

```python
# models/lgbm_price_model.py — add after .fit()

import shap

def compute_shap_importance(model, X_train: pd.DataFrame) -> dict:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_train)
    mean_abs = np.abs(shap_values).mean(axis=0)
    ranked = sorted(zip(X_train.columns, mean_abs), key=lambda x: -x[1])
    return {feat: float(imp) for feat, imp in ranked[:5]}
```

**Output:** Log to `agent_events` with `event_key='model_manager'` and `data={'shap_top5': {...}}` so the dashboard Agent Feed card shows it.

**Time estimate:** ~2 hours (shap is already a transitive dependency of lightgbm).

---

### 3.4 Bull / Bear Debate Agent

**Source:** `TauricResearch/TradingAgents` (47.4k stars)

**What it does:** Before the `CouncilAgent` votes, a `BullAgent` and `BearAgent` independently write a 3-point case for and against taking the trade. The `CouncilAgent` then synthesizes both cases in its prompt, producing more adversarial reasoning.

**Why it matters:** The current `CouncilAgent` is a panel of 4 independent experts that don't challenge each other. Adding a structured debate forces the model to surface the strongest counterargument before confirming a trade.

**Architecture change:**

```
Current:  StrategyAgent → CouncilAgent → RiskAgent
Proposed: StrategyAgent → BullBearDebate → CouncilAgent → RiskAgent
```

**Implementation sketch:**

```python
# agents/council_agent.py — add debate step

BULL_SYSTEM = """You are a bullish trading analyst. Given this signal context, 
write exactly 3 strong arguments FOR taking this trade. Be specific about 
price levels, RR ratio, and confluence factors. Format: 1. ... 2. ... 3. ..."""

BEAR_SYSTEM = """You are a bearish trading analyst. Given this signal context, 
write exactly 3 strong arguments AGAINST taking this trade. Focus on 
invalidation levels, adverse conditions, and risk factors. Format: 1. ... 2. ... 3. ..."""

async def _run_debate(self, signal_context: str) -> tuple[str, str]:
    bull_args = await self._call_llm(BULL_SYSTEM, signal_context)
    bear_args = await self._call_llm(BEAR_SYSTEM, signal_context)
    return bull_args, bear_args
```

The debate output is then prepended to the existing council prompt:

```
=== BULL CASE ===
{bull_args}

=== BEAR CASE ===
{bear_args}

=== COUNCIL VOTE ===
Given the above debate, each council member now casts their vote...
```

**Time estimate:** ~2 days (council prompt engineering + test coverage).

---

### 3.5 Trader Memory Core — Trade Thesis Lifecycle

**Source:** `tradermonty/claude-trading-skills`

**What it does:** Every signal that passes the full pipeline generates a structured "thesis" document: entry rationale, invalidation level, target, actual outcome (win/loss/scratch), and post-trade notes. These persist across sessions. The LGBM models can be fine-tuned against them.

**Thesis lifecycle:**

```
IDEA → ENTRY_READY → ACTIVE → [CLOSED_WIN | CLOSED_LOSS | CLOSED_SCRATCH]
```

**Storage:** New `trade_theses` table in PostgreSQL:

```sql
CREATE TABLE trade_theses (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    direction   VARCHAR(5),
    stage       VARCHAR(20) DEFAULT 'IDEA',
    entry_price DECIMAL(10,5),
    sl_price    DECIMAL(10,5),
    tp_price    DECIMAL(10,5),
    rr_ratio    DECIMAL(5,2),
    bull_case   TEXT,
    bear_case   TEXT,
    entry_reason TEXT,
    actual_outcome VARCHAR(20),
    mae_pips    DECIMAL(8,1),
    mfe_pips    DECIMAL(8,1),
    notes       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    closed_at   TIMESTAMPTZ
);
```

**Integration:** `ExecutionAgent` writes IDEA→ENTRY_READY→ACTIVE on open; `TradeManager` writes CLOSED_* + MAE/MFE on close.

**Value:** After 100+ theses, the `bull_case`/`bear_case` fields become a searchable trade journal that the LGBM training can reference. Also surfaces to the dashboard's Trades page.

**Time estimate:** ~2 days (migration + agent wiring + dashboard query).

---

## 4. Feature Designs — Tier 2

### 4.1 Exposure Coach

**Source:** `tradermonty/claude-trading-skills` — Exposure Coach skill

**What it does:** Before executing a trade, synthesize 8 upstream signals into a single exposure ceiling (0–100%) and issue one of three directives:
- `NEW_ENTRY_ALLOWED` — full position sizing applies
- `REDUCE_ONLY` — reduce existing positions; no new entries
- `CASH_PRIORITY` — close everything and hold cash

**The 8 signals:**
1. Current realized P&L vs. daily/monthly limit
2. Open position count vs. max_positions limit
3. Current GARCH volatility vs. 30-day rolling average
4. Crucix macro score (VIX, yield curve, regime)
5. Correlation of proposed trade to existing positions
6. Hour-of-day liquidity score (session filter)
7. Recent win rate (last 10 closed trades)
8. LGBM confidence score on current signal

**Output:** A single `ExposureDecision` dataclass that flows into `RiskAgent` before lot sizing.

```python
@dataclass
class ExposureDecision:
    directive: Literal["NEW_ENTRY_ALLOWED", "REDUCE_ONLY", "CASH_PRIORITY"]
    exposure_ceiling_pct: float          # 0.0 → 1.0
    reason: str
    contributing_signals: dict[str, float]
```

**Time estimate:** ~1 day.

---

### 4.2 Reinforcement Learning Agent (PPO)

**Source:** `tensortrade-org/tensortrade` + `Yvictor/TradingGym`

**What it does:** Train a PPO agent on H1 OHLCV data using a Gym-compatible environment. The RL agent outputs {BUY, SELL, HOLD} and operates in parallel with the existing rule-based pipeline. It only overrides the LSTM/ICT signal if its confidence significantly exceeds threshold.

**Environment design:**

```python
# rl/trading_env.py
class MT5TradingEnv(gym.Env):
    observation_space = gym.spaces.Box(
        low=-np.inf, high=np.inf,
        shape=(60, 7),   # 60 H1 candles × [O,H,L,C,V, RSI, MACD]
        dtype=np.float32
    )
    action_space = gym.spaces.Discrete(3)   # 0=HOLD, 1=BUY, 2=SELL

    def step(self, action):
        ...
        reward = self._compute_reward()    # Sharpe-adjusted PnL delta
        return obs, reward, done, info
```

**Integration:** PPO agent runs as a 13th agent (`rl_agent.py`) that adds a vote to the `CouncilAgent` panel.

**Time estimate:** ~5 days (environment + training + integration + test).

---

### 4.3 Dilated-CNN Feature Extractor

**Source:** `huseinzol05/Stock-Prediction-Models` — Dilated-CNN-Seq2seq achieved **95.86%** accuracy (best of 18 models)

**What it does:** Replace (or augment) the LSTM's embedding layer with a Dilated Causal Convolution block. Dilated CNNs capture multi-scale temporal patterns (short + long lag dependencies) more efficiently than LSTMs for 1D time series.

**Architecture change:**

```
Current:  LSTM(128) → LSTM(64) → Dense(1)
Proposed: DilatedConv(rates=[1,2,4,8]) → LSTM(64) → Dense(1)
```

**PyTorch implementation:**

```python
class DilatedTemporalBlock(nn.Module):
    def __init__(self, channels: int, rates: list[int]):
        super().__init__()
        self.convs = nn.ModuleList([
            nn.Conv1d(channels, channels, kernel_size=3,
                      dilation=r, padding=r)
            for r in rates
        ])
    
    def forward(self, x):
        outs = [F.relu(conv(x)) for conv in self.convs]
        return torch.stack(outs).mean(0)   # or sum
```

**Time estimate:** ~3 days (architecture change + retrain eval + regression test).

---

### 4.4 Synthetic Training Data via TimeGAN

**Source:** `stefan-jansen/machine-learning-for-trading` Ch.22

**What it does:** Use TimeGAN (Generative Adversarial Network for time series) to synthesize additional OHLCV training samples for rare market conditions (high volatility, flash crashes, trend reversals). Augments the 2-year H1 dataset to improve LSTM generalization.

**Why it matters:** NeuralFX currently trains on **~1,750 H1 candles per symbol** (2 years). TimeGAN can expand this to 10,000+ statistically consistent samples without look-ahead bias.

**Time estimate:** ~4 days (GAN training is slow; GPU recommended).

---

### 4.5 Persistent Agent Memory (Letta-style)

**Source:** `letta-ai/claude-subconscious`

**What it does:** Give the bot persistent cross-session memory in the form of 8 labeled memory blocks stored in PostgreSQL:

| Block Name | Content |
|---|---|
| `session_context` | Last bot start time, symbols active, current regime |
| `trade_history_summary` | Last 20 trades: symbol, direction, outcome, lesson |
| `model_performance` | LSTM/LGBM accuracy metrics rolling 30 days |
| `market_regime` | Current macro regime from Crucix (risk-on/off, VIX level) |
| `user_preferences` | Risk tolerance, preferred pairs, blacklisted symbols |
| `strategy_notes` | Manual notes from the dashboard command panel |
| `incident_log` | Any broker errors, slippage events, failed executions |
| `performance_journal` | Weekly returns, Sharpe, drawdown, equity milestones |

**Storage:** `bot_memory` table with `(block_name, content TEXT, updated_at)`.

**Integration:** `LoggingAgent` updates relevant blocks after each loop. `CrucixAgent` reads `market_regime` on startup to skip a full macro refresh if the regime hasn't changed.

**Time estimate:** ~2 days.

---

### 4.6 GARCH-X Extension (Exogenous Inputs)

**Source:** `stefan-jansen/machine-learning-for-trading` Ch.09 — ARCH models

**What it does:** Extend the existing `GARCH(1,1)` model in `AnalysisAgent` to `GARCH-X`, where the `X` term is an exogenous variable such as:
- VIX level from Crucix macro feed
- Realized variance from the previous session (Asia/London/NY)
- News activity count from Crucix OSINT feed

**Why it matters:** Pure `GARCH(1,1)` forecasts variance only from its own lag. Adding exogenous inputs gives the model a 5–15 minute lead time before volatility spikes affect prices.

**Implementation:** Replace `arch.univariate.GARCH` with `arch.univariate.GARCH` + `x` parameter:

```python
from arch import arch_model

model = arch_model(
    returns,
    vol='Garch', p=1, q=1,
    x=exog_matrix    # shape (T, k) — VIX, news_count, session_var
)
```

**Time estimate:** ~1 day.

---

## 5. Feature Designs — Tier 3

### 5.1 TradingView MCP Integration

**Source:** `tradesdontlie/tradingview-mcp` (1.1k stars, 78 tools)

**What it does:** Connect NeuralFX to TradingView Desktop via Chrome DevTools Protocol (port 9222). Enables:
- Screenshot trading setups to the dashboard
- Fetch Pine Script indicator values in real time (as a second data source)
- Auto-draw S/R levels, order blocks, FVGs on the chart
- Batch-run Pine strategies and compare results to our LSTM

**Constraint:** Requires TradingView paid subscription; may violate TradingView ToS for automation. Use for development/research only.

**Time estimate:** ~3 days (Node.js subprocess integration from Python).

---

### 5.2 Institutional Whale Flow Detection

**Source:** `staskh/trading_skills` — `whale-hunting` skill

**What it does:** Connect to Polygon.io or Unusual Whales API to monitor real-time options flow for large institutional positions. If a whale buys deep OTM calls/puts on a forex ETF (EUO, FXE, UUP), treat it as a directional signal for the underlying pair.

**API:** `https://api.polygon.io/v2/last/trade/{optionsTicker}` (requires paid tier ~$29/mo).

**Integration:** New `filters/whale_filter.py` that the `AnalysisAgent` queries. If a strong whale signal aligns with the LSTM direction, boost confidence by 10%. If it contradicts, reduce confidence by 15%.

**Time estimate:** ~2 days.

---

### 5.3 Copy-Trading Signal Publisher

**Source:** `HKUDS/AI-Trader` (12.2k stars)

**What it does:** After each trade closes, publish the signal (symbol, direction, entry, SL, TP, confidence, outcome) to a public REST endpoint so other traders can subscribe. Enables:
- Signal subscription marketplace
- Track record building
- Community backtesting against your signals

**Architecture:** FastAPI endpoint in a new `api/` directory that reads the `trades` table and serves signals as a JSON feed.

**Time estimate:** ~5 days (FastAPI + authentication + subscriber management).

---

## 6. Implementation Order Recommendation

Based on impact-to-effort ratio and zero risk of breaking the existing pipeline:

### Sprint 1 — Risk & Observability (Week 1)
1. **Daily/Monthly Loss Limit Guard** (4h) — highest safety value
2. **SHAP Feature Importance** (2h) — zero risk, immediate insight
3. **Trader Memory Core — DB schema only** (4h) — enables #4 below

### Sprint 2 — Analytical Depth (Week 2)
4. **Bull/Bear Debate Agent** (2d) — improves council reasoning
5. **Exposure Coach** (1d) — synthesizes risk signals before each trade
6. **Persistent Agent Memory** (2d) — cross-session learning

### Sprint 3 — Backtesting (Week 3)
7. **Walk-Forward Backtesting Engine** (3d) — validates model robustness
8. **Metrics module** (0.5d) — Sharpe, SQN, drawdown, profit factor

### Sprint 4 — ML Improvements (Week 4)
9. **GARCH-X Extension** (1d) — exogenous volatility inputs
10. **Dilated-CNN Feature Extractor** (3d) — potential LSTM accuracy boost

### Sprint 5 — Long-term (Month 2+)
11. RL Agent (PPO) — 5 days
12. TimeGAN synthetic data — 4 days
13. TradingView MCP — 3 days
14. Whale flow detection — 2 days
15. Copy-trading publisher — 5 days

---

## Notes on What NOT to Build

Based on the research, several repo patterns are explicitly **not appropriate** for NeuralFX:

| Pattern | Why Skip |
|---|---|
| Multi-exchange crypto arbitrage (HFT-Arbitrage-EA) | NeuralFX is MT5/forex-only; HFT latency not achievable via Python |
| P&F chart indicator (EarnForex) | NeuralFX uses H1 OHLCV natively; P&F adds no signal value |
| Zipline backtesting | Archived, Python 2.7 — use backtrader instead |
| Gekko patterns | Archived, Node.js, crypto-only |
| Bitcoin wallet / PSBT (claw-cash) | Irrelevant — not a crypto custody product |
| Multi-broker copy trading marketplace (AI-Trader) | Far outside current scope; would require infrastructure rebuild |

---

*Last updated: based on 40-repo landscape analysis across trading AI, Claude/MCP, ML finance, and backtesting ecosystems.*
