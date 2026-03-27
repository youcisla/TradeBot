# TradingBot — Claude Code Project Rules

## MANDATORY: Do This Before Every Response

1. **Read the relevant skills** in `.claude/skills/` that apply to the task (use the `Skill` tool or read files directly)
2. **Read the current state of the files** you are about to touch — never assume you remember them from a previous session
3. **Check memory** at `C:\Users\Y.chehboub\.claude\projects\c--Users-Y-chehboub-Downloads-TradingBot\memory\` for any relevant user preferences or project state
4. **Only then act** — plan, implement, verify

Never skip step 1-3. Never write code based on memory alone. Always read → then write.

---

## Project Identity

**Name:** NeuralFX TradingBot
**Stack:** Python (bot) + Next.js 14 App Router (dashboard)
**Broker:** PU Prime via MetaTrader 5
**DB:** PostgreSQL (Supabase) — 7 tables
**Dashboard URL:** Next.js app in `web/`
**Primary strategy:** LSTM Neural Network (per-symbol, auto-trained on 2yr H1 history)
**Legacy strategies:** ICT/SMC engine, SMA Crossover (kept for reference, not active in main loop)

---

## Skill Index

| Skill | When to use |
|---|---|
| `trading-bot-overview` | Architecture decisions, agent pipeline, system design |
| `implement-agent` | Building or modifying any agent |
| `add-strategy` | Creating or modifying a trading strategy |
| `trade-execution` | SL/TP/partial close/breakeven logic |
| `learning-system` | Reward scoring, confidence adjustment |
| `configure-infra` | Infra, API keys, deployment, broker config |
| `coding-standards` | UI/UX, code style, frontend patterns (READ THIS for any web work) |
| `prompt-guide` | How to write expert prompts for Claude |
| `trading-bot-overview` | Full system reference |

**Before writing any frontend code → read `coding-standards` skill first.**

---

## Agent Pipeline (current)

```
PIPELINE:  crucix → market → analysis → strategy → neural → council → risk → execution → trade_manager
SUPPORT:   learning · model_manager · logging
```

Agent event keys in DB (for `AgentFeed.tsx`):
- `crucix`, `market`, `analysis`, `strategy`, `neural`, `council`, `risk`, `execution`, `trade_manager`
- `learning`, `model_manager`, `logging`

---

## Key Files

```
main.py                          ← Bot entry point
agents/                          ← All agent implementations
  crucix_agent.py                ← Macro intelligence (wraps CrucixClient, replaces NewsFilter)
  market_agent.py, analysis_agent.py, strategy_agent.py
  neural_strategy.py             ← NeuralStrategy wrapping ModelManager
  model_manager.py               ← LSTM training/inference/fine-tuning
  risk_agent.py, execution_agent.py
  trade_manager.py, learning_agent.py, logging_agent.py
filters/crucix_client.py         ← CrucixClient + MacroContext (used by CrucixAgent)
strategies/                      ← Strategy implementations
  ict_strategy.py, ict/          ← ICT/SMC engine (10 modules)
  sma_crossover.py               ← Legacy fallback
models/
  neural_model.py                ← LSTMTradingModel, FeatureNormalizer
  neural/ (SYMBOL_H1.pt + .json) ← Saved model weights + normalizer params
config/settings.py               ← All env-driven config
web/                             ← Next.js dashboard
  src/app/dashboard/             ← Pages: page, analytics, trades, learning, strategy, ict, settings, chart
  src/components/                ← Shared components
```

---

## Skill Update Rule

When you learn something new about this project (new file, new pattern, design decision, user preference), **update the relevant skill file immediately**. Skills must always reflect the current state of the project — they are the source of truth for future sessions.

---

## What NOT to Do

- Do not use Tailwind CSS classes on any new or modified frontend file — always use inline styles
- Do not use `className` in new JSX (existing ones being migrated, do not add new ones)
- Do not skip reading files before editing them
- Do not invent file paths or API shapes — verify them first
- Do not commit without asking
- Do not push without asking
