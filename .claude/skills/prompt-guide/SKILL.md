---
name: prompt-guide
description: Expert guide on how to write high-quality prompts for Claude when working on this TradingBot project. Covers prompt anatomy, examples, anti-patterns, schemas for different task types, and tips for getting exactly what you want.
user-invocable: true
---

# How to Write Expert Prompts for Claude

Writing a great prompt is about giving Claude the right **context**, the right **constraints**, and the right **output format** — so it can act like a specialist who already knows the project deeply, not a generalist guessing from scratch.

---

## The 5 Elements of a Great Prompt

```
1. CONTEXT    → What is the current state? What file am I in? What already exists?
2. TASK       → What exactly do I want to change or create?
3. RULES      → What constraints must the result respect?
4. FORMAT     → What should the output look like?
5. EXAMPLES   → (Optional) Show me what "good" looks like
```

You don't always need all 5. Simple tasks need fewer elements. Complex tasks need all of them.

---

## Prompt Schema by Task Type

### Schema 1: "Change something in the UI"

```
[TASK]: Change [X] in [file/component]
[CONTEXT]: Currently it does [Y] / looks like [Z]
[RULES]: Must use inline styles (no Tailwind), keep the same color palette (#0a0a12 bg, JetBrains Mono font)
[TARGET]: Should now [new behavior/appearance]
```

**Weak prompt:**
> "Make the button look better"

**Strong prompt:**
> "In `web/src/components/CommandPanel.tsx`, the PAUSE button currently has a yellow border but no hover glow effect.
> Add an onMouseEnter/onMouseLeave glow effect (box-shadow: `0 0 12px rgba(245,197,24,0.4)`) like we do on other action buttons.
> Use inline styles only — no className. Don't touch the click handler logic."

---

### Schema 2: "Add a new feature"

```
[TASK]: Add [feature name]
[CONTEXT]: The current system does [X]. The feature should integrate with [Y component/agent/table]
[BEHAVIOR]: When [trigger], it should [action]
[DATA]: The data comes from [API endpoint / DB table / prop]
[RULES]: [stack constraints, style rules, don't-break-X]
[OUTPUT FORMAT]: [page / component / function / DB schema change]
```

**Weak prompt:**
> "Add a notification system"

