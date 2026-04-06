# PulseTrade TradingBot — Full Repo Research (42 Repos)
> Compiled April 2026. Covers all repos from the original list. Cross-references existing `REPO_LEARNINGS.md` and `idea.md` to avoid duplication. Only new findings or gaps are marked **NEW**. Previously covered items are summarised for completeness with a ✅ tag.

---

## Full Repository Analysis Table

> Sorted by Priority → Difficulty. "Already in project" = feature already exists per REPO_LEARNINGS.md audit.

| # | Repo | Stars | What Is It | Steal/Implement TODAY | Difficulty | Priority | Status |
|---|------|-------|------------|-----------------------|------------|----------|--------|
| 1 | `TauricResearch/TradingAgents` | 47.4k | LangGraph multi-agent debate framework: 4 analysts + bull/bear debate + risk gating | `LangGraph` multi-specialist pipeline replacing linear agent chain; `quick_think_llm` for routing (cuts cost 70%) | Hard | High | ✅ In REPO_LEARNINGS |
| 2 | `TraderAlice/OpenAlice` | 3.1k | 24/7 autonomous trading agent built with Claude; trading-as-git paradigm | `GuardPipeline` class + `trade_commits` hash table + `EventLog` JSONL bus + `HeartbeatProtocol` | Medium | High | ✅ In REPO_LEARNINGS |
| 3 | `tradermonty/claude-trading-skills` | 655 | SKILL.md-based signal quality gate system for Claude trading agents | `ExposureCoach` gate + `SignalPostmortem` classifier + `MAE/MFE` tracking table | Easy | High | ✅ In REPO_LEARNINGS |
| 4 | `calesthio/Crucix` | 8.5k | 27-source macro intelligence platform in Node.js with delta-scoring and alert tiers | `IntelligenceSweep` with `asyncio.gather()` + `DeltaEngine` FLASH/PRIORITY/ROUTINE + Telegram commands | Medium | High | ✅ In REPO_LEARNINGS |
| 5 | `abdlhannan/MT5_Trade_Connector` | 14 | MT5 connector with daily/monthly loss limits and trailing stop thread safety | `RiskManagement_v1` class: daily 5% / monthly 10% limits; `FeedFreshnessGuard` pattern | Easy | High | ✅ In REPO_LEARNINGS |
| 6 | `sickn33/antigravity-awesome-skills` | 22.9k | 1,000+ battle-tested SKILL.md files for Claude Code / Antigravity agents | **NEW**: Browse `skills/` for domain-specific prompt patterns; steal `skill-template.md` structure for PulseTrade SKILL.md files | Easy | High | 🆕 Not covered |
| 7 | `mementum/backtrader` | 21k | Python backtesting library with 122 indicators and SQN analyzer | `cerebro.addanalyzer(bt.analyzers.SQN)` — SQN > 2.5 = production-ready gate | Easy | High | ✅ In REPO_LEARNINGS |
| 8 | `HKUDS/AI-Trader` | 12.2k | AI agent swarm marketplace with strategy publishing and copy-trading | `signals` table schema with `sources`, `reasoning`, `metadata` JSONB columns | Easy | High | ✅ In REPO_LEARNINGS |
| 9 | `huseinzol05/Stock-Prediction-Models` | 9.3k | 18 DL models benchmarked + 23 RL agents; ensemble stacking patterns | Dilated-CNN-Seq2seq (95.86%, 5× faster than LSTM); 3-class output (up/unchanged/down) | Medium | High | ✅ In REPO_LEARNINGS |
| 10 | `stefan-jansen/machine-learning-for-trading` | 17k | 150+ notebooks: SHAP, GARCH, Kalman, LSTM, TimeGAN, RL | SHAP feature explainability on LGBM + Kalman filter pre-LSTM + GARCH regime gate | Medium | High | ✅ In REPO_LEARNINGS |
| 11 | `letta-ai/claude-subconscious` | 407 | Gives Claude Code persistent memory via Letta agent + hook system (SessionStart, PreToolUse, Stop) | **NEW**: `hooks/` directory pattern — wire `PreToolUse` hook to validate any risky agent action before execution; `SessionStart` hook to reload prior agent memory from Supabase | Easy | High | 🆕 Not fully covered |
| 12 | `staskh/trading_skills` | 77 | 24 MCP tools: whale-hunting via Polygon.io, Greeks, VaR, Sharpe, drawdown | `whale-hunting` MCP tool (Polygon.io options flow) + dual SKILL.md + FastMCP server pattern | Medium | High | ✅ In REPO_LEARNINGS |
| 13 | `antonoly/claude-code-anymodel` | 33 | Proxy layer to use Claude Code with OpenRouter, Ollama, and 200+ models via bridge | **NEW**: Use `bridge/` as pattern for PulseTrade LLM fallback chain: route DeepSeek → Anthropic → OpenRouter → rule-based without changing agent code | Easy | High | 🆕 Not covered |
| 14 | `KeygraphHQ/shannon` | 10.6k | Autonomous AI security auditor achieving 96% exploit detection; uses `.claude/commands/` + `audit-logs/` | **NEW**: Steal `audit-logs/` append-only pattern and `.claude/commands/` slash-command registry — directly applicable to PulseTrade trade audit trail and `/sweep`, `/brief` slash commands | Easy | High | 🆕 Not covered |
| 15 | `tensortrade-org/tensortrade` | 6.1k | RL trading framework; v1.0.4 Python 3.12+; commission=0.0% destroys all RL profitability | `commission=0.0001` mandatory in ALL backtests; `ActionScheme`/`RewardScheme` composable RL env | Easy | High | ✅ In REPO_LEARNINGS |
| 16 | `QuantConnect/Lean` | 18.3k | Institutional-grade C# quant platform with 4-layer framework (Alpha→Portfolio→Risk→Execution) | 4-layer architecture map for PulseTrade + walk-forward OOS validation as production gate | Hard | High | ✅ In REPO_LEARNINGS |
| 17 | `MSL135/GODMOD3` | 88 | ULTRAPLINIAN pattern: OpenRouter gateway + 3-model committee vote + hedge-language stripping | `strip_hedges()` function + committee_vote() for council decisions + OpenRouter as LLM gateway | Easy | High | ✅ In REPO_LEARNINGS |
| 18 | `hzjken/HFT-price-prediction` | 181 | LightGBM + RF on order book; 76-78% OOS directional accuracy; genetic algorithm feature selection | `bid_advance_time`, `ask_advance_time`, `bid_ask_vol_ratio` microstructure features from MT5 ticks | Medium | High | ✅ In REPO_LEARNINGS |
| 19 | `tradesdontlie/tradingview-mcp` | 1.1k | 78 MCP tools bridging Claude to TradingView Desktop via CDP on port 9222 | `chart_get_state` + `data_get_study_values` (RSI/MACD/BB live) + `tv stream quote` | Medium | Medium | ✅ In REPO_LEARNINGS |
| 20 | `HFTHaidra/HFT-Arbitrage-EA-MQL4-MQL5` | 110 | Two-broker arbitrage EA; compares bid/ask tick-by-tick to detect price lag | Feed staleness check pattern: if MT5 tick timestamp delta > 30s → block order | Easy | Medium | ✅ In REPO_LEARNINGS |
| 21 | `ccxt/binance-trade-bot` | 8.6k | Binance crypto rotation bot; rotates between coins based on ratio thresholds | **NEW**: Steal SQLAlchemy-based `database.py` trade history pattern + `config.cfg` environment management; crypto pair ratio-based switching usable as crypto signal gate | Easy | Medium | 🆕 Not covered |
| 22 | `Yvictor/TradingGym` | 1.9k | OpenAI Gym RL env for tick data with explicit bid/ask as features | `fee=0.0001` + `bid_ask_ratio` as RL observation feature | Easy | Medium | ✅ In REPO_LEARNINGS |
| 23 | `EarnForex/Point-and-Figure` | 7 | MT5 P&F chart indicator with ATR-based box sizing | Use P&F box logic as a noise-filter for ICT/SMC: only act on signals that represent ≥1 P&F box move | Hard | Medium | ✅ In REPO_LEARNINGS |
| 24 | `grananqvist/Awesome-Quant-ML-Trading` | 3.5k | Curated list of quant ML resources (de Prado, mlfinlab, PGPortfolio) | Read de Prado "10 Reasons ML Funds Fail" — checklist for PulseTrade model validation | Easy | Medium | ✅ In REPO_LEARNINGS |
| 25 | `StockSharp/StockSharp` | 9.3k | C# algo trading platform covering stocks, forex, crypto, and options with visual designer | **NEW**: Low applicability to Python stack, but reference `Algo.Analytics` for analytics pipeline pattern; `Alerts.Interfaces` for typed alert schema | Hard | Low | 🆕 Not covered |
| 26 | `gbeced/pyalgotrade` | 4.6k | Python algo trading library (archived Nov 2023); event-driven; broker abstraction | ARCHIVED — superseded by backtrader. Skip. | — | Low | 🆕 Archived |
| 27 | `Mathieu2301/TradingView-API` | 2.9k | Node.js TradingView socket: real-time prices, indicators, screener, backtesting API | Use for cross-validation of MT5 data in research sessions only; not production-stable | Medium | Low | ✅ In REPO_LEARNINGS |
| 28 | `viabtc/viabtc_exchange_server` | 2.8k | C-based high-speed exchange matching engine with Redis/Kafka real-time notification | **NEW**: Reference only — C infrastructure, not Python-compatible. Key insight: use Redis pub/sub for PulseTrade internal signal bus (replace `mesh_bus.py` polling with Redis channels) | Hard | Medium | 🆕 Not covered |
| 29 | `MKwenhua/real-time-charts` | 209 | Real-time market trading platform with WebSocket charts | **NEW**: Reference for Next.js 14 WebSocket chart streaming pattern into the PulseTrade dashboard | Medium | Low | 🆕 Not covered |
| 30 | `Superalgos/Superalgos` | varies | Visual strategy node-graph editor; community strategy sharing; multi-exchange | Pattern library for slippage simulation config; community sharing not applicable to PulseTrade | Hard | Low | ✅ In REPO_LEARNINGS |
| 31 | `koreainvestment/open-trading-api` | varies | Korea Investment brokerage open API with LLM integration patterns | Not applicable to MT5/Forex. Skip. | — | Low | ✅ In REPO_LEARNINGS |
| 32 | `knowm/XChange` | varies | Java unified interface for 60+ crypto exchanges | Java stack — not applicable. Architecture reference only for order book schema | Hard | Low | ✅ In REPO_LEARNINGS |
| 33 | `quantopian/zipline` | 19.6k | Event-driven backtesting framework (archived); active fork: zipline-reloaded | ARCHIVED — use `zipline-reloaded` if needed; backtrader is better choice | — | Low | ✅ In REPO_LEARNINGS |
| 34 | `askmike/gekko` | 10.2k | Bitcoin TA bot in Node.js (archived 2020) | ARCHIVED. Historical reference only. Plugin strategy pattern interesting but dead. | — | Low | ✅ In REPO_LEARNINGS |
| 35 | `tensortrade-org/tensortrade` | 6.1k | (see row 15) | Already covered above | — | — | ✅ Duplicate |
| 36 | `stavros0/bitcoin-price-prediction` | varies | Bayesian regression for BTC price with uncertainty quantification | **NEW**: Bayesian posterior predictive → uncertainty bounds on LSTM predictions; add `confidence_interval` field to `Signal` model | Medium | Low | 🆕 Not covered |
| 37 | `anthropics/claude-code` | 109k | Official Claude Code CLI; slash commands, CLAUDE.md, permission model, MCP config | Use `.claude/commands/` for PulseTrade dev workflow slash commands: `/deploy`, `/backtest`, `/sweep` | Easy | Medium | ✅ In idea.md |
| 38 | `affaan-m/everything-claude-code` | 140k | Claude Code optimization: compact contexts, parallel subagents, CLAUDE.md architecture | Parallel subagent pattern: run market + analysis agents simultaneously; CLAUDE.md structured imports | Easy | Medium | ✅ In idea.md |
| 39 | `antonoly/claude-code-anymodel` | 33 | (see row 13) | Already covered above | — | — | ✅ Duplicate |
| 40 | `shareAI-lab/learn-claude-code` | 48.6k | Prompt scaffolding, system prompt injection, multi-file context loading patterns | Harness engineering: structured system prompt with explicit role + constraints + output format | Easy | Low | ✅ In idea.md |
| 41 | `ultraworkers/claw-code` | 171k | Rust CLI agent harness; multi-session management; workspace isolation | **NEW**: Session isolation pattern — run backtest and live agents in isolated workspaces so a backtest crash doesn't affect live trading | Medium | Medium | 🆕 Not covered |
| 42 | `tiero/claw-cash` | 17 | Bitcoin wallet for AI agents with hardware enclave key storage | **NEW**: Key storage in hardware enclave pattern → apply to PulseTrade MT5 credentials: store in OS keychain (`keyring` library) not plaintext `.env` | Easy | High | 🆕 Not covered |
| 43 | `public-apis/public-apis` | varies | Curated list of free public APIs | Already used to build IntelligenceSweep source list. Skip. | — | Low | ✅ Covered |
| 44 | `MSL135/GODMOD3` | 88 | (see row 17) | Already covered above | — | — | ✅ Duplicate |

