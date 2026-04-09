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
# Runtime profile selector. Keep "custom" to respect raw .env values.
# Supported: custom, dev, paper, live-safe, live-full
BOT_PROFILE: str = os.getenv("BOT_PROFILE", "custom").strip().lower()

# ── Broker ───────────────────────────────────────────────────────────────
BROKER_ACCOUNT: str = os.getenv("BROKER_ACCOUNT", "")
BROKER_PASSWORD: str = os.getenv("BROKER_PASSWORD", "")
BROKER_SERVER: str = os.getenv("BROKER_SERVER", "")

# ── Market Data ──────────────────────────────────────────────────────────
ALPHA_VANTAGE_KEY: str = os.getenv("ALPHA_VANTAGE_KEY", "")
TWELVE_DATA_KEY: str = os.getenv("TWELVE_DATA_KEY", "")

# ── Intelligence Sweep / FRED / yfinance ─────────────────────────────────
FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
YFINANCE_ENABLED: bool = os.getenv("YFINANCE_ENABLED", "true").lower() == "true"
INTELLIGENCE_SWEEP_INTERVAL_MINUTES: int = int(
    os.getenv("INTELLIGENCE_SWEEP_INTERVAL_MINUTES", "15")
)

# ── OpenRouter LLM Gateway ───────────────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
OPENROUTER_FALLBACK_ENABLED: bool = (
    os.getenv("OPENROUTER_FALLBACK_ENABLED", "false").lower() == "true"
)

# ── Guard Pipeline ───────────────────────────────────────────────────────
GUARD_PIPELINE_ENABLED: bool = (
    os.getenv("GUARD_PIPELINE_ENABLED", "true").lower() == "true"
)
GUARD_COOLDOWN_SECONDS: int = int(os.getenv("GUARD_COOLDOWN_SECONDS", "300"))
GUARD_MAX_DAILY_LOSS_PCT: float = float(os.getenv("GUARD_MAX_DAILY_LOSS_PCT", "0.05"))
GUARD_MAX_VIX: float = float(os.getenv("GUARD_MAX_VIX", "40.0"))
GUARD_FEED_STALENESS_SECONDS: float = float(
    os.getenv("GUARD_FEED_STALENESS_SECONDS", "120")
)

# ── Backtesting ──────────────────────────────────────────────────────────
BACKTEST_COMMISSION_PER_LOT_PER_SIDE: float = float(
    os.getenv("BACKTEST_COMMISSION_PER_LOT_PER_SIDE", "0.0001")
)
BACKTEST_WALK_FORWARD_ENABLED: bool = (
    os.getenv("BACKTEST_WALK_FORWARD_ENABLED", "false").lower() == "true"
)
BACKTEST_WALK_FORWARD_WINDOW_DAYS: int = int(
    os.getenv("BACKTEST_WALK_FORWARD_WINDOW_DAYS", "90")
)

# ── ML Enhancements ──────────────────────────────────────────────────────
KALMAN_ENABLED: bool = os.getenv("KALMAN_ENABLED", "true").lower() == "true"
GARCH_ENABLED: bool = os.getenv("GARCH_ENABLED", "true").lower() == "true"
GARCH_HIGH_VOL_THRESHOLD: float = float(os.getenv("GARCH_HIGH_VOL_THRESHOLD", "2.0"))
LGBM_ENSEMBLE_ENABLED: bool = (
    os.getenv("LGBM_ENSEMBLE_ENABLED", "true").lower() == "true"
)
HEDGE_STRIP_ENABLED: bool = (
    os.getenv("HEDGE_STRIP_ENABLED", "true").lower() == "true"
)

# ── MCP Server ───────────────────────────────────────────────────────────
MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8080"))
MCP_SERVER_ENABLED: bool = (
    os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"
)

# ── Economic Calendar / News Filter ─────────────────────────────────────
NEWS_CALENDAR_SOURCE: str = os.getenv("NEWS_CALENDAR_SOURCE", "static")
FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
NEWS_BLACKOUT_MINUTES: int = int(os.getenv("NEWS_BLACKOUT_MINUTES", "15"))

