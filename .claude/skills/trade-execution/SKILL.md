---
name: trade-execution
description: Implement or review the trade execution model. Covers order placement, Stop Loss, 3 Take Profits, partial closes, breakeven logic, and trailing stops. Use when building, modifying, or debugging trade execution and management.
---

# Trade Execution Model

This skill covers the full trade execution and management lifecycle for the trading bot.

## Order Structure

Every trade placed by the bot must include:

| Component | Description |
|---|---|
| Entry | Market or limit order at signal price |
| Stop Loss | Single SL protecting the full position |
| Take Profit 1 | First partial close target |
| Take Profit 2 | Second partial close target |
| Take Profit 3 | Final close target |

## Position Splitting for TPs

When a trade opens, the position is logically split:

```
Total position: 1.0 lot (example)
├── TP1 portion: 0.40 lot (40%)
├── TP2 portion: 0.30 lot (30%)
└── TP3 portion: 0.30 lot (30%)
```

These percentages should be configurable in `config/settings.py`:

```python
TP1_CLOSE_PERCENT = 0.40
TP2_CLOSE_PERCENT = 0.30
TP3_CLOSE_PERCENT = 0.30  # remainder
```

## Trade Lifecycle

```
1. Signal approved by Risk Agent
        ↓
2. Execution Agent places order
   - Market order (or limit at entry)
   - SL attached
   - TP1, TP2, TP3 levels recorded
   - Verify actual filled size (handle partial fills)
   - Persist trade to DB immediately
        ↓
3. Trade is OPEN — Trade Manager monitors
        ↓
4. TP1 HIT
   - Close 40% of position (via MT5 counter-order, not a "close_partial" call)
   - Move SL to breakeven = entry + spread + commission (NOT raw entry price)
   - Persist state to DB
   - Log event
        ↓
5. TP2 HIT
   - Close 30% of position
   - Begin trailing SL behind price
   - Persist state to DB
   - Log event
        ↓
6. TP3 HIT
   - Close remaining 30%
   - Trade fully closed
   - Persist final state to DB
   - Log event → Learning Agent reviews
        ↓
   OR at any point:
   SL HIT → close everything remaining → persist → log → review
```

## Stop Loss Management

| Phase | SL Behavior |
|---|---|
| After entry | SL at original level |
| After TP1 | SL moved to breakeven **= entry + spread + commission_in_pips** |
| After TP2 | SL trails behind price at configurable distance |

**Why breakeven ≠ entry price:**
If you move SL to exactly the entry price, on a 1.2 pip spread pair the close price is `entry - spread`, giving you a small loss instead of zero. True breakeven must account for:
- The spread at entry
- Commission per side (converted to pips)

```python
# Correct breakeven calculation
spread_pips = market_agent.get_spread(symbol)
commission_pips = config.COMMISSION_PER_LOT / pip_value  # convert $ to pips
breakeven_offset = spread_pips + commission_pips

if direction == "BUY":
    breakeven_sl = entry_price + breakeven_offset
else:  # SELL
    breakeven_sl = entry_price - breakeven_offset
```

Trailing stop config:

```python
TRAILING_STOP_DISTANCE_PIPS = 20  # configurable
```

## Implementation Notes

### Broker Integration

The Execution Agent calls the broker connector:

```python
# broker/connector.py interface
class BrokerConnector:
    def place_order(self, symbol, direction, lot_size, sl, tp) -> str:
        """Place an order. Returns order ID."""

    def modify_order(self, order_id, sl=None, tp=None) -> bool:
        """Modify SL or TP of an existing order."""

    def close_partial(self, order_id, lot_size) -> bool:
        """Partially close a position. See MT5 implementation note below."""

    def close_order(self, order_id) -> bool:
        """Fully close a position."""

    def get_open_positions(self) -> list:
        """Get all open positions."""
    
    def get_fill_size(self, order_id) -> float:
        """Get actual filled lot size for an order (may differ from requested)."""
```

### MT5 Partial Close — CRITICAL Implementation Detail

MT5 Python does **NOT** have a `close_partial()` function. To partially close a position, you must send a **counter-order** for the fraction you want to close, referencing the original position ticket.

```python
import MetaTrader5 as mt5

def close_partial_mt5(position_ticket: int, symbol: str, lot_size: float, direction: str):
    """Close a partial amount of a position by sending a counter-order."""
    # For a BUY position, send a SELL order to partially close
    close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(symbol).bid if direction == "BUY" else mt5.symbol_info_tick(symbol).ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": close_type,
        "position": position_ticket,  # Reference the original position
        "price": price,
        "deviation": 20,
        "magic": 123456,
        "comment": "partial close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    return result.retcode == mt5.TRADE_RETCODE_DONE
```

This is NOT optional knowledge — calling a nonexistent `close_partial()` will crash the bot. The broker connector must implement this pattern.

### Partial Fill Handling

When you request 0.5 lots but only 0.3 fills (possible with ECN brokers at illiquid moments):

1. **Always check actual fill size** from `order_send()` result
2. If filled < minimum lot size → close the position and log an error
3. If partially filled → recalculate TP portion volumes based on actual fill
4. **Never assume requested = filled**

```python
result = mt5.order_send(request)
filled_lots = result.volume  # actual filled, NOT requested

if filled_lots < MIN_LOT_SIZE:
    # Cancel — too small to manage
    close_order(result.order)
    raise PartialFillError(f"Only {filled_lots} filled")

# Recalculate TP volumes from actual fill
tp1_lots = round(filled_lots * TP1_CLOSE_PERCENT, 2)
tp2_lots = round(filled_lots * TP2_CLOSE_PERCENT, 2)
tp3_lots = round(filled_lots - tp1_lots - tp2_lots, 2)  # remainder avoids rounding drift
```

### Trade Data Model

```python
# models/trade.py
@dataclass
class Trade:
    id: str
    symbol: str
    direction: str          # "BUY" or "SELL"
    entry_price: float
    lot_size: float         # actual filled size (not requested)
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    tp1_lots: float         # portion for TP1 (calculated from actual fill)
    tp2_lots: float         # portion for TP2
    tp3_lots: float         # portion for TP3 (remainder)
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    status: str = "OPEN"    # OPEN, PARTIAL, CLOSED
    open_time: datetime
    close_time: datetime = None
    pnl: float = 0.0
    close_reason: str = ""  # TP1, TP2, TP3, SL, MANUAL, EMERGENCY
    broker_ticket: int = 0  # MT5 position ticket for reconciliation
    spread_at_entry: float = 0.0  # for learning system tracking
```
    close_time: datetime = None
    pnl: float = 0.0
    close_reason: str = ""  # TP1, TP2, TP3, SL, MANUAL, EMERGENCY
```

### Error Handling

- If order placement fails → log error, do NOT retry blindly, alert via Telegram
- If partial close fails → retry once, then log and alert
- If broker disconnects during open trades → reconnect and **reconcile** positions
- Never leave orphaned positions without SL
- If partial fill occurs → recalculate TP volumes from actual fill, or cancel if below minimum
- **Every state change must be persisted to DB** — if the bot crashes between TP1 close and SL move, it must know on restart that TP1 was already hit