---

## NEW Findings Not in Existing Research

The following repos yielded concrete new findings not present in `REPO_LEARNINGS.md` or `idea.md`:

### 1. `sickn33/antigravity-awesome-skills` (22.9k ⭐) — NEW

**What it is:** The largest curated collection of battle-tested SKILL.md files for Claude Code — 1,000+ skills covering everything from database migrations to API design.

**Steal TODAY:** Browse the `skills/` directory and extract:
- `skill-template.md` — the canonical SKILL.md format with `When to use`, `Key files`, `API surface`, `Examples`, `Anti-patterns` sections
- Financial/trading skills if any exist in the collection (search for "trading", "backtest", "risk")
- Use as a reference for the 5 missing PulseTrade SKILL.md files identified in REPO_LEARNINGS

**Implementation (15 minutes):**
```bash
# Find any trading/finance skills
curl -s https://api.github.com/repos/sickn33/antigravity-awesome-skills/git/trees/main?recursive=1 \
  | jq -r '.tree[].path' | grep -i "trading\|finance\|invest\|risk\|quant"
```

**Difficulty:** Easy | **Priority:** High

---

### 2. `letta-ai/claude-subconscious` (407 ⭐) — NEW HOOK PATTERN

**What it is:** Adds a Letta-powered "subconscious" to Claude Code via Claude's hooks system — persistent memory that survives session resets.