# ── Telegram ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_NOISE_FILTER_ENABLED: bool = (
    os.getenv("TELEGRAM_NOISE_FILTER_ENABLED", "true").lower() == "true"
)
TELEGRAM_DEDUPE_WINDOW_SECONDS: int = int(
    os.getenv("TELEGRAM_DEDUPE_WINDOW_SECONDS", "180")
)
TELEGRAM_RATE_LIMIT_PER_MINUTE: int = int(
    os.getenv("TELEGRAM_RATE_LIMIT_PER_MINUTE", "20")
)
TELEGRAM_SUPPRESSION_REPORT_EVERY: int = int(
    os.getenv("TELEGRAM_SUPPRESSION_REPORT_EVERY", "10")
)
TELEGRAM_CHART_DAYS: int = int(os.getenv("TELEGRAM_CHART_DAYS", "30"))
TELEGRAM_ALLOWED_USERNAMES: tuple[str, ...] = tuple(
    u.strip().lstrip("@").lower()
    for u in os.getenv("TELEGRAM_ALLOWED_USERNAMES", "").replace(";", ",").split(",")
    if u.strip()
)
TELEGRAM_ALLOWED_USER_IDS: tuple[int, ...] = tuple(
    int(v.strip())
    for v in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").replace(";", ",").split(",")
    if v.strip().isdigit()
)

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
# Council decision mode:
# - blocking: veto trade when council rejects (classic behavior)
# - advisory: council still scores/reasons but does not block execution
COUNCIL_MODE: str = os.getenv("COUNCIL_MODE", "advisory").lower()
# Hard cap to avoid council latency exploding in signal-heavy loops.
# Set to 0 to skip in-loop council reviews entirely.
COUNCIL_MAX_REVIEWS_PER_LOOP: int = int(os.getenv("COUNCIL_MAX_REVIEWS_PER_LOOP", "3"))
# In advisory mode, optionally haircut confidence when council disagrees.
COUNCIL_ADVISORY_REJECTION_CONF_PENALTY: float = float(
    os.getenv("COUNCIL_ADVISORY_REJECTION_CONF_PENALTY", "0.08")
)
# Advisory mode viability floor — any signal with council vote below this
# is fully blocked rather than penalized and continued.
COUNCIL_ADVISORY_MIN_VIABILITY: float = float(
    os.getenv("COUNCIL_ADVISORY_MIN_VIABILITY", "0.45")
)
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
# Minimum ICT confluence score (0-70) for a valid ICT/SMC signal.
# ICT score < 40 AND no SMC confirmation always returns NONE.
ICT_MIN_CONFIDENCE: int = int(os.getenv("ICT_MIN_CONFIDENCE", "30"))

# ── Bull/Bear Debate Agent ───────────────────────────────────────────────
# Set DEBATE_ENABLED=true to run a pre-trade LLM bull/bear debate.
# The debate adjusts signal confidence but never blocks trading on LLM failure.
# Requires OPENROUTER_API_KEY.  Each call costs 1 LLM request per signal.
DEBATE_ENABLED: bool = os.getenv("DEBATE_ENABLED", "false").lower() == "true"
# Override the LLM used for debates (empty = inherit OPENROUTER_MODEL).
DEBATE_LLM_MODEL: str = os.getenv("DEBATE_LLM_MODEL", "")
# Hard timeout per debate call.  Keep well below signal loop latency.
DEBATE_TIMEOUT_SECONDS: int = int(os.getenv("DEBATE_TIMEOUT_SECONDS", "8"))
# bear_score threshold to issue a SKIP verdict (confidence −25 %).
DEBATE_BEAR_VETO_THRESHOLD: float = float(os.getenv("DEBATE_BEAR_VETO_THRESHOLD", "0.75"))
# bear_score threshold to issue a CAUTIOUS verdict (confidence −10 %).
DEBATE_BEAR_CAUTION_THRESHOLD: float = float(os.getenv("DEBATE_BEAR_CAUTION_THRESHOLD", "0.60"))

# ── Exposure Coach ───────────────────────────────────────────────────────
# Synthesises 8 market-environment signals (P&L, open-count, GARCH vol,
# macro regime, correlation, session, win-rate, LGBM confidence) into a
# single exposure directive.  Enable with EXPOSURE_ENABLED=true.
# Signals blocked by REDUCE_ONLY or CASH_PRIORITY are logged; a coach
# failure always falls back to NEW_ENTRY_ALLOWED (fail-open).
EXPOSURE_ENABLED: bool = os.getenv("EXPOSURE_ENABLED", "false").lower() == "true"
# Composite score below this threshold → REDUCE_ONLY (no new entries).
EXPOSURE_REDUCE_THRESHOLD: float = float(os.getenv("EXPOSURE_REDUCE_THRESHOLD", "0.40"))
# Composite score below this threshold → CASH_PRIORITY (protect capital).
EXPOSURE_CASH_THRESHOLD: float = float(os.getenv("EXPOSURE_CASH_THRESHOLD", "0.20"))
# Number of recent closed trades used for the win-rate look-back window.
EXPOSURE_WIN_RATE_LOOKBACK: int = int(os.getenv("EXPOSURE_WIN_RATE_LOOKBACK", "10"))

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
M5_CANDLE_COUNT: int = int(os.getenv("M5_CANDLE_COUNT", "100"))
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
MIN_ICT_SCORE_CRYPTO: float = float(os.getenv("MIN_ICT_SCORE_CRYPTO", "35.0"))