**Strong prompt:**
> "Add a toast notification component to the dashboard.
> It should appear in the top-right corner when the bot status changes (from 'running' to 'paused' or vice versa).
> The BotStatusBar already polls `/api/status` every 5 seconds — use that as the trigger.
> Style: dark card (#0a0a12 bg, #1c1c28 border), JetBrains Mono 11px, colored left border matching the status color (green=running, yellow=paused).
> Auto-dismiss after 4 seconds. Maximum 3 toasts stacked. No external libraries — inline styles only."

---

### Schema 3: "Fix a bug"

```
[BUG]: [What is broken / what error appears]
[REPRO]: When I [do X], [Y happens instead of Z]
[FILE]: The issue is in [file:line or component]
[EXPECTED]: It should [correct behavior]
[DON'T BREAK]: [Related functionality that must still work]
```

**Weak prompt:**
> "The chart isn't working"

**Strong prompt:**
> "The TradingChart component in `web/src/components/TradingChart.tsx` shows a blank canvas when the symbol changes from EURUSD to BTCUSD.
> The chart renders correctly on first load but doesn't re-fetch data when the symbol prop changes.
> The chart library is lightweight-charts. Check if the useEffect dependency array is missing `symbol`.
> Do not change the timeframe selector logic — only fix the symbol-change re-render."

---

### Schema 4: "Implement a Python agent/module"

```
[AGENT]: [agent name]
[RESPONSIBILITY]: This agent answers: "[one question]"
[INPUTS]: Receives [data type] from [source]
[OUTPUTS]: Returns [data type] / Writes to [DB table]
[RULES]: Must follow the agent contract in implement-agent skill
[INTEGRATION]: Called from [main.py / other agent]
[EDGE CASES]: Handle [X, Y, Z]
```

**Weak prompt:**
> "Write the neural agent"

**Strong prompt:**
> "Implement `agents/neural_strategy.py` following the `add-strategy` skill and the plan in `.claude/plans/`.
> It wraps `agents/model_manager.py` which is already implemented.
> The `detect(context)` method should:
>   1. Call `model_manager.predict(context.symbol, context.candles, context)`
>   2. If confidence >= settings.NEURAL_MIN_CONFIDENCE (0.60): return a Signal with SL = 2×ATR, TP1/2/3 = 1R/2R/3R
>   3. If confidence < threshold OR model not ready: return None
> Must include an EntrySnapshot capturing spread, session, and market_condition.
> Don't implement ModelManager here — it already exists."

---

### Schema 5: "Redesign a page"

```
[PAGE]: `web/src/app/dashboard/[page]/page.tsx`
[CURRENT STATE]: Currently shows [X] using [Tailwind classes / old layout]
[TARGET]: Redesign to match the dark terminal aesthetic:
  - All inline styles (no className)
  - Background: #0a0a12 cards, #0e0e10 tables
  - Font: 'JetBrains Mono', monospace everywhere
  - Colors: [specific accents for this page]
  - Header: subsystem label (9px caps) + h1 (20px, colored)
[DATA]: The page fetches from [/api/endpoint] — keep that logic intact
[DON'T CHANGE]: The data fetching, state management, event handlers
```

**Weak prompt:**
> "Make the ICT page look better"

**Strong prompt:**
> "Redesign `web/src/app/dashboard/ict/page.tsx` to match the visual style of the analytics and trades pages we just redesigned.
> Rules:
> - ALL inline styles — remove every className
> - Keep all fetch logic, state, and calculations exactly as-is
> - Card accent colors: yellow (#f5c518) for model distribution, cyan (#00d4ff) for confluence bars, orange (#ff9d00) for session stats
> - KPI cards: same pattern as analytics page (colored top border, 22px value, 8.5px caps label)
> - Confluence bars: animated gradient bars like the ConfidenceBar in learning/page.tsx
> - Table rows: hover effect rgba(0,212,255,0.03)
> - All text: JetBrains Mono
> Return the complete rewritten file."

---

### Schema 6: "Update a skill"

```
Update the [skill-name] skill to reflect:
[CHANGE]: [What changed in the codebase]
[WHY]: [Why this matters for future sessions]
[SECTION]: Add/modify the [section] section
```

**Example:**
> "Update the `trading-bot-overview` skill to reflect that:
> 1. The SMA Crossover strategy is no longer registered in main.py (it's kept on disk but not active)
> 2. NeuralStrategy is now the primary strategy, wrapping ModelManager
> 3. The agent pipeline now includes `neural` between `strategy` and `council`
> 4. ModelManager trains one LSTM per symbol on 2yr H1 data at startup"

---

## Power Techniques

### Technique 1: Scope Limiting
Tell Claude exactly what NOT to touch. This prevents unintended refactors.
> "Only change the button styles. Do not touch the `send()` function, the COMMANDS array, or the status polling logic."

### Technique 2: File Anchoring
Reference exact file paths so Claude reads the right file.
> "Read `web/src/components/AgentFeed.tsx` first, then add the `neural` agent to the PIPELINE array after `strategy`."

### Technique 3: Show the Target
Reference an existing implementation as the gold standard.
> "Style the new card exactly like the KpiCard component in `web/src/app/dashboard/analytics/page.tsx`."

### Technique 4: Explicit Data Shape
If you know what the API returns, tell Claude exactly:
> "The `/api/learning` endpoint returns `{ confidences: StrategyConfidence[], scores: TradeScore[] }`.
> `StrategyConfidence` has: `strategy: string, confidence: number, total_trades: number, total_score: number, last_updated: string`"

### Technique 5: State the Non-Obvious
Don't assume Claude knows your project constraints — say them explicitly.
> "We use inline styles everywhere because we're migrating away from Tailwind. The reason is that Tailwind's utility classes don't give us the fine-grained control we need for the terminal aesthetic."

### Technique 6: Request Verification
Ask Claude to verify before touching things.
> "Before writing any code, read the current implementation of `CommandPanel.tsx` and tell me what the KILL button's current onClick handler does. Then make the change."

---

## Anti-Patterns to Avoid

| Bad Prompt | Why It Fails | Better Version |
|---|---|---|
| "Make it look better" | No target, no constraints | "Add a glow effect to the active nav link using box-shadow: `0 0 8px rgba(0,255,65,0.4)`" |
| "Fix the bug" | No file, no error, no repro | "In `AgentFeed.tsx`, the auto-scroll scrolls the whole page. Fix it to only scroll the inner `#terminal-log` div" |
| "Add authentication" | No spec, Claude invents one | "Add a simple password check in `layout.tsx` — read `SESSION_PASSWORD` from env, redirect to `/login` if missing" |
| "Rewrite the bot" | Way too broad | Break into: "Update the main loop to skip ICT and use NeuralStrategy instead" |
| "Do what you think is best" | Claude may add unwanted abstractions | "Keep it simple — no new abstractions, just change the one function" |

---

## Template Library

Copy-paste these for common tasks:

### Add a page to the dashboard
```
Add a new page at `web/src/app/dashboard/[NAME]/page.tsx`.
The page should:
- Use "use client" directive
- Fetch data from `/api/[endpoint]` on mount with useEffect
- Show a page header (9px caps label + 20px h1 in [COLOR])
- Display [DATA] in [TABLE/CARDS/CHART format]
- All inline styles, JetBrains Mono font, dark terminal aesthetic
- Use SymbolFilter if the data is per-symbol
```

### Add a new DB table / API route
```
Add a new API route at `web/src/app/api/[name]/route.ts`.
It should:
- Query the [TABLE] table in Supabase
- Return [SHAPE] as JSON
- Handle errors with { error: string } and status 500
- The existing pattern to follow: read `web/src/app/api/trades/route.ts`
```

### Add a new Python config setting
```
Add `[SETTING_NAME]` to `config/settings.py`.
It should:
- Read from env var `[ENV_VAR_NAME]` with default `[DEFAULT]`
- Type: [int/float/str/bool]
- Add a comment explaining what it controls
```

---

## Example: Full Expert Prompt

Here is what a complete, expert-level prompt for a complex task looks like:

---

> **Task:** Add real-time P&L streaming to the open positions table
>
> **Context:**
> The `OpenTradesTable.tsx` component at `web/src/components/OpenTradesTable.tsx` currently polls `/api/trades` every 15 seconds. It shows static PnL from the DB. The broker updates mark-to-market PnL in real-time.
>
> **Goal:**
> Add a second polling layer at 3-second intervals that fetches live PnL from `/api/trades/live-pnl` (endpoint already exists, returns `[{trade_id: string, pnl: number}]`).
> Merge live PnL values into the existing trades state by trade_id.
>
> **Rules:**
> - Only add the live PnL poll — don't change the existing 15s poll structure
> - The PnL cell should briefly flash green/red when the value changes (CSS transition or keyframe on the value span)
> - Keep all existing inline styles — don't add className
> - If `/api/trades/live-pnl` returns 404 or fails, silently ignore (bot may not support this endpoint)
>
> **Don't touch:**
> - The `closeTrade()` handler
> - The table structure and headers
> - The 15s polling logic for the main trade data

---

That level of specificity gets precise results with no surprises.