**Steal TODAY — Hook Registration Pattern:**

```json
// .claude/settings.json — add hooks
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "python scripts/agent_memory_reload.py --agent all"
      }]
    }],
    "PreToolUse": [{
      "matcher": "execute_order|place_trade",
      "hooks": [{
        "type": "command",
        "command": "python agents/guards.py --pre-validate $TOOL_INPUT"
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command", 
        "command": "python scripts/session_checkpoint.py --save-state"
      }]
    }]
  }
}
```

**Why High priority:** The `PreToolUse` hook is a programmatic safety gate — it runs `GuardPipeline` validation *before* any tool call that could place a trade. This is defence-in-depth on top of the existing 7 guards.

**Difficulty:** Easy | **Priority:** High

---

### 3. `antonoly/claude-code-anymodel` — LLM Bridge Pattern

**What it is:** A proxy bridge that lets Claude Code route to any LLM via OpenRouter/Ollama with zero code changes.

**Steal TODAY — LLM Bridge for PulseTrade:**

```python
# llm/bridge.py — model-agnostic LLM caller
import openai

PROVIDER_CHAIN = [
    {"base_url": "https://api.anthropic.com/v1", "model": "claude-sonnet-4-6", "key_env": "ANTHROPIC_API_KEY"},
    {"base_url": "https://api.deepseek.com/v1",  "model": "deepseek-chat",      "key_env": "DEEPSEEK_API_KEY"},
    {"base_url": "https://openrouter.ai/api/v1", "model": "meta-llama/llama-3.3-70b", "key_env": "OPENROUTER_API_KEY"},
]

async def call_llm_with_fallback(messages: list, temperature: float = 0.1) -> str:
    for provider in PROVIDER_CHAIN:
        try:
            client = openai.AsyncOpenAI(
                base_url=provider["base_url"],
                api_key=os.environ[provider["key_env"]]
            )
            resp = await client.chat.completions.create(
                model=provider["model"],
                messages=messages,
                temperature=temperature
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"Provider {provider['model']} failed: {e}")
    return rule_based_fallback(messages)
```

