---
name: coding-standards
description: "PulseTrade frontend code style rules — inline styles only, no Tailwind on new files, no className on new JSX."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# PulseTrade Coding Standards

## CRITICAL FRONTEND RULES

### 1. Tailwind is the design system — use utility classes for all styling
New files and migrated files use Tailwind utility classes exclusively (per senior-frontend redesign, 2026-04-13).

### 2. shadcn/ui component primitives
Use shadcn/ui + Radix for all compound UI components (Dialog, DropdownMenu, Select, Tabs, etc.).
Install new components via: `npx shadcn@latest add <component>`

### 3. Design tokens via Tailwind config + CSS variables
Custom tokens (colors, fonts, spacing) live in `tailwind.config.ts` and `globals.css`.
Do not hardcode hex values in components.
```tsx
// Design token reference:
// --matrix / #00fd87       = primary green (active, positive, live)
// #ff716c                  = error/danger red
// #ffb86c                  = warning orange
// #00d2fd                  = info cyan
// #e966ff                  = DeepSeek purple
// #adaaaa                  = muted text
// #494847                  = border/divider
// #0e0e0e                  = surface (card background)
// #000000 / #131313         = page background
```

---

## Python Code Style

```python
# Line length: 100 chars max
# Indentation: 4 spaces
# Imports: stdlib → third-party → project (blank lines between groups)
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from config import settings
from database.db import Database

logger = logging.getLogger(__name__)
```

### Naming
| Type | Convention | Example |
|---|---|---|
| Variables/functions | snake_case | `best_setup`, `_compute_sl()` |
| Classes | PascalCase | `ICTStrategy`, `RiskAgent` |
| Constants | UPPER_SNAKE_CASE | `TIER_FLASH`, `_RED` |
| Private | leading underscore | `_run_inner()`, `_db` |

### Type hints (always)
```python
def detect(self, context: MarketContext) -> Optional[Signal]:
def _parse(self, raw: dict) -> MacroContext:
lot_size: float = 0.01
```

### Error handling
```python
# Never swallow exceptions silently
try:
    result = risky_operation()
except Exception:
    logger.exception("Operation failed for %s", symbol)
    return None  # safe default

# Only catch what you expect
try:
    rates = mt5.copy_rates_range(sym, tf, start, end)
except (ConnectionError, TimeoutError) as exc:
    logger.warning("MT5 connection issue: %s", exc)
    return None
```

---

## TypeScript / Next.js Style

```typescript
// Use const, never let for primitives that don't change
const PIPELINE_AGENTS = [...]  // UPPER_SNAKE_CASE for module-level constants

// Types/interfaces: PascalCase
interface BotStatus { state: string; equity: number; }
type RiskTier = "CLEAR" | "ROUTINE" | "PRIORITY" | "FLASH";

// Functions: camelCase
function statusIcon(msg: string): { icon: string; color: string } { ... }

// No unused imports or variables
// Prefer explicit return types on exported functions
```

---

## File Naming
- Python: `snake_case.py`
- TypeScript/TSX: `PascalCase.tsx` (components), `kebab-case.ts` (utilities)
- No new files unless strictly necessary for the task

---

## Comments
Add comments only when logic is non-obvious:
```python
# Good: explains WHY
# ATR > 10.0 catches crypto/XAU — use wider staleness gate
_multiplier = LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO if atr > 10.0 else LIMIT_ENTRY_MAX_DISTANCE_ATR

# Bad: describes WHAT (obvious from code)
# Set multiplier based on ATR value
_multiplier = ...
```

---

## What NOT to do
- Do not add docstrings to code you didn't change
- Do not add error handling for impossible scenarios
- Do not create helpers for one-time operations
- Do not add backwards-compatibility hacks
- Do not add features beyond what was asked
- Do not use `any` type in TypeScript unless unavoidable
- Do not use `var` in JavaScript/TypeScript
