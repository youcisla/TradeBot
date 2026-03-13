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
        ↓
3. Trade is OPEN — Trade Manager monitors
        ↓
4. TP1 HIT
   - Close 40% of position
   - Move SL to breakeven (entry price)
   - Log event
        ↓
5. TP2 HIT
   - Close 30% of position
   - Begin trailing SL behind price
   - Log event
        ↓
6. TP3 HIT
   - Close remaining 30%
   - Trade fully closed
   - Log event → Learning Agent reviews
        ↓
   OR at any point:
   SL HIT → close everything remaining → log → review
```

## Stop Loss Management

| Phase | SL Behavior |
|---|---|
| After entry | SL at original level |
| After TP1 | SL moved to breakeven (entry price) |
| After TP2 | SL trails behind price at configurable distance |

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
        """Partially close a position."""

    def close_order(self, order_id) -> bool:
        """Fully close a position."""

    def get_open_positions(self) -> list:
        """Get all open positions."""
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
    lot_size: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    status: str = "OPEN"    # OPEN, PARTIAL, CLOSED
    open_time: datetime
    close_time: datetime = None
    pnl: float = 0.0
    close_reason: str = ""  # TP1, TP2, TP3, SL, MANUAL, EMERGENCY
```

### Error Handling

- If order placement fails → log error, do NOT retry blindly, alert via Telegram
- If partial close fails → retry once, then log and alert
- If broker disconnects during open trades → reconnect and verify positions
- Never leave orphaned positions without SL