**Difficulty:** Easy | **Priority:** High

---

### 4. `KeygraphHQ/shannon` (10.6k ⭐) — Audit Log + Slash Commands

**What it is:** Autonomous AI security scanner; achieved 96% exploit detection via systematic tool-use + structured audit logging.

**Steal TODAY — Two patterns:**

**A. `.claude/commands/` slash command registry:**
```bash
mkdir -p .claude/commands
# Each file becomes a /command in Claude Code
cat > .claude/commands/sweep.md << 'EOF'
# /sweep
Run a full intelligence sweep across all macro sources.

Steps:
1. Execute `python -m filters.intelligence_sweep --full`
2. Display FLASH alerts immediately
3. Save results to `logs/sweep_$(date +%Y%m%d_%H%M%S).json`
4. Update the dashboard with new regime data
EOF

cat > .claude/commands/backtest.md << 'EOF'  
# /backtest $SYMBOL $DAYS
Run walk-forward backtest. Args: symbol (e.g. EURUSD), days (default 90).
Steps: 1. Load data 2. Run walk_forward_optimizer 3. Report SQN + max drawdown
EOF
```

**B. `audit-logs/` append pattern** — Shannon commits every tool call + result to a structured JSONL file. Identical to OpenAlice's EventLog pattern but confirms it's the right approach.

