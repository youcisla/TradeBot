---
name: trade-execution
description: "SL/TP/partial close/breakeven logic — lot allocation, TP hit handling, structural BE, TP4 runner lifecycle."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Trade Execution & Lifecycle

## Lot Allocation (ExecutionAgent)

```
Total lot → split into 4 slices:
  TP1 = 40%  (TP1_CLOSE_PERCENT=0.40)
  TP2 = 30%  (TP2_CLOSE_PERCENT=0.30)
  TP3 = 20%  (TP3_CLOSE_PERCENT=0.20)
  TP4 = 10%  (TP4_CLOSE_PERCENT=0.10) — only when take_profit_4 > 0

Broker order SL = actual SL
Broker order TP = take_profit_4 if runner, else take_profit_3 if set, else None
(TradeManager handles TP1/2/3 partial closes manually — broker TP is for crash safety only)
```

## Trade Status Flow
```
OPEN → (TP1 hit) → PARTIAL → (TP2 hit) → PARTIAL → (TP3 hit) → CLOSED or PARTIAL (runner)
                                                           ↓ (if TP4 runner active)
                                                       (TP4 hit) → CLOSED
```

## Breakeven After TP1

Two modes in `_handle_tp1` (TradeManager):
```python
# Mode 1: Structural BE (preferred — uses swing level from ICT engine)
if trade.structural_be > 0:
    be_sl = trade.structural_be   # Most recent unbroken swing low (BUY) or high (SELL)

# Mode 2: Entry+spread fallback
else:
    be_sl = entry + spread + commission  # BUY
    # or
    be_sl = entry - spread - commission  # SELL
```

`structural_be` is computed by `ICTStrategy._compute_structural_be()` at signal generation time using the ICT engine's swing point data.

## TP Hit Handling (TradeManager)

### TP1 (`_handle_tp1`):
1. `close_partial(ticket, tp1_lots)` via broker
2. Set `trade.tp1_hit = True`
3. Move SL to breakeven (structural or entry+spread)
4. `broker.modify_order(ticket, sl=be_sl)`
5. Emit Telegram: "🎯 TP1 hit — BE set"

### TP2 (`_handle_tp2`):
1. `close_partial(ticket, tp2_lots)`
2. Set `trade.tp2_hit = True`
3. Emit: "🎯 TP2 hit — runner active"

### TP3 (`_handle_tp3`):
- **Without runner** (tp4 == 0): Full close remaining position → status = CLOSED
- **With runner** (tp4 > 0): `close_partial(ticket, tp3_lots)` → status stays PARTIAL
  - Trail stop continues tracking on remaining TP4 runner

### TP4 (`_handle_tp4`):
1. `close_order(ticket)` — close entire remaining position
2. Set `trade.tp4_hit = True`, `status = CLOSED`, `close_reason = "TP4"`
3. Emit Telegram: "🚀 TP4 RUNNER HIT"

## Trailing Stop (After TP2+)
```python
def _trail_stop(self, trade, current_price):
    # Only trail after TP2 to let trade breathe
    if not trade.tp2_hit:
        return
    trail_dist = settings.TRAILING_STOP_DISTANCE_PIPS * pip_size
    if trade.direction == "BUY":
        new_sl = current_price - trail_dist
        if new_sl > trade.stop_loss:
            broker.modify_order(trade.broker_ticket, sl=new_sl)
    else:
        new_sl = current_price + trail_dist
        if new_sl < trade.stop_loss:
            broker.modify_order(trade.broker_ticket, sl=new_sl)
```

## SL Hit Handling
- Detected when broker position no longer exists (not in `pos_map`)
- `trade.status = CLOSED`, `close_reason = "SL"`
- Learning system records loss → reduces strategy confidence

## Remaining Lots Calculation
```python
@property
def remaining_lots(self) -> float:
    remaining = self.lot_size
    if self.tp1_hit: remaining -= self.tp1_lots
    if self.tp2_hit: remaining -= self.tp2_lots
    if self.tp3_hit: remaining -= self.tp3_lots
    if self.tp4_hit: remaining -= self.tp4_lots
    return max(0.0, round(remaining, 2))
```

## Broker Calls Reference
```python
# Open order
broker.open_order(symbol, direction, lot_size, sl, tp=None)  # Returns ticket int

# Partial close
broker.close_partial(ticket, lots)

# Full close
broker.close_order(ticket)

# Modify SL/TP
broker.modify_order(ticket, sl=new_sl, tp=new_tp)

# Check position exists
pos_map = broker.get_open_positions()  # dict[ticket → position]
if ticket not in pos_map: # position was closed (SL/TP hit)
```

## Key Settings
```
TP1_CLOSE_PERCENT = 0.40
TP2_CLOSE_PERCENT = 0.30
TP3_CLOSE_PERCENT = 0.20  (with runner; 0.30 without)
TP4_CLOSE_PERCENT = 0.10
TRAILING_STOP_DISTANCE_PIPS = 20
COMMISSION_PER_LOT = 7.0
BREAKEVEN_SPREAD_OFFSET = true
```
