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
DEMO_MODE: bool = False  # Hardcoded for Phase 1 — never change via .env

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
# Signals must score >= COUNCIL_MIN_CONFIDENCE to proceed.
# ICT signals get strategy-aware weighting (ICT expert carries 50% weight)
# so the effective bar is already higher for non-ICT strategies.
# Default 60% — do NOT raise above 70% or near-zero trades will result.
# On unexpected errors the council fails open — trading is never blocked.
COUNCIL_ENABLED: bool = os.getenv("COUNCIL_ENABLED", "true").lower() == "true"
COUNCIL_MIN_CONFIDENCE: float = float(os.getenv("COUNCIL_MIN_CONFIDENCE", "0.60"))
# Expert vote weights — must sum to 1.0.
COUNCIL_ICT_WEIGHT: float    = float(os.getenv("COUNCIL_ICT_WEIGHT",    "0.50"))
COUNCIL_DANIAL_WEIGHT: float = float(os.getenv("COUNCIL_DANIAL_WEIGHT", "0.17"))
COUNCIL_TRAD_WEIGHT: float   = float(os.getenv("COUNCIL_TRAD_WEIGHT",   "0.17"))
COUNCIL_WORLD_WEIGHT: float  = float(os.getenv("COUNCIL_WORLD_WEIGHT",  "0.16"))
# Minimum candle count required before the council will vote.
COUNCIL_MIN_CANDLES: int = int(os.getenv("COUNCIL_MIN_CANDLES", "20"))
# Minimum candle count required before the neural strategy will infer.
NEURAL_MIN_CANDLES: int = int(os.getenv("NEURAL_MIN_CANDLES", "65"))
# LSTM architecture & training
NEURAL_SEQ_LEN: int        = int(os.getenv("NEURAL_SEQ_LEN",        "50"))
NEURAL_HIDDEN_SIZE: int    = int(os.getenv("NEURAL_HIDDEN_SIZE",    "128"))
NEURAL_NUM_LAYERS: int     = int(os.getenv("NEURAL_NUM_LAYERS",     "2"))
NEURAL_TRAIN_EPOCHS: int   = int(os.getenv("NEURAL_TRAIN_EPOCHS",   "100"))
NEURAL_RETRAIN_EVERY: int  = int(os.getenv("NEURAL_RETRAIN_EVERY",  "20"))
NEURAL_MIN_CONFIDENCE: float = float(os.getenv("NEURAL_MIN_CONFIDENCE", "0.55"))
NEURAL_MODELS_DIR: str     = os.getenv(
    "NEURAL_MODELS_DIR",
    str(Path(__file__).resolve().parent.parent / "models" / "neural"),
)
# Multi-timeframe candle counts fetched by MarketAgent
# Analysis TFs: M30 (bridge), H1 (main), H4 (structure), D1 (bias)
# Entry TFs:    M15 (trigger), M5/M1 (precision — future)
H4_CANDLE_COUNT: int  = int(os.getenv("H4_CANDLE_COUNT",  "50"))
D1_CANDLE_COUNT: int  = int(os.getenv("D1_CANDLE_COUNT",  "20"))
M30_CANDLE_COUNT: int = int(os.getenv("M30_CANDLE_COUNT", "100"))
M15_CANDLE_COUNT: int = int(os.getenv("M15_CANDLE_COUNT", "100"))
# MTF alignment: confidence boost when all TFs agree, D1 veto when it contradicts
MTF_ALIGNMENT_BOOST: float = float(os.getenv("MTF_ALIGNMENT_BOOST", "0.05"))
MTF_D1_VETO: bool = os.getenv("MTF_D1_VETO", "true").lower() == "true"
# Regime-based confidence adjustment (ranging market penalised)
REGIME_ADX_TRENDING: float  = float(os.getenv("REGIME_ADX_TRENDING",  "25.0"))
REGIME_ADX_RANGING: float   = float(os.getenv("REGIME_ADX_RANGING",   "20.0"))
REGIME_CONFIDENCE_PENALTY: float = float(os.getenv("REGIME_CONFIDENCE_PENALTY", "0.10"))
# Dynamic TP multipliers per regime
TP_TRENDING_TP3_MULT: float = float(os.getenv("TP_TRENDING_TP3_MULT", "4.0"))
TP_TRENDING_TP4_MULT: float = float(os.getenv("TP_TRENDING_TP4_MULT", "6.0"))
TP_RANGING_TP1_MULT: float  = float(os.getenv("TP_RANGING_TP1_MULT",  "0.8"))
TP_RANGING_TP2_MULT: float  = float(os.getenv("TP_RANGING_TP2_MULT",  "1.5"))
# Time-in-trade limit: close stale trades after this many hours with no TP hit
MAX_HOURS_IN_TRADE: int = int(os.getenv("MAX_HOURS_IN_TRADE", "48"))
# Minimum ICT engine score for crypto (lower than forex — crypto lacks killzones
# so the session component caps at 5.0 instead of 7.0, reducing potential max score).
MIN_ICT_SCORE_CRYPTO: float = float(os.getenv("MIN_ICT_SCORE_CRYPTO", "42.0"))

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
# Indices are quoted in points — allow up to 5 points spread (covers typical CFD spread)
MAX_SPREAD_POINTS_INDEX: float = float(os.getenv("MAX_SPREAD_POINTS_INDEX", "5.0"))
# ── Trade Execution ──────────────────────────────────────────────────────
TP1_CLOSE_PERCENT: float = float(os.getenv("TP1_CLOSE_PERCENT", "0.40"))
TP2_CLOSE_PERCENT: float = float(os.getenv("TP2_CLOSE_PERCENT", "0.30"))
TP3_CLOSE_PERCENT: float = float(os.getenv("TP3_CLOSE_PERCENT", "0.20"))
# TP4 is the runner slice held for the HTF liquidity target.
# Carved out of what was previously the full TP3 allocation:
#   TP1=40%, TP2=30%, TP3=20%, TP4=10% → sums to 100%.
TP4_CLOSE_PERCENT: float = float(os.getenv("TP4_CLOSE_PERCENT", "0.10"))
TRAILING_STOP_DISTANCE_PIPS: float = float(os.getenv("TRAILING_STOP_DISTANCE_PIPS", "20"))
# Per-asset-class round-trip commission in account currency per standard lot.
# Defaults to 7.0 for all classes; override via .env once PuPrime rates are confirmed.
COMMISSION_PER_LOT: float = float(os.getenv("COMMISSION_PER_LOT", "7.0"))
COMMISSION_PER_LOT_CRYPTO: float = float(os.getenv("COMMISSION_PER_LOT_CRYPTO", "7.0"))
COMMISSION_PER_LOT_COMMODITY: float = float(os.getenv("COMMISSION_PER_LOT_COMMODITY", "7.0"))
COMMISSION_PER_LOT_EXOTIC: float = float(os.getenv("COMMISSION_PER_LOT_EXOTIC", "7.0"))
BREAKEVEN_SPREAD_OFFSET: bool = os.getenv("BREAKEVEN_SPREAD_OFFSET", "true").lower() == "true"
# Pillar 3 — entry precision gate.
# When ICT snaps entry to an FVG CE or OB midpoint, skip the signal if current
# price is already more than this many ATRs beyond the ideal entry level.
# Forex default: 0.5 ATR.  Crypto gets a larger multiplier because BTCUSD
# moves $100+ per candle; 0.5 ATR would reject almost every setup.
LIMIT_ENTRY_MAX_DISTANCE_ATR: float = float(os.getenv("LIMIT_ENTRY_MAX_DISTANCE_ATR", "0.5"))
LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO: float = float(os.getenv("LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO", "2.0"))