**Difficulty:** Easy | **Priority:** High

---

### 5. `tiero/claw-cash` — Credential Security

**What it is:** Bitcoin wallet for AI agents with hardware enclave key storage, stablecoin-in Bitcoin-out conversion.

**Steal TODAY — Secure MT5 credential storage:**

```python
# broker/credential_store.py
import keyring

SERVICE_NAME = "PulseTrade-TradingBot"

def store_mt5_credentials(login: str, password: str, server: str):
    """Store MT5 credentials in OS keychain (not .env)."""
    keyring.set_password(SERVICE_NAME, "MT5_LOGIN", login)
    keyring.set_password(SERVICE_NAME, "MT5_PASSWORD", password)
    keyring.set_password(SERVICE_NAME, "MT5_SERVER", server)

def get_mt5_credentials() -> dict:
    return {
        "login":    keyring.get_password(SERVICE_NAME, "MT5_LOGIN"),
        "password": keyring.get_password(SERVICE_NAME, "MT5_PASSWORD"),
        "server":   keyring.get_password(SERVICE_NAME, "MT5_SERVER"),
    }
```

```bash
pip install keyring
# On Linux also: pip install secretstorage
```

**Why:** MT5 credentials in `.env` files get accidentally committed to git. OS keychain is encrypted at rest and tied to the user session. The claw-cash enclave pattern is the production-grade equivalent.

**Difficulty:** Easy | **Priority:** High

---

### 6. `viabtc/viabtc_exchange_server` — Redis Signal Bus

**What it is:** C-based high-performance exchange matching engine using Redis pub/sub for real-time order book and trade notifications.

**Steal TODAY — Replace `mesh_bus.py` polling with Redis pub/sub:**

```python
# utils/redis_bus.py
import redis.asyncio as aioredis
import json

class RedisBus:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(url)
    
    async def publish(self, channel: str, payload: dict):
        await self.redis.publish(channel, json.dumps(payload))
    
    async def subscribe(self, channel: str):
        """Generator that yields messages from channel."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield json.loads(message['data'])

# Channels:
# "PulseTrade:signals"    — new trading signals
# "PulseTrade:alerts"     — intelligence sweep alerts
# "PulseTrade:heartbeat"  — pipeline health pings
# "PulseTrade:trades"     — execution confirmations
```

**Why Medium priority:** Current `mesh_bus.py` likely uses polling or direct function calls. Redis pub/sub is non-blocking and decouples agents — analysis_agent doesn't need to know where strategy_agent runs.

**Difficulty:** Medium | **Priority:** Medium

---

### 7. `ccxt/binance-trade-bot` — SQLAlchemy Trade History Pattern

**What it is:** Crypto rotation bot that trades between Binance pairs; uses SQLAlchemy ORM for trade history with a clean schema.

**Steal TODAY — Trade history ORM pattern:**

```python
# database/models.py — SQLAlchemy declarative pattern
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TradeHistory(Base):
    __tablename__ = "trade_history"
    
    id          = Column(Integer, primary_key=True)
    symbol      = Column(String, nullable=False, index=True)
    direction   = Column(String(10))  # BUY / SELL
    lots        = Column(Float)
    open_price  = Column(Float)
    close_price = Column(Float)
    pnl_usd     = Column(Float)
    pnl_pips    = Column(Float)
    commission  = Column(Float)
    strategy    = Column(String(50))  # which strategy fired
    confidence  = Column(Float)       # model confidence at entry
    opened_at   = Column(DateTime)
    closed_at   = Column(DateTime)
    duration_m  = Column(Integer)     # minutes in trade
```

**Difficulty:** Easy | **Priority:** Medium