# ── Risk ─────────────────────────────────────────────────────────────────
MAX_RISK_PER_TRADE: float = float(os.getenv("MAX_RISK_PER_TRADE", "0.02"))
MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "12"))
MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "0.05"))
MAX_MONTHLY_LOSS: float = float(os.getenv("MAX_MONTHLY_LOSS", "0.10"))  # MT5_Trade_Connector RiskManagement_v1 pattern
MAX_SPREAD_PIPS: float = float(os.getenv("MAX_SPREAD_PIPS", "8.0"))
DRAWDOWN_COOLDOWN_HOURS: int = int(os.getenv("DRAWDOWN_COOLDOWN_HOURS", "24"))
MIN_LOT_SIZE: float = float(os.getenv("MIN_LOT_SIZE", "0.01"))
MAX_LOT_SIZE: float = float(os.getenv("MAX_LOT_SIZE", "50.0"))

# ── Scalp-specific risk limits ───────────────────────────────────────────────
# Scalp trades (scalp_m5 strategy) use tighter SL → larger lots for same $ risk.
# These caps prevent scalp from consuming disproportionate balance.
SCALP_MAX_LOT_SIZE: float = float(os.getenv("SCALP_MAX_LOT_SIZE", "0.50"))
SCALP_MAX_CONCURRENT: int = int(os.getenv("SCALP_MAX_CONCURRENT", "2"))
SCALP_MAX_TRADES_PER_HOUR: int = int(os.getenv("SCALP_MAX_TRADES_PER_HOUR", "4"))
SCALP_DAILY_LOSS_LIMIT: float = float(os.getenv("SCALP_DAILY_LOSS_LIMIT", "0.02"))  # 2% of balance
# Position sizing mode (MT5-style modes):
# - equity_pct        : risk percent of equity (default)
# - balance_pct       : risk percent of balance
# - fixed_lot         : always use POSITION_SIZE_FIXED_LOT
# - fixed_risk_amount : fixed account-currency amount risked per trade
POSITION_SIZE_MODE: str = os.getenv("POSITION_SIZE_MODE", "equity_pct").lower()
POSITION_SIZE_FIXED_LOT: float = float(os.getenv("POSITION_SIZE_FIXED_LOT", "0.10"))
POSITION_SIZE_FIXED_RISK_AMOUNT: float = float(
    os.getenv("POSITION_SIZE_FIXED_RISK_AMOUNT", "100.0")
)
# Kelly Criterion position sizing (POSITION_SIZE_MODE=kelly).
# Half-Kelly is applied by default (KELLY_HALF=true) to prevent over-betting.
# Falls back to equity_pct when fewer than KELLY_MIN_TRADES are available.
KELLY_MIN_TRADES: int = int(os.getenv("KELLY_MIN_TRADES", "20"))
KELLY_LOOKBACK_DAYS: int = int(os.getenv("KELLY_LOOKBACK_DAYS", "90"))
KELLY_HALF: bool = os.getenv("KELLY_HALF", "true").lower() == "true"
# Per-asset-class spread limits.
# Forex/exotic/commodity use pip-based limits.
# Crypto uses a percentage-of-price limit (0.1 = 0.1%) because dollar
# spreads vary wildly across instruments ($17 on BTC vs $0.002 on XRP).
MAX_SPREAD_PCT_CRYPTO: float = float(os.getenv("MAX_SPREAD_PCT_CRYPTO", "2.5"))
MAX_SPREAD_PIPS_COMMODITY: float = float(os.getenv("MAX_SPREAD_PIPS_COMMODITY", "10.0"))
MAX_SPREAD_PIPS_EXOTIC: float = float(os.getenv("MAX_SPREAD_PIPS_EXOTIC", "15.0"))
# Indices are quoted in points — allow up to 5 points spread (covers typical CFD spread)
MAX_SPREAD_POINTS_INDEX: float = float(os.getenv("MAX_SPREAD_POINTS_INDEX", "5.0"))

