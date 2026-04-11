"""Trading Bot — entry point.  All logic moved to orchestrator/bot.py."""

from __future__ import annotations

import os
import sys

# Enable ANSI colour codes on Windows CMD / PowerShell
if sys.platform == "win32":
    os.system("")  # activates VT100 processing for the current console

from orchestrator.bot import TradingBot


if __name__ == "__main__":
    bot = TradingBot()
    bot.startup()
    bot.run()

