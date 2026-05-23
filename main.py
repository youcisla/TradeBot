"""Trading Bot — entry point.  All logic moved to orchestrator/bot.py."""

from __future__ import annotations

import logging
import os
import sys
import threading

# Enable ANSI colour codes on Windows CMD / PowerShell
if sys.platform == "win32":
    os.system("")  # activates VT100 processing for the current console

# ── Sentry (must be before any instrumented library) ─────────────────────
from config import settings as _cfg
if _cfg.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_cfg.SENTRY_DSN,
        enable_tracing=True,
        traces_sample_rate=1.0,
        ignore_errors=[KeyboardInterrupt],
    )

from orchestrator.bot import TradingBot
from orchestrator.bot_singleton import set_bot


if __name__ == "__main__":
    bot = TradingBot()
    set_bot(bot)

    # Start FastAPI server in a background thread so the dashboard can
    # reach /api/auth/* while the trading loop runs.
    api_port = int(getattr(_cfg, "API_PORT", 8001))

    def _start_api() -> None:
        import uvicorn
        from api.server import app
        uvicorn.run(app, host="127.0.0.1", port=api_port, log_level="warning")

    api_thread = threading.Thread(target=_start_api, daemon=True, name="FastAPI-server")
    api_thread.start()
    logging.info("FastAPI server started on port %d", api_port)

    try:
        bot.startup()
        bot.run()
    except Exception:
        logging.exception("Fatal error")
        bot.shutdown()
        sys.exit(1)