# Risk behavior profile:
# - strict: all gates enforced
# - balanced: default production posture
# - agile: looser entry gating for high-confidence opportunities
RISK_VALIDATION_PROFILE: str = os.getenv("RISK_VALIDATION_PROFILE", "agile").lower()
# Confidence level considered "high-quality" when agile profile is active.
RISK_AGILE_HIGH_CONF_THRESHOLD: float = float(
    os.getenv("RISK_AGILE_HIGH_CONF_THRESHOLD", "0.74")
)
# Spread multiplier in agile mode for high-confidence setups.
RISK_AGILE_SPREAD_MULTIPLIER: float = float(
    os.getenv("RISK_AGILE_SPREAD_MULTIPLIER", "1.35")
)

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

# ── Sniper Entry (Fibonacci pullback gate) ───────────────────────────────
# Replaces the Council/DeepSeek gate with a deterministic Fibonacci-based
# confidence split:
#   conf >= SNIPER_CONF_THRESHOLD  → instant execution (no waiting)
#   conf <  SNIPER_CONF_THRESHOLD  → wait for pullback into Fibonacci zone
#     → if price pulls back to a valid retracement (38.2%–78.6%) → execute
#     → if timeout reached or price moves past zone → skip
SNIPER_ENTRY_ENABLED: bool = os.getenv("SNIPER_ENTRY_ENABLED", "true").lower() == "true"
# Minimum ICT confidence to qualify for instant (no-wait) execution.
SNIPER_CONF_THRESHOLD: float = float(os.getenv("SNIPER_CONF_THRESHOLD", "0.55"))
# Maximum time to wait on watchlist for a pullback before skipping.
SNIPER_TIMEOUT_MINUTES: float = float(os.getenv("SNIPER_TIMEOUT_MINUTES", "30.0"))
# Maximum distance price can move past entry zone before signal is skipped.
# Expressed as a multiple of ATR.  BUY: price above entry + this × ATR = stale.
# SELL: price below entry - this × ATR = stale.
SNIPER_MAX_ENTRY_ATR_DISTANCE: float = float(os.getenv("SNIPER_MAX_ENTRY_ATR_DISTANCE", "0.55"))
# Fibonacci retracement depths accepted for sniper entry.
# "golden_zone" (0.618–0.705) is optimal; "acceptable" (0.382–0.618) also valid.
# Deeper pullbacks ("deep" = 0.705–0.786) are riskier but still allowed.
SNIPER_FIB_MIN_DEPTH: str = os.getenv("SNIPER_FIB_MIN_DEPTH", "acceptable")
SNIPER_FIB_MAX_DEPTH: str = os.getenv("SNIPER_FIB_MAX_DEPTH", "deep")

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
MIN_CONF_TRENDING: float = float(os.getenv("MIN_CONF_TRENDING", "0.40"))
MIN_CONF_RANGING: float = float(os.getenv("MIN_CONF_RANGING", "0.40"))
MIN_CONF_VOLATILE: float = float(os.getenv("MIN_CONF_VOLATILE", "0.40"))
MIN_CONF_UNKNOWN: float = float(os.getenv("MIN_CONF_UNKNOWN", "0.40"))
MIN_CONF_CRYPTO_BONUS: float = float(os.getenv("MIN_CONF_CRYPTO_BONUS", "0.03"))
MIN_CONF_EXOTIC_BONUS: float = float(os.getenv("MIN_CONF_EXOTIC_BONUS", "0.04"))

# Time-phase confidence gate (optional).
# Useful for strategies built around fixed-time candles (e.g. 15m):
# early phase can require stricter confidence than late phase.
TIME_PHASE_CONFIDENCE_ENABLED: bool = (
    os.getenv("TIME_PHASE_CONFIDENCE_ENABLED", "false").lower() == "true"
)
TIME_PHASE_BUCKET_MINUTES: int = int(os.getenv("TIME_PHASE_BUCKET_MINUTES", "15"))
TIME_PHASE_EARLY_MAX_MINUTE: int = int(os.getenv("TIME_PHASE_EARLY_MAX_MINUTE", "3"))
TIME_PHASE_MID_MAX_MINUTE: int = int(os.getenv("TIME_PHASE_MID_MAX_MINUTE", "11"))
TIME_PHASE_MIN_CONF_EARLY: float = float(os.getenv("TIME_PHASE_MIN_CONF_EARLY", "0.55"))
TIME_PHASE_MIN_CONF_MID: float = float(os.getenv("TIME_PHASE_MIN_CONF_MID", "0.50"))
TIME_PHASE_MIN_CONF_LATE: float = float(os.getenv("TIME_PHASE_MIN_CONF_LATE", "0.48"))

