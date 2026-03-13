"""Quick MT5 connectivity check."""
import MetaTrader5 as mt5

print("MT5 package version:", mt5.__version__)

if not mt5.initialize():
    print("initialize() failed — error:", mt5.last_error())
    print("Make sure MetaTrader 5 terminal is installed and running.")
    raise SystemExit(1)

print("initialize() OK")

info = mt5.account_info()
if info is None:
    print("account_info() returned None — error:", mt5.last_error())
else:
    print(f"Account:  {info.login}")
    print(f"Server:   {info.server}")
    print(f"Balance:  {info.balance}")
    print(f"Equity:   {info.equity}")
    print(f"Leverage: 1:{info.leverage}")

# Quick tick check
tick = mt5.symbol_info_tick("EURUSD")
if tick:
    print(f"EURUSD:   bid={tick.bid} ask={tick.ask} spread={(tick.ask-tick.bid)*10000:.1f} pips")
else:
    print("EURUSD tick failed:", mt5.last_error())

mt5.shutdown()
print("\nMT5 connection OK — ready for live trading.")