# ── Bot Loop ─────────────────────────────────────────────────────────────
LOOP_INTERVAL_SECONDS: int = int(os.getenv("LOOP_INTERVAL_SECONDS", "30"))
RECONCILE_EVERY_N_LOOPS: int = int(os.getenv("RECONCILE_EVERY_N_LOOPS", "10"))
CANDLE_SERVER_PORT: int = int(os.getenv("CANDLE_SERVER_PORT", "5555"))
# Minimum wall-clock seconds between re-scanning the same symbol.
SCAN_COOLDOWN_SECONDS: int = int(os.getenv("SCAN_COOLDOWN_SECONDS", "300"))
# Symbol auto-disable: after this many consecutive IPC failures the symbol is
# suspended for SYMBOL_DISABLE_SECONDS to avoid wasting loop time.
SYMBOL_MAX_FAIL_COUNT: int = int(os.getenv("SYMBOL_MAX_FAIL_COUNT", "3"))
SYMBOL_DISABLE_SECONDS: int = int(os.getenv("SYMBOL_DISABLE_SECONDS", "3600"))

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

# ── DeepSeek LLM Strategy ────────────────────────────────────────────────
DEEPSEEK_API_KEY:        str   = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL:          str   = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_MIN_CONFIDENCE: float = float(os.getenv("DEEPSEEK_MIN_CONFIDENCE", "0.65"))
# How long (minutes) to reuse a cached signal before re-querying the API.
# One H1 bar = 60 min; default 30 min re-queries twice per bar if the loop
# runs every 5 min but the symbol cooldown is also 5 min.
DEEPSEEK_CACHE_MINUTES:  int   = int(os.getenv("DEEPSEEK_CACHE_MINUTES", "30"))

# ── Analysis Agent indicator periods ────────────────────────────────────
SMA_FAST_PERIOD: int = int(os.getenv("SMA_FAST_PERIOD", "10"))
SMA_SLOW_PERIOD: int = int(os.getenv("SMA_SLOW_PERIOD", "50"))

# ── Database ─────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
DB_PATH: str = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "trading_bot.db"))

# ── Timezone (display only — all internal trading logic stays UTC) ───────
# Used for log timestamps, day-of-week labels, and daily summary scheduling.
# Must be a valid IANA timezone name.  Defaults to Europe/Paris (CET/CEST).
TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")

# ── Weekend / Crypto-only mode ───────────────────────────────────────────
# Symbols scanned during the forex weekend (Friday 22:00 – Sunday 22:00 UTC).
# Crypto markets run 24/7 so the bot stays active but narrows focus.
# Comma-separated, e.g. "BTCUSD" or "BTCUSD,ETHUSD".
WEEKEND_SYMBOLS: str = os.getenv("WEEKEND_SYMBOLS", "BTCUSD")

# ── Crucix World Intelligence (optional) ─────────────────────────────
CRUCIX_URL: str = os.getenv("CRUCIX_URL", "http://localhost:3117")