# Protection layer (Freqtrade-style guards for overtrading / loss streaks).
PROTECTIONS_ENABLED: bool = os.getenv("PROTECTIONS_ENABLED", "true").lower() == "true"
# Per-symbol cooldown after a close before allowing re-entry.
PROTECTION_COOLDOWN_MINUTES: int = int(os.getenv("PROTECTION_COOLDOWN_MINUTES", "10"))
# Per-symbol stoploss guard: lock symbol when too many SL closes in lookback.
PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES: int = int(
    os.getenv("PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES", "180")
)
PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT: int = int(
    os.getenv("PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT", "3")
)
PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES: int = int(
    os.getenv("PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES", "60")
)
# Global recent-loss guard: lock all entries on clustered losses.
PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES: int = int(
    os.getenv("PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES", "120")
)
PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES: int = int(
    os.getenv("PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES", "4")
)
PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES: int = int(
    os.getenv("PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES", "45")
)
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
RECONCILE_EVERY_N_LOOPS: int = int(os.getenv("RECONCILE_EVERY_N_LOOPS", "60"))
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
    os.getenv("BTC_PRIORITY_SCAN_COOLDOWN_SECONDS", "8")
)
EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE: bool = (
    os.getenv("EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE", "true").lower() == "true"
)

# Opportunity lifecycle orchestration (inspired by short-horizon two-leg flows).
OPPORTUNITY_PHASE_ENABLED: bool = (
    os.getenv("OPPORTUNITY_PHASE_ENABLED", "true").lower() == "true"
)
OPPORTUNITY_ROLLOVER_SECONDS: int = int(
    os.getenv("OPPORTUNITY_ROLLOVER_SECONDS", "900")
)
OPPORTUNITY_WATCH_WINDOW_SECONDS: int = int(
    os.getenv("OPPORTUNITY_WATCH_WINDOW_SECONDS", "180")
)
OPPORTUNITY_HEDGE_TIMEOUT_SECONDS: int = int(
    os.getenv("OPPORTUNITY_HEDGE_TIMEOUT_SECONDS", "300")
)
OPPORTUNITY_MIN_RECOVERY_CONFIDENCE: float = float(
    os.getenv("OPPORTUNITY_MIN_RECOVERY_CONFIDENCE", "0.62")
)
OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT: float = float(
    os.getenv("OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT", "0.003")
)
OPPORTUNITY_SHOCK_LOOKBACK_SECONDS: int = int(
    os.getenv("OPPORTUNITY_SHOCK_LOOKBACK_SECONDS", "5")
)
OPPORTUNITY_SHOCK_DROP_THRESHOLD: float = float(
    os.getenv("OPPORTUNITY_SHOCK_DROP_THRESHOLD", "0.0015")
)
OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE: bool = (
    os.getenv("OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE", "true").lower() == "true"
)
# Simulation-first guard for newly introduced lifecycle logic.
# In live mode, the opportunity lifecycle is disabled unless explicitly enabled.
OPPORTUNITY_LIVE_ENABLED: bool = (
    os.getenv("OPPORTUNITY_LIVE_ENABLED", "false").lower() == "true"
)

# MarketAgent higher-timeframe cache tuning by session profile.
HTF_CACHE_TTL_M15_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_M15_SECONDS", "20"))
HTF_CACHE_TTL_M5_SECONDS: float = float(os.getenv("HTF_CACHE_TTL_M5_SECONDS", "15"))
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