---

### 8. `ultraworkers/claw-code` — Workspace Isolation

**What it is:** Rust CLI for multi-session Claude Code management with workspace isolation.

**Steal TODAY — Isolated process model:**

```python
# main.py — separate processes for live vs backtest
import multiprocessing

def run_live_trading():
    """Live trading process — isolated, can't be killed by backtest crash."""
    from agents.crucix import CrucixAgent
    # ... live pipeline
    
def run_backtest_session(symbol, days):
    """Backtest in subprocess — crash doesn't affect live."""
    from backtesting.engine import BacktestEngine
    # ...

if __name__ == "__main__":
    live_proc = multiprocessing.Process(target=run_live_trading, daemon=False)
    live_proc.start()
    # Backtests always run in separate non-daemon processes
```

**Difficulty:** Medium | **Priority:** Medium

---

### 9. `stavros0/bitcoin-price-prediction` — Uncertainty Quantification

**What it is:** Bayesian regression for BTC price; key contribution is posterior predictive uncertainty bounds.

**Steal TODAY — Confidence intervals on LSTM output:**

```python
# models/uncertainty.py
import numpy as np

def monte_carlo_dropout_predict(model, X, n_passes: int = 50) -> dict:
    """
    Enable dropout at inference time for uncertainty estimation.
    Run N forward passes, compute mean and std.
    """
    model.training = True  # keep dropout active
    predictions = np.array([model(X).numpy() for _ in range(n_passes)])
    
    return {
        "mean": predictions.mean(axis=0),
        "std": predictions.std(axis=0),
        "ci_lower": np.percentile(predictions, 5, axis=0),
        "ci_upper": np.percentile(predictions, 95, axis=0),
    }

# In neural_strategy.py:
pred = monte_carlo_dropout_predict(model, features)
if pred["std"] > UNCERTAINTY_THRESHOLD:
    return SignalType.HOLD  # too uncertain — skip trade
```

**Difficulty:** Medium | **Priority:** Low

---

### 10. `MKwenhua/real-time-charts` — Dashboard WebSocket Pattern

**What it is:** React + WebSocket real-time market chart platform.

**Steal TODAY — For Next.js 14 dashboard:**

