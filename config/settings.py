"""All configurable parameters for the trading bot.

Values are loaded from `.env` where appropriate.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── Mode ─────────────────────────────────────────────────────────────────
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

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
# DeepSeek-specific council weighting (must sum to 1.0).
# Rationale: preserve ICT/SnR signal checks while giving more weight to
# traditional + world-context agreement for LLM-originated signals.
COUNCIL_DEEPSEEK_ICT_WEIGHT: float = float(
    os.getenv("COUNCIL_DEEPSEEK_ICT_WEIGHT", "0.15")
)
COUNCIL_DEEPSEEK_DANIAL_WEIGHT: float = float(
    os.getenv("COUNCIL_DEEPSEEK_DANIAL_WEIGHT", "0.15")
)
COUNCIL_DEEPSEEK_TRAD_WEIGHT: float = float(
    os.getenv("COUNCIL_DEEPSEEK_TRAD_WEIGHT", "0.35")
)
COUNCIL_DEEPSEEK_WORLD_WEIGHT: float = float(
    os.getenv("COUNCIL_DEEPSEEK_WORLD_WEIGHT", "0.35")
)
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

# ── Execution lanes (speed vs certainty) ─────────────────────────────────
# Fast lane runs hard safety checks first to minimize signal-to-order latency.
# Full lane then re-checks with all filters and can force-close if needed.
FAST_LANE_ENABLED: bool = os.getenv("FAST_LANE_ENABLED", "true").lower() == "true"
FAST_LANE_MAX_SIGNALS: int = int(os.getenv("FAST_LANE_MAX_SIGNALS", "1"))
FAST_LANE_CLOSE_ON_FULL_REJECT: bool = (
    os.getenv("FAST_LANE_CLOSE_ON_FULL_REJECT", "true").lower() == "true"
)

# Instant entry: enter on signal detection, skip council gate entirely.
# Council runs post-entry as advisory only (non-blocking).
# Only applies when signal confidence >= INSTANT_ENTRY_MIN_CONFIDENCE.
# Signals below that threshold always go through the council gate first.
INSTANT_ENTRY_ENABLED: bool = os.getenv("INSTANT_ENTRY_ENABLED", "true").lower() == "true"
INSTANT_ENTRY_MIN_CONFIDENCE: float = float(os.getenv("INSTANT_ENTRY_MIN_CONFIDENCE", "0.78"))

# Confidence-to-size mapping (borderline setups are sized down, not discarded).
SIZE_SCALE_VERY_LOW_THRESHOLD: float = float(
    os.getenv("SIZE_SCALE_VERY_LOW_THRESHOLD", "0.45")
)
SIZE_SCALE_LOW_THRESHOLD: float = float(
    os.getenv("SIZE_SCALE_LOW_THRESHOLD", "0.60")
)
SIZE_SCALE_MEDIUM_THRESHOLD: float = float(
    os.getenv("SIZE_SCALE_MEDIUM_THRESHOLD", "0.75")
)
SIZE_SCALE_VERY_LOW: float = float(os.getenv("SIZE_SCALE_VERY_LOW", "0.35"))
SIZE_SCALE_LOW: float = float(os.getenv("SIZE_SCALE_LOW", "0.55"))
SIZE_SCALE_MEDIUM: float = float(os.getenv("SIZE_SCALE_MEDIUM", "0.75"))
SIZE_SCALE_FULL: float = float(os.getenv("SIZE_SCALE_FULL", "1.00"))

# Dynamic confidence floors by regime and asset class.
MIN_CONF_TRENDING: float = float(os.getenv("MIN_CONF_TRENDING", "0.48"))
MIN_CONF_RANGING: float = float(os.getenv("MIN_CONF_RANGING", "0.58"))
MIN_CONF_VOLATILE: float = float(os.getenv("MIN_CONF_VOLATILE", "0.62"))
MIN_CONF_UNKNOWN: float = float(os.getenv("MIN_CONF_UNKNOWN", "0.55"))
MIN_CONF_CRYPTO_BONUS: float = float(os.getenv("MIN_CONF_CRYPTO_BONUS", "0.03"))
MIN_CONF_EXOTIC_BONUS: float = float(os.getenv("MIN_CONF_EXOTIC_BONUS", "0.04"))
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
LOOP_INTERVAL_SECONDS: int = int(os.getenv("LOOP_INTERVAL_SECONDS", "5"))
RECONCILE_EVERY_N_LOOPS: int = int(os.getenv("RECONCILE_EVERY_N_LOOPS", "10"))
CANDLE_SERVER_PORT: int = int(os.getenv("CANDLE_SERVER_PORT", "5555"))
# Minimum wall-clock seconds between re-scanning the same symbol.
SCAN_COOLDOWN_SECONDS: int = int(os.getenv("SCAN_COOLDOWN_SECONDS", "300"))
# Session-profiled cooldown (London/NY scans faster, Asia scans slower).
SCAN_COOLDOWN_SECONDS_LONDON_NY: int = int(
    os.getenv("SCAN_COOLDOWN_SECONDS_LONDON_NY", "60")
)
SCAN_COOLDOWN_SECONDS_ASIA: int = int(
    os.getenv("SCAN_COOLDOWN_SECONDS_ASIA", "120")
)
# BTC priority scheduler: scan this symbol first and more frequently while
# still scanning the full symbol universe.
BTC_PRIORITY_SYMBOL: str = os.getenv("BTC_PRIORITY_SYMBOL", "BTCUSD")
BTC_PRIORITY_SCAN_COOLDOWN_SECONDS: int = int(
    os.getenv("BTC_PRIORITY_SCAN_COOLDOWN_SECONDS", "15")
)
EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE: bool = (
    os.getenv("EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE", "true").lower() == "true"
)

# MarketAgent higher-timeframe cache tuning by session profile.
HTF_CACHE_TTL_M15_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_M15_SECONDS", "20"))
HTF_CACHE_TTL_M30_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_M30_SECONDS", "30"))
HTF_CACHE_TTL_H4_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_H4_SECONDS", "120"))
HTF_CACHE_TTL_D1_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_D1_SECONDS", "300"))
HTF_CACHE_TTL_MULTIPLIER_LONDON_NY: float = float(
    os.getenv("HTF_CACHE_TTL_MULTIPLIER_LONDON_NY", "0.75")
)
HTF_CACHE_TTL_MULTIPLIER_ASIA: float = float(
    os.getenv("HTF_CACHE_TTL_MULTIPLIER_ASIA", "1.35")
)

# Deferred-entry queue: keep quality setups warm until price revisits entry.
DEFERRED_ENTRY_ENABLED: bool = os.getenv("DEFERRED_ENTRY_ENABLED", "true").lower() == "true"
DEFERRED_ENTRY_MAX_AGE_SECONDS: int = int(
    os.getenv("DEFERRED_ENTRY_MAX_AGE_SECONDS", "900")
)
DEFERRED_ENTRY_MAX_ATR_DISTANCE: float = float(
    os.getenv("DEFERRED_ENTRY_MAX_ATR_DISTANCE", "0.35")
)
DEFERRED_ENTRY_MIN_CONF: float = float(os.getenv("DEFERRED_ENTRY_MIN_CONF", "0.60"))
DEFERRED_ENTRY_TTL_SECONDS: int = int(os.getenv("DEFERRED_ENTRY_TTL_SECONDS", "900"))
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

# KPI cadence for opportunity-capture telemetry in logs/agent feed.
METRICS_LOG_EVERY_N_LOOPS: int = int(os.getenv("METRICS_LOG_EVERY_N_LOOPS", "5"))

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
DEEPSEEK_SCHEMA_VERSION: str = os.getenv("DEEPSEEK_SCHEMA_VERSION", "v1")
# How long (minutes) to reuse a cached signal before re-querying the API.
# One H1 bar = 60 min; default 30 min re-queries twice per bar if the loop
# runs every 5 min but the symbol cooldown is also 5 min.
DEEPSEEK_CACHE_MINUTES:  int   = int(os.getenv("DEEPSEEK_CACHE_MINUTES", "30"))
# Allowed relative deviation for 1R/2R/3R TP checks from model output.
# Example: 0.25 means +/-25% tolerance around expected R multiples.
DEEPSEEK_R_MULT_TOLERANCE: float = float(
    os.getenv("DEEPSEEK_R_MULT_TOLERANCE", "0.25")
)
# Quality telemetry cadence (in DeepSeek detect calls).
DEEPSEEK_METRICS_LOG_EVERY: int = int(os.getenv("DEEPSEEK_METRICS_LOG_EVERY", "25"))

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

# ── Session / Day quality gates ─────────────────────────────────────────
# Comma-separated sessions to ALLOW entries in.  Empty string = no gate.
# Winning session pattern (from trade history): asian, overlap.
# London and New York have 0% win rate in observed data.
# Valid values: asian, london, new_york, overlap, off_hours
ENTRY_ALLOWED_SESSIONS: list = [
    s.strip() for s in os.getenv("ENTRY_ALLOWED_SESSIONS", "asian,overlap").split(",")
    if s.strip()
]
# Days to BLOCK entries.  Saturday and Sunday show 0–11% win rates.
ENTRY_BLOCKED_DAYS: list = [
    d.strip() for d in os.getenv("ENTRY_BLOCKED_DAYS", "Saturday,Sunday").split(",")
    if d.strip()
]
# Minimum MTF alignment fraction (0.0–1.0) required for entry.
# 0.75 = at least 3 of 4 analysis timeframes must agree with signal direction.
# Set 0.0 to disable.
MTF_MIN_ALIGNMENT: float = float(os.getenv("MTF_MIN_ALIGNMENT", "0.0"))

# ── Weekend / Crypto-only mode ───────────────────────────────────────────
# Symbols scanned during the forex weekend (Friday 22:00 – Sunday 22:00 UTC).
# Crypto markets run 24/7 so the bot stays active but narrows focus.
# Comma-separated, e.g. "BTCUSD" or "BTCUSD,ETHUSD".
WEEKEND_SYMBOLS: str = os.getenv("WEEKEND_SYMBOLS", "BTCUSD")

# ── Crucix World Intelligence (optional) ─────────────────────────────
CRUCIX_URL: str = os.getenv("CRUCIX_URL", "http://localhost:3117")