# ── Multi-agent orchestration optimization ──────────────────────────────
# Non-MT5 brokers can safely parallelize symbol scans. Keep MT5 sequential
# because the MT5 bridge is thread-sensitive.
ORCHESTRATION_SCAN_WORKERS_MIN: int = int(
    os.getenv("ORCHESTRATION_SCAN_WORKERS_MIN", "2")
)
ORCHESTRATION_SCAN_WORKERS_MAX: int = int(
    os.getenv("ORCHESTRATION_SCAN_WORKERS_MAX", "10")
)
ORCHESTRATION_SCAN_WORKERS_DEFAULT: int = int(
    os.getenv("ORCHESTRATION_SCAN_WORKERS_DEFAULT", "6")
)
# Adaptive tuning is reversible and bounded by min/max workers.
ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED: bool = (
    os.getenv("ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED", "true").lower() == "true"
)
# Performance goals (ms) used for feedback control and bottleneck alerts.
ORCHESTRATION_TARGET_SCAN_MS: float = float(
    os.getenv("ORCHESTRATION_TARGET_SCAN_MS", "15000")
)
ORCHESTRATION_TARGET_RANK_MS: float = float(
    os.getenv("ORCHESTRATION_TARGET_RANK_MS", "200")
)
ORCHESTRATION_TARGET_EXEC_MS: float = float(
    os.getenv("ORCHESTRATION_TARGET_EXEC_MS", "800")
)
ORCHESTRATION_TARGET_TOTAL_MS: float = float(
    os.getenv("ORCHESTRATION_TARGET_TOTAL_MS", "60000")
)
# Hard cap on ranked signals processed per loop to prevent runaway loops.
ORCHESTRATION_MAX_SIGNALS_PER_ITERATION: int = int(
    os.getenv("ORCHESTRATION_MAX_SIGNALS_PER_ITERATION", "20")
)
# Emit traceable iteration lifecycle events to DB logs.
ORCHESTRATION_ENABLE_ITERATION_TRACE: bool = (
    os.getenv("ORCHESTRATION_ENABLE_ITERATION_TRACE", "true").lower() == "true"
)
# Graceful degradation: if scan failures exceed this ratio in one loop,
# skip ranking/execution for that loop and retry next cycle.
ORCHESTRATION_SCAN_ERROR_RATE_ABORT: float = float(
    os.getenv("ORCHESTRATION_SCAN_ERROR_RATE_ABORT", "0.70")
)
ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES: int = int(
    os.getenv("ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES", "5")
)
# Hard stage budgets (ms). When exceeded, orchestration degrades gracefully
# by skipping optional gates and/or stopping further ranked processing.
ORCHESTRATION_HARD_BUDGET_ENABLED: bool = (
    os.getenv("ORCHESTRATION_HARD_BUDGET_ENABLED", "true").lower() == "true"
)
ORCHESTRATION_MAX_SCAN_MS: float = float(
    os.getenv("ORCHESTRATION_MAX_SCAN_MS", "90000")
)
ORCHESTRATION_MAX_RANK_MS: float = float(
    os.getenv("ORCHESTRATION_MAX_RANK_MS", "1000")
)
ORCHESTRATION_MAX_EXEC_MS: float = float(
    os.getenv("ORCHESTRATION_MAX_EXEC_MS", "3000")
)
ORCHESTRATION_MAX_ITERATION_MS: float = float(
    os.getenv("ORCHESTRATION_MAX_ITERATION_MS", "120000")
)
# Safety margin: when remaining execution budget is below this threshold,
# skip council reviews to preserve order-placement latency.
ORCHESTRATION_EXEC_BUDGET_COUNCIL_MARGIN_MS: float = float(
    os.getenv("ORCHESTRATION_EXEC_BUDGET_COUNCIL_MARGIN_MS", "350")
)

# ── Data Validation ──────────────────────────────────────────────────────
STUCK_QUOTE_THRESHOLD: int = int(os.getenv("STUCK_QUOTE_THRESHOLD", "10"))
STUCK_QUOTE_THRESHOLD_CRYPTO: int = int(
    os.getenv("STUCK_QUOTE_THRESHOLD_CRYPTO", "14")
)
SPIKE_PERCENT_THRESHOLD: float = float(os.getenv("SPIKE_PERCENT_THRESHOLD", "2.0"))

# ── Execution hard-failure backoff ───────────────────────────────────────
# MT5 10017/10027 indicates terminal-level autotrading disabled.
# Backing off avoids hammering the terminal with repeated failed sends.
EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS: int = int(
    os.getenv("EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS", "300")
)
# Pending-order confirmation watchdog:
# after order_send succeeds, wait up to this timeout for the ticket to appear
# in broker open positions; if it never appears, execution escalates and
# attempts an emergency close to avoid phantom/open-state divergence.
EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS: float = float(
    os.getenv("EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS", "4.0")
)
EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS: float = float(
    os.getenv("EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS", "0.25")
)

