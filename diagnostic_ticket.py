#!/usr/bin/env python3
"""Diagnostic: inspect MT5 deal history for a specific ticket.

Usage:
    python diagnostic_ticket.py <ticket>
    python diagnostic_ticket.py 191652860
"""
import sys

import MetaTrader5 as mt5

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    sys.exit(1)

try:
    ticket = int(sys.argv[1])
except (IndexError, ValueError):
    print(f"Usage: python {sys.argv[0]} <ticket>")
    sys.exit(1)

# ── DEAL REASON MAP (MT5 enum) ──────────────────────────────────────────────
DEAL_REASON = {
    0:  "RO_REASON_REVENGE",      # internal
    1:  "RO_REASON_STOP_LOSS",    # SL hit
    2:  "RO_REASON_TAKE_PROFIT",  # TP hit
    3:  "RO_REASON_STOP_LIMIT",
    4:  "RO_REASON_FAILED_ACTIVATION",
    5:  "RO_REASON_EXPIRATION",
    6:  "RO_REASON_POSITION_CLOSED",
    7:  "RO_REASON_DEALER",
    8:  "RO_REASON_PIPS",
    9:  "RO_REASON_DIVIDEND",
    10: "RO_REASON_ADMIN",        # admin close
    11: "RO_REASON_MARGIN_CALL",
    12: "RO_REASON_ATR",
    13: "RO_REASON_GSLO",
    14: "RO_REASON_SOFT",
}
ENTRY_MAP = {0: "ENTRY_IN", 1: "ENTRY_OUT", 2: "ENTRY_INOUT"}
TYPE_MAP  = {0: "BUY", 1: "SELL"}

print(f"\n── Deals for position ticket {ticket} ──\n")

deals = mt5.history_deals_get(position=ticket)
if not deals:
    print(f"No deals found for position {ticket}")
    deals = mt5.history_deals_get(ticket=ticket)
    if deals:
        print(f"Found by deal ticket instead:")
    else:
        print(f"No history under deal ticket either.")
        sys.exit(0)

total_profit = 0.0
for d in deals:
    reason_str = DEAL_REASON.get(d.reason, f"UNKNOWN({d.reason})")
    entry_str  = ENTRY_MAP.get(d.entry,  f"entry={d.entry}")
    type_str   = TYPE_MAP.get(d.type,    f"type={d.type}")
    from datetime import datetime
    ts = datetime.fromtimestamp(d.time, tz=None)
    print(f"  deal {d.ticket}  {ts}  {type_str}  {entry_str}")
    print(f"    profit={d.profit}  swap={d.swap}  commission={d.commission}")
    print(f"    reason={reason_str}  comment='{d.comment}'")
    total_profit += d.profit

print(f"\n  Total profit: {total_profit:.2f}\n")

# Also show the position
print("── Position snapshot ──\n")
pos = mt5.position_get(ticket=ticket)
if pos:
    print(f"  symbol    : {pos.symbol}")
    print(f"  type      : {TYPE_MAP.get(pos.type, pos.type)}")
    print(f"  volume    : {pos.volume}")
    print(f"  price_open: {pos.price_open}")
    print(f"  sl        : {pos.sl}")
    print(f"  tp        : {pos.tp}")
    print(f"  price_cur : {pos.price_current}")
    print(f"  profit    : {pos.profit}")
    print(f"  comment   : {pos.comment}")
    print(f"  magic     : {pos.magic}")
else:
    print(f"  Position {ticket} not found (already closed)")

mt5.shutdown()
