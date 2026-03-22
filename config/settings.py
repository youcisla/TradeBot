"""All configurable parameters for the trading bot.

Values are loaded from `.env` where appropriate.  DEMO_MODE is hardcoded
True for Phase 1 — it is NOT read from the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── Mode ─────────────────────────────────────────────────────────────────
DEMO_MODE: bool = True  # Hardcoded for Phase 1 — never change via .env

# ── Broker ───────────────────────────────────────────────────────────────
BROKER_ACCOUNT: str = os.getenv("BROKER_ACCOUNT", "")
BROKER_PASSWORD: str = os.getenv("BROKER_PASSWORD", "")
BROKER_SERVER: str = os.getenv("BROKER_SERVER", "")

# ── Market Data ──────────────────────────────────────────────────────────
ALPHA_VANTAGE_KEY: str = os.getenv("ALPHA_VANTAGE_KEY", "")
TWELVE_DATA_KEY: str = os.getenv("TWELVE_DATA_KEY", "")

# ── Economic Calendar / News Filter ─────────────────────────────────────
NEWS_CALENDAR_SOURCE: str = os.getenv("NEWS_CALENDAR_SOURCE", "static")
FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
NEWS_BLACKOUT_MINUTES: int = int(os.getenv("NEWS_BLACKOUT_MINUTES", "15"))

# ── Telegram ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Security ─────────────────────────────────────────────────────────────
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# ── Trading Council (algorithmic quality gate) ───────────────────────────
# Set COUNCIL_ENABLED=true to activate the three-expert algorithmic debate.
# Signals must score >= COUNCIL_MIN_CONFIDENCE (default 80%) to proceed.
# On unexpected errors the council fails open — trading is never blocked.
COUNCIL_ENABLED: bool = os.getenv("COUNCIL_ENABLED", "false").lower() == "true"
COUNCIL_MIN_CONFIDENCE: float = float(os.getenv("COUNCIL_MIN_CONFIDENCE", "0.80"))

# ── Risk ─────────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.02"))
MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "3"))
MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
MAX_SPREAD_PIPS: float = float(os.getenv("MAX_SPREAD_PIPS", "3.0"))
DRAWDOWN_COOLDOWN_HOURS: int = int(os.getenv("DRAWDOWN_COOLDOWN_HOURS", "24"))
MIN_LOT_SIZE: float = float(os.getenv("MIN_LOT_SIZE", "0.01"))
MAX_LOT_SIZE: float = float(os.getenv("MAX_LOT_SIZE", "5.0"))
# Per-asset-class spread limits.
# Forex/exotic/commodity use pip-based limits.
# Crypto uses a percentage-of-price limit (0.1 = 0.1%) because dollar
# spreads vary wildly across instruments ($17 on BTC vs $0.002 on XRP).
MAX_SPREAD_PCT_CRYPTO: float = float(os.getenv("MAX_SPREAD_PCT_CRYPTO", "2.5"))
MAX_SPREAD_PIPS_COMMODITY: float = float(os.getenv("MAX_SPREAD_PIPS_COMMODITY", "10.0"))
MAX_SPREAD_PIPS_EXOTIC: float = float(os.getenv("MAX_SPREAD_PIPS_EXOTIC", "15.0"))
# ── Trade Execution ──────────────────────────────────────────────────────
TP1_CLOSE_PERCENT: float = float(os.getenv("TP1_CLOSE_PERCENT", "0.40"))
TP2_CLOSE_PERCENT: float = float(os.getenv("TP2_CLOSE_PERCENT", "0.30"))
TP3_CLOSE_PERCENT: float = float(os.getenv("TP3_CLOSE_PERCENT", "0.30"))
TRAILING_STOP_DISTANCE_PIPS: float = float(os.getenv("TRAILING_STOP_DISTANCE_PIPS", "20"))
# Per-asset-class round-trip commission in account currency per standard lot.
# Defaults to 7.0 for all classes; override via .env once PuPrime rates are confirmed.
COMMISSION_PER_LOT: float = float(os.getenv("COMMISSION_PER_LOT", "7.0"))
COMMISSION_PER_LOT_CRYPTO: float = float(os.getenv("COMMISSION_PER_LOT_CRYPTO", "7.0"))
COMMISSION_PER_LOT_COMMODITY: float = float(os.getenv("COMMISSION_PER_LOT_COMMODITY", "7.0"))
COMMISSION_PER_LOT_EXOTIC: float = float(os.getenv("COMMISSION_PER_LOT_EXOTIC", "7.0"))
BREAKEVEN_SPREAD_OFFSET: bool = os.getenv("BREAKEVEN_SPREAD_OFFSET", "true").lower() == "true"

# ── Bot Loop ─────────────────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS: int = int(os.getenv("LOOP_INTERVAL_SECONDS", "60"))
RECONCILE_EVERY_N_LOOPS: int = int(os.getenv("RECONCILE_EVERY_N_LOOPS", "10"))
CANDLE_SERVER_PORT: int = int(os.getenv("CANDLE_SERVER_PORT", "5555"))

# ── Logging ──────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DAILY_SUMMARY_HOUR: int = int(os.getenv("DAILY_SUMMARY_HOUR", "17"))

# ── Learning System ──────────────────────────────────────────────────────
DEFAULT_CONFIDENCE: float = 0.5
INITIAL_CONFIDENCE: float = 0.5
CONFIDENCE_ALLOW: float = 0.3
CONFIDENCE_REDUCED: float = 0.5
CONFIDENCE_FULL: float = 0.7
CONFIDENCE_DISABLE_THRESHOLD: float = 0.2

# ── Data Validation ──────────────────────────────────────────────────────
STUCK_QUOTE_THRESHOLD: int = int(os.getenv("STUCK_QUOTE_THRESHOLD", "10"))
SPIKE_PERCENT_THRESHOLD: float = float(os.getenv("SPIKE_PERCENT_THRESHOLD", "2.0"))

# ── Symbols (default for V1) ────────────────────────────────────────────
DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "EURUSD")
DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "H1")

# ── Neural LSTM Strategy ─────────────────────────────────────────────────
NEURAL_MIN_CONFIDENCE: float = float(os.getenv("NEURAL_MIN_CONFIDENCE", "0.60"))
NEURAL_SEQ_LEN: int          = int(os.getenv("NEURAL_SEQ_LEN", "50"))
NEURAL_TRAIN_YEARS: int      = int(os.getenv("NEURAL_TRAIN_YEARS", "2"))
NEURAL_RETRAIN_EVERY: int    = int(os.getenv("NEURAL_RETRAIN_EVERY", "20"))  # trades
NEURAL_MODELS_DIR: str       = os.getenv("NEURAL_MODELS_DIR", str(Path(__file__).resolve().parent.parent / "models" / "neural"))
NEURAL_TRAIN_EPOCHS: int     = int(os.getenv("NEURAL_TRAIN_EPOCHS", "20"))
NEURAL_HIDDEN_SIZE: int      = int(os.getenv("NEURAL_HIDDEN_SIZE", "64"))
NEURAL_NUM_LAYERS: int       = int(os.getenv("NEURAL_NUM_LAYERS", "2"))

# ── Database ─────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
DB_PATH: str = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "trading_bot.db"))