# ── Spread rejection cooldown ────────────────────────────────────────────
# If a symbol repeatedly fails spread checks, temporarily cool it down
# to avoid wasting loops on the same reject condition.
SPREAD_REJECT_COOLDOWN_HITS: int = int(
    os.getenv("SPREAD_REJECT_COOLDOWN_HITS", "3")
)
SPREAD_REJECT_COOLDOWN_SECONDS: int = int(
    os.getenv("SPREAD_REJECT_COOLDOWN_SECONDS", "300")
)

# ── Autonomous tool system ──────────────────────────────────────────────
# Enables a built-in tool registry that can run diagnostics and
# corrective actions on a schedule from inside the main trading loop.
TOOL_SYSTEM_ENABLED: bool = os.getenv("TOOL_SYSTEM_ENABLED", "true").lower() == "true"
TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS: int = int(
    os.getenv("TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS", "5")
)
TOOL_SYSTEM_STRICT_CRITICAL: bool = (
    os.getenv("TOOL_SYSTEM_STRICT_CRITICAL", "true").lower() == "true"
)
TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE: int = int(
    os.getenv("TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE", "8")
)
TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD: int = int(
    os.getenv("TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD", "2")
)
TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES: int = int(
    os.getenv("TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES", "2")
)
TOOL_SYSTEM_EMERGENCY_SYMBOLS: str = os.getenv(
    "TOOL_SYSTEM_EMERGENCY_SYMBOLS",
    "BTCUSD,ETHUSD,XAUUSD,EURUSD",
)
TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE: float = float(
    os.getenv("TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE", "0.005")
)
TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES: int = int(
    os.getenv("TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES", "1")
)
TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS: int = int(
    os.getenv("TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS", "48")
)
TOOL_SYSTEM_REWEIGHT_MIN_TRADES: int = int(
    os.getenv("TOOL_SYSTEM_REWEIGHT_MIN_TRADES", "4")
)

# ── Symbols (default for V1) ────────────────────────────────────────────
DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "BTCUSD")
DEFAULT_TIMEFRAME: str = os.getenv("DEFAULT_TIMEFRAME", "H1")