```typescript
// web/app/hooks/useRealtimeCandles.ts
import { useEffect, useState } from 'react'

export function useRealtimeCandles(symbol: string) {
  const [candles, setCandles] = useState<Candle[]>([])
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/candles/${symbol}`)
    ws.onmessage = (e) => {
      const candle = JSON.parse(e.data)
      setCandles(prev => {
        // Update last candle if same timestamp, else append
        if (prev.length && prev[prev.length-1].ts === candle.ts) {
          return [...prev.slice(0, -1), candle]
        }
        return [...prev.slice(-500), candle]  // keep last 500
      })
    }
    return () => ws.close()
  }, [symbol])
  
  return candles
}
```

**Difficulty:** Easy | **Priority:** Low

---

## IMPLEMENT TODAY — Top 5 Most Impactful + Easiest

### 🔴 #1 — Secure MT5 Credentials with `keyring` (30 min)
**Repo:** `tiero/claw-cash`  
**File:** Create `broker/credential_store.py`  
**Why urgent:** Credentials in `.env` are one `git add .` away from a disaster. OS keychain survives that.  
```bash
pip install keyring
# then replace os.environ["MT5_PASSWORD"] with get_mt5_credentials()["password"]
```
**Effort:** 30 minutes. Zero architectural changes needed.

---

### 🔴 #2 — Add `PreToolUse` Hook for Guard Validation (45 min)
**Repo:** `letta-ai/claude-subconscious`  
**File:** `.claude/settings.json` (add `hooks` block)  
**Why urgent:** This is a zero-code safety gate. Any Claude Code session that tries to place a trade gets routed through `GuardPipeline` first — even if you forgot to call it in agent code.  
```json
"PreToolUse": [{"matcher": "place_order|execute_trade", "hooks": [{"type": "command", "command": "python agents/guards.py --validate-stdin"}]}]
```
**Effort:** 45 minutes including guard CLI wrapper.

---

### 🔴 #3 — Create 5 Missing SKILL.md Files (2 hours)
**Repo:** `sickn33/antigravity-awesome-skills` (template source)  
**Files:** Create `.claude/skills/intelligence-sweep.md`, `signal-quality-gates.md`, `model-evaluation.md`, `backtest-standards.md`, `feature-engineering.md`  
**Why urgent:** Identified gap in REPO_LEARNINGS. Every new capability needs a SKILL.md or Claude Code won't know how to use it. These 5 cover IntelligenceSweep, ExposureCoach, SHAP, SQN, and Kalman — all features being added right now.  
**Effort:** 2 hours (use the SKILL.md template from sickn33 repo).

---

### 🔴 #4 — Register `.claude/commands/` Slash Commands (1 hour)
**Repo:** `KeygraphHQ/shannon`  
**Files:** Create `.claude/commands/sweep.md`, `backtest.md`, `status.md`, `deploy.md`, `review.md`  
**Why urgent:** Every dev session currently requires typing long incantations. Slash commands like `/sweep EURUSD`, `/backtest EURUSD 90`, `/status` take 5 minutes each to create and save hours per week.  
**Effort:** 1 hour. One markdown file per command.

---

### 🔴 #5 — Wire LLM Bridge with Fallback Chain (2 hours)
**Repo:** `antonoly/claude-code-anymodel`  
**File:** Create `llm/bridge.py`; update all `call_llm()` usages to go through bridge  
**Why urgent:** If Anthropic API goes down mid-session, the bot goes blind. The bridge costs 2 hours to implement and provides automatic failover to DeepSeek → OpenRouter → rule-based, no manual intervention needed.  
**Effort:** 2 hours. Already have `DEEPSEEK_API_KEY` and `OPENROUTER_API_KEY` env vars presumably in place from DeepSeek LLM strategy.

---

## Priority × Difficulty Summary Matrix

| Priority | Easy | Medium | Hard |
|----------|------|--------|------|
| **High** | keyring credentials, PreToolUse hook, slash commands, SKILL.md files, LLM bridge, `commission=0.0001`, `strip_hedges()`, OpenRouter gateway | IntelligenceSweep, GuardPipeline, SHAP+Kalman+GARCH, microstructure features, Dilated-CNN benchmark, ExposureCoach, EventLog | LangGraph debate pipeline |
| **Medium** | SQN analyzer, `TradeHistory` ORM, feed freshness guard, FRED API | Redis signal bus, workspace isolation, TradingView MCP, walk-forward optimizer | 4-layer framework, P&F filter |
| **Low** | Bayesian uncertainty (MC dropout), WebSocket dashboard hook, skill template browser | Uncertainty quantification | StockSharp reference, viabtc architecture |

---

## Source Quality Index — New Repos Only

| Repository | Stars | Activity | Quality | Primary Value for PulseTrade |
|-----------|-------|----------|---------|---------------------------|
| sickn33/antigravity-awesome-skills | 22.9k | Active | ⭐⭐⭐⭐ | SKILL.md templates + community patterns |
| KeygraphHQ/shannon | 10.6k | Active | ⭐⭐⭐⭐ | Audit log + slash command registry |
| letta-ai/claude-subconscious | 407 | Active | ⭐⭐⭐⭐ | PreToolUse safety hooks |
| antonoly/claude-code-anymodel | 33 | New | ⭐⭐⭐ | LLM bridge/fallback pattern |
| tiero/claw-cash | 17 | Active | ⭐⭐⭐ | Credential security via keychain |
| viabtc/viabtc_exchange_server | 2.8k | Stale | ⭐⭐⭐ | Redis pub/sub signal bus concept |
| ccxt/binance-trade-bot | 8.6k | Active | ⭐⭐⭐ | SQLAlchemy trade history schema |
| ultraworkers/claw-code | 171k | Active | ⭐⭐ | Process isolation for live vs backtest |
| MKwenhua/real-time-charts | 209 | Stale | ⭐⭐ | WebSocket candle hook for dashboard |
| stavros0/bitcoin-price-prediction | ~50 | Archived | ⭐⭐ | MC dropout uncertainty quantification |
| gbeced/pyalgotrade | 4.6k | Archived | ❌ | Skip — superseded by backtrader |
| StockSharp/StockSharp | 9.3k | Active | ⭐ | C# — not applicable |
| koreainvestment/open-trading-api | varies | Active | ⭐ | Korea brokerage — not applicable |

---

*Research base: 42 repositories, ~650k+ combined stars. This document supplements `REPO_LEARNINGS.md` (26 repos) and `idea.md` (40 repo catalogue). Total unique actionable findings across all three documents: 47.*