# ── DeepSeek LLM Strategy ────────────────────────────────────────────────
DEEPSEEK_API_KEY:        str   = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL:          str   = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_QUICK_MODEL:    str   = os.getenv("DEEPSEEK_QUICK_MODEL", DEEPSEEK_MODEL)
DEEPSEEK_DEEP_MODEL:     str   = os.getenv("DEEPSEEK_DEEP_MODEL", "deepseek-reasoner")
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
DEEPSEEK_QUICK_TIMEOUT_SECONDS: float = float(
    os.getenv("DEEPSEEK_QUICK_TIMEOUT_SECONDS", "10")
)
DEEPSEEK_DEEP_TIMEOUT_SECONDS: float = float(
    os.getenv("DEEPSEEK_DEEP_TIMEOUT_SECONDS", "8")
)
DEEPSEEK_ENABLE_DEEP_VERIFY: bool = (
    os.getenv("DEEPSEEK_ENABLE_DEEP_VERIFY", "true").lower() == "true"
)
DEEPSEEK_DEEP_VERIFY_MIN_CONFIDENCE: float = float(
    os.getenv("DEEPSEEK_DEEP_VERIFY_MIN_CONFIDENCE", "0.78")
)
# Optional multi-agent mode: run multiple specialized LLM roles in parallel
# and aggregate to a single consensus signal.
DEEPSEEK_AGENT_SWARM_ENABLED: bool = (
    os.getenv("DEEPSEEK_AGENT_SWARM_ENABLED", "false").lower() == "true"
)
DEEPSEEK_AGENT_SWARM_MAX_AGENTS: int = int(
    os.getenv("DEEPSEEK_AGENT_SWARM_MAX_AGENTS", "3")
)
# Format: "name:instruction;name:instruction"
DEEPSEEK_AGENT_SWARM_PROFILES: str = os.getenv(
    "DEEPSEEK_AGENT_SWARM_PROFILES",
    "",
)
DEEPSEEK_MESH_ENABLED: bool = (
    os.getenv("DEEPSEEK_MESH_ENABLED", "true").lower() == "true"
)
DEEPSEEK_MESH_MIN_ACTIVE_AGENTS: int = int(
    os.getenv("DEEPSEEK_MESH_MIN_ACTIVE_AGENTS", "2")
)
DEEPSEEK_MESH_LATENCY_PENALTY: float = float(
    os.getenv("DEEPSEEK_MESH_LATENCY_PENALTY", "0.25")
)
DEEPSEEK_MESH_TRUST_ALPHA: float = float(
    os.getenv("DEEPSEEK_MESH_TRUST_ALPHA", "0.18")
)
DEEPSEEK_MESH_MIN_TRUST: float = float(
    os.getenv("DEEPSEEK_MESH_MIN_TRUST", "0.15")
)
DEEPSEEK_MESH_MAX_TRUST: float = float(
    os.getenv("DEEPSEEK_MESH_MAX_TRUST", "0.95")
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
# All four active sessions are enabled by default so the ICT killzone engine
# (London 07-10 UTC, NY 12-16 UTC) can work as designed.  The prior "0% win
# rate for London/NY" reflected a tiny early sample — those sessions carry
# the highest volume, tightest spreads, and the strongest ICT setups.
# Override via .env ENTRY_ALLOWED_SESSIONS=asian,overlap to revert if needed.
# IMPORTANT: use "newyork" (no underscore) — that is what current_session() returns.
# Valid values: asian, london, overlap, newyork, off_hours
ENTRY_ALLOWED_SESSIONS: list = [
    s.strip() for s in os.getenv("ENTRY_ALLOWED_SESSIONS", "asian,london,overlap").split(",")
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
WEEKEND_SYMBOLS: str = os.getenv(
    "WEEKEND_SYMBOLS",
    "BTCUSD,ETHUSD,BNBUSD,SOLUSD,XRPUSD,ADAUSD,DOTUSD,LTCUSD,EOSUSD,XLMUSD,TRXUSD",
)

# ── Crucix World Intelligence (optional) ─────────────────────────────
CRUCIX_URL: str = os.getenv("CRUCIX_URL", "https://crucix-pi.vercel.app")

# ── Strategy plugin loader ───────────────────────────────────────────────
# Comma-separated dotted paths to strategy classes, e.g.
# STRATEGY_PLUGINS=my_pkg.alpha.AlphaStrategy,my_pkg.beta.BetaStrategy
STRATEGY_PLUGINS: tuple[str, ...] = tuple(
    s.strip()
    for s in os.getenv("STRATEGY_PLUGINS", "").split(",")
    if s.strip()
)
STRATEGY_PLUGIN_FAIL_FAST: bool = (
    os.getenv("STRATEGY_PLUGIN_FAIL_FAST", "false").lower() == "true"
)


def _apply_profile_overrides() -> None:
    """Apply opinionated runtime profiles after env parsing.

    Profiles intentionally only override a small, high-impact subset.
    """

    profile_overrides: dict[str, dict[str, object]] = {
        "dev": {
            "DEMO_MODE": True,
            "COUNCIL_ENABLED": False,
            "COUNCIL_MODE": "advisory",
            "FAST_LANE_ENABLED": True,
            "INSTANT_ENTRY_ENABLED": True,
            "MAX_RISK_PER_TRADE": 0.005,
            "MAX_OPEN_TRADES": 2,
            "MAX_DAILY_LOSS": 0.02,
        },
        "paper": {
            "DEMO_MODE": True,
            "COUNCIL_ENABLED": True,
            "COUNCIL_MODE": "blocking",
            "FAST_LANE_ENABLED": False,
            "INSTANT_ENTRY_ENABLED": False,
            "MAX_RISK_PER_TRADE": 0.003,
            "MAX_OPEN_TRADES": 2,
            "MAX_DAILY_LOSS": 0.015,
        },
        "live-safe": {
            "DEMO_MODE": False,
            "COUNCIL_ENABLED": True,
            "COUNCIL_MODE": "blocking",
            "FAST_LANE_ENABLED": False,
            "INSTANT_ENTRY_ENABLED": False,
            "MAX_RISK_PER_TRADE": 0.005,
            "MAX_OPEN_TRADES": 2,
            "MAX_DAILY_LOSS": 0.02,
            "RISK_VALIDATION_PROFILE": "strict",
        },
        "live-full": {
            "DEMO_MODE": False,
            "COUNCIL_ENABLED": True,
            "COUNCIL_MODE": "advisory",
            "FAST_LANE_ENABLED": True,
            "INSTANT_ENTRY_ENABLED": True,
            "MAX_RISK_PER_TRADE": 0.01,
            "MAX_OPEN_TRADES": 4,
            "MAX_DAILY_LOSS": 0.03,
            "RISK_VALIDATION_PROFILE": "agile",
        },
    }

    selected = profile_overrides.get(BOT_PROFILE)
    if not selected:
        return

    g = globals()
    for key, value in selected.items():
        if key in g:
            g[key] = value


_apply_profile_overrides()
