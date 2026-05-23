"""All configurable parameters for the trading bot.

Validated at startup via Pydantic Settings.  All values are also re-exported as
flat module-level variables so existing code (`from config.settings import
BROKER_ACCOUNT`) continues to work without any changes.

New code should prefer the structured ``settings`` object::

    from config.settings import settings
    if settings.risk.max_risk_per_trade > 0.05:
        ...

Environment variables are loaded from ``.env`` in the project root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

# ── Load .env ──────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


# ── Helper validators ────────────────────────────────────────────────────

def _parse_tuple_str(value: str) -> tuple[str, ...]:
    """Parse a comma-separated env var into a tuple of stripped strings."""
    return tuple(s.strip() for s in value.split(",") if s.strip())


def _parse_tuple_int(value: str) -> tuple[int, ...]:
    """Parse a comma-separated env var into a tuple of ints."""
    result: list[int] = []
    for v in value.replace(";", ",").split(","):
        v = v.strip()
        if v.isdigit():
            result.append(int(v))
    return tuple(result)


def _parse_list_str(value: str) -> list[str]:
    """Parse a comma-separated env var into a list of stripped strings."""
    return [s.strip() for s in value.split(",") if s.strip()]


# ── Broker settings ───────────────────────────────────────────────────────

class BrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BROKER_", extra="ignore")

    account: str = Field(default="", validation_alias="BROKER_ACCOUNT")
    password: str = Field(default="", validation_alias="BROKER_PASSWORD")
    server: str = Field(default="", validation_alias="BROKER_SERVER")


# ── Risk settings ─────────────────────────────────────────────────────────

class RiskSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    max_risk_per_trade: float = Field(default=0.02, ge=0.0001, le=0.50, validation_alias="MAX_RISK_PER_TRADE")
    max_open_trades: int = Field(default=5, ge=1, le=50, validation_alias="MAX_OPEN_TRADES")
    max_daily_loss: float = Field(default=0.05, ge=0.001, le=0.50, validation_alias="MAX_DAILY_LOSS")
    max_monthly_loss: float = Field(default=0.10, ge=0.001, le=0.99, validation_alias="MAX_MONTHLY_LOSS")
    max_spread_pips: float = Field(default=8.0, ge=0.0, validation_alias="MAX_SPREAD_PIPS")
    max_spread_pips_commodity: float = Field(default=10.0, ge=0.0, validation_alias="MAX_SPREAD_PIPS_COMMODITY")
    max_spread_pips_exotic: float = Field(default=15.0, ge=0.0, validation_alias="MAX_SPREAD_PIPS_EXOTIC")
    max_spread_pct_crypto: float = Field(default=2.5, ge=0.0, validation_alias="MAX_SPREAD_PCT_CRYPTO")
    max_spread_points_index: float = Field(default=5.0, ge=0.0, validation_alias="MAX_SPREAD_POINTS_INDEX")
    drawdown_cooldown_hours: int = Field(default=24, ge=0, validation_alias="DRAWDOWN_COOLDOWN_HOURS")
    min_lot_size: float = Field(default=0.01, ge=0.0, validation_alias="MIN_LOT_SIZE")
    max_lot_size: float = Field(default=50.0, ge=0.0, validation_alias="MAX_LOT_SIZE")
    fixed_lot_size: float = Field(default=0.0, ge=0.0, validation_alias="FIXED_LOT_SIZE")
    position_size_mode: str = Field(default="equity_pct", validation_alias="POSITION_SIZE_MODE")
    position_size_fixed_lot: float = Field(default=0.10, ge=0.0, validation_alias="POSITION_SIZE_FIXED_LOT")
    position_size_fixed_risk_amount: float = Field(default=100.0, ge=0.0, validation_alias="POSITION_SIZE_FIXED_RISK_AMOUNT")
    kelly_min_trades: int = Field(default=20, ge=2, validation_alias="KELLY_MIN_TRADES")
    kelly_lookback_days: int = Field(default=90, ge=7, validation_alias="KELLY_LOOKBACK_DAYS")
    kelly_half: bool = Field(default=True, validation_alias="KELLY_HALF")
    risk_validation_profile: str = Field(default="agile", validation_alias="RISK_VALIDATION_PROFILE")
    risk_agile_high_conf_threshold: float = Field(default=0.74, ge=0.0, le=1.0, validation_alias="RISK_AGILE_HIGH_CONF_THRESHOLD")
    risk_agile_spread_multiplier: float = Field(default=1.35, ge=0.0, validation_alias="RISK_AGILE_SPREAD_MULTIPLIER")

    @field_validator("position_size_mode", "risk_validation_profile", mode="before")
    @classmethod
    def _lowercase_str(cls, v: str) -> str:
        return str(v).lower()


# ── Guard pipeline settings ───────────────────────────────────────────────

class GuardSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="GUARD_PIPELINE_ENABLED")
    cooldown_seconds: int = Field(default=300, ge=0, validation_alias="GUARD_COOLDOWN_SECONDS")
    max_daily_loss_pct: float = Field(default=0.05, ge=0.0, le=1.0, validation_alias="GUARD_MAX_DAILY_LOSS_PCT")
    max_vix: float = Field(default=40.0, ge=0.0, validation_alias="GUARD_MAX_VIX")
    feed_staleness_seconds: float = Field(default=120.0, ge=0.0, validation_alias="GUARD_FEED_STALENESS_SECONDS")


# ── Execution / TP settings ─────────────────────────────────────────────────

class ExecutionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    tp1_close_percent: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="TP1_CLOSE_PERCENT")
    tp2_close_percent: float = Field(default=0.30, ge=0.0, le=1.0, validation_alias="TP2_CLOSE_PERCENT")
    tp3_close_percent: float = Field(default=0.20, ge=0.0, le=1.0, validation_alias="TP3_CLOSE_PERCENT")
    tp4_close_percent: float = Field(default=0.10, ge=0.0, le=1.0, validation_alias="TP4_CLOSE_PERCENT")
    trailing_stop_distance_pips: float = Field(default=20.0, ge=0.0, validation_alias="TRAILING_STOP_DISTANCE_PIPS")
    commission_per_lot: float = Field(default=7.0, ge=0.0, validation_alias="COMMISSION_PER_LOT")
    commission_per_lot_crypto: float = Field(default=7.0, ge=0.0, validation_alias="COMMISSION_PER_LOT_CRYPTO")
    commission_per_lot_commodity: float = Field(default=7.0, ge=0.0, validation_alias="COMMISSION_PER_LOT_COMMODITY")
    commission_per_lot_exotic: float = Field(default=7.0, ge=0.0, validation_alias="COMMISSION_PER_LOT_EXOTIC")
    breakeven_spread_offset: bool = Field(default=True, validation_alias="BREAKEVEN_SPREAD_OFFSET")
    limit_entry_max_distance_atr: float = Field(default=0.5, ge=0.0, validation_alias="LIMIT_ENTRY_MAX_DISTANCE_ATR")
    limit_entry_max_distance_atr_crypto: float = Field(default=2.0, ge=0.0, validation_alias="LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO")

    @model_validator(mode="after")
    def _tp_sum_check(self) -> "ExecutionSettings":
        total = (
            self.tp1_close_percent
            + self.tp2_close_percent
            + self.tp3_close_percent
            + self.tp4_close_percent
        )
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"TP close percents must sum to 1.0, got {total:.2f} "
                f"(tp1={self.tp1_close_percent} "
                f"tp2={self.tp2_close_percent} "
                f"tp3={self.tp3_close_percent} "
                f"tp4={self.tp4_close_percent})"
            )
        return self


# ── Sniper / deferred entry settings ─────────────────────────────────────

class SniperSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="SNIPER_ENTRY_ENABLED")
    conf_threshold: float = Field(default=0.55, ge=0.0, le=1.0, validation_alias="SNIPER_CONF_THRESHOLD")
    timeout_minutes: float = Field(default=30.0, ge=0.0, validation_alias="SNIPER_TIMEOUT_MINUTES")
    max_entry_atr_distance: float = Field(default=0.55, ge=0.0, validation_alias="SNIPER_MAX_ENTRY_ATR_DISTANCE")
    fib_min_depth: str = Field(default="acceptable", validation_alias="SNIPER_FIB_MIN_DEPTH")
    fib_max_depth: str = Field(default="deep", validation_alias="SNIPER_FIB_MAX_DEPTH")

    @field_validator("fib_min_depth", "fib_max_depth", mode="before")
    @classmethod
    def _lowercase_str(cls, v: str) -> str:
        return str(v).lower()


class DeferredSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="DEFERRED_ENTRY_ENABLED")
    max_age_seconds: int = Field(default=900, ge=0, validation_alias="DEFERRED_ENTRY_MAX_AGE_SECONDS")
    max_atr_distance: float = Field(default=0.35, ge=0.0, validation_alias="DEFERRED_ENTRY_MAX_ATR_DISTANCE")
    min_conf: float = Field(default=0.60, ge=0.0, le=1.0, validation_alias="DEFERRED_ENTRY_MIN_CONF")
    ttl_seconds: int = Field(default=900, ge=0, validation_alias="DEFERRED_ENTRY_TTL_SECONDS")


# ── Fast lane / instant entry settings ─────────────────────────────────────

class FastLaneSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="FAST_LANE_ENABLED")
    max_signals: int = Field(default=1, ge=0, validation_alias="FAST_LANE_MAX_SIGNALS")
    close_on_full_reject: bool = Field(default=True, validation_alias="FAST_LANE_CLOSE_ON_FULL_REJECT")


class InstantEntrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="INSTANT_ENTRY_ENABLED")
    min_confidence: float = Field(default=0.78, ge=0.0, le=1.0, validation_alias="INSTANT_ENTRY_MIN_CONFIDENCE")


class ExposureSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=False, validation_alias="EXPOSURE_ENABLED")
    reduce_threshold: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="EXPOSURE_REDUCE_THRESHOLD")
    cash_threshold: float = Field(default=0.20, ge=0.0, le=1.0, validation_alias="EXPOSURE_CASH_THRESHOLD")
    win_rate_lookback: int = Field(default=10, ge=1, validation_alias="EXPOSURE_WIN_RATE_LOOKBACK")


# ── ML / neural settings ─────────────────────────────────────────────────

class NeuralSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    min_candles: int = Field(default=65, ge=1, validation_alias="NEURAL_MIN_CANDLES")
    seq_len: int = Field(default=50, ge=1, validation_alias="NEURAL_SEQ_LEN")
    hidden_size: int = Field(default=128, ge=1, validation_alias="NEURAL_HIDDEN_SIZE")
    num_layers: int = Field(default=2, ge=1, validation_alias="NEURAL_NUM_LAYERS")
    train_epochs: int = Field(default=100, ge=1, validation_alias="NEURAL_TRAIN_EPOCHS")
    retrain_every: int = Field(default=20, ge=1, validation_alias="NEURAL_RETRAIN_EVERY")
    min_confidence: float = Field(default=0.55, ge=0.0, le=1.0, validation_alias="NEURAL_MIN_CONFIDENCE")
    lgbm_ensemble_enabled: bool = Field(default=True, validation_alias="LGBM_ENSEMBLE_ENABLED")
    kalman_enabled: bool = Field(default=False, validation_alias="KALMAN_ENABLED")


class GarchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="GARCH_ENABLED")
    high_vol_threshold: float = Field(default=2.0, ge=0.0, validation_alias="GARCH_HIGH_VOL_THRESHOLD")


# ── ICT strategy settings ─────────────────────────────────────────────────

class ICTSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    min_confidence: int = Field(default=30, ge=0, le=100, validation_alias="ICT_MIN_CONFIDENCE")
    h4_candle_count: int = Field(default=200, ge=1, validation_alias="H4_CANDLE_COUNT")
    d1_candle_count: int = Field(default=20, ge=1, validation_alias="D1_CANDLE_COUNT")
    m30_candle_count: int = Field(default=100, ge=1, validation_alias="M30_CANDLE_COUNT")
    m15_candle_count: int = Field(default=250, ge=1, validation_alias="M15_CANDLE_COUNT")
    m5_candle_count: int = Field(default=100, ge=1, validation_alias="M5_CANDLE_COUNT")
    mtf_alignment_boost: float = Field(default=0.05, ge=0.0, le=1.0, validation_alias="MTF_ALIGNMENT_BOOST")
    mtf_d1_veto: bool = Field(default=True, validation_alias="MTF_D1_VETO")
    regime_adx_trending: float = Field(default=25.0, ge=0.0, validation_alias="REGIME_ADX_TRENDING")
    regime_adx_ranging: float = Field(default=20.0, ge=0.0, validation_alias="REGIME_ADX_RANGING")
    regime_confidence_penalty: float = Field(default=0.10, ge=0.0, le=1.0, validation_alias="REGIME_CONFIDENCE_PENALTY")
    tp_trending_tp1_mult: float = Field(default=1.5, ge=0.0, validation_alias="TP_TRENDING_TP1_MULT")
    tp_trending_tp2_mult: float = Field(default=2.5, ge=0.0, validation_alias="TP_TRENDING_TP2_MULT")
    tp_trending_tp3_mult: float = Field(default=4.0, ge=0.0, validation_alias="TP_TRENDING_TP3_MULT")
    tp_trending_tp4_mult: float = Field(default=6.0, ge=0.0, validation_alias="TP_TRENDING_TP4_MULT")
    tp_ranging_tp1_mult: float = Field(default=0.8, ge=0.0, validation_alias="TP_RANGING_TP1_MULT")
    tp_ranging_tp2_mult: float = Field(default=1.5, ge=0.0, validation_alias="TP_RANGING_TP2_MULT")
    tp_ranging_tp3_mult: float = Field(default=2.5, ge=0.0, validation_alias="TP_RANGING_TP3_MULT")
    max_hours_in_trade: int = Field(default=48, ge=0, validation_alias="MAX_HOURS_IN_TRADE")
    min_ict_score_crypto: float = Field(default=35.0, ge=0.0, validation_alias="MIN_ICT_SCORE_CRYPTO")
    min_conf_trending: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="MIN_CONF_TRENDING")
    min_conf_ranging: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="MIN_CONF_RANGING")
    min_conf_volatile: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="MIN_CONF_VOLATILE")
    min_conf_unknown: float = Field(default=0.40, ge=0.0, le=1.0, validation_alias="MIN_CONF_UNKNOWN")
    min_conf_crypto_bonus: float = Field(default=0.03, ge=0.0, le=1.0, validation_alias="MIN_CONF_CRYPTO_BONUS")
    min_conf_exotic_bonus: float = Field(default=0.04, ge=0.0, le=1.0, validation_alias="MIN_CONF_EXOTIC_BONUS")
    size_scale_very_low_threshold: float = Field(default=0.45, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_VERY_LOW_THRESHOLD")
    size_scale_low_threshold: float = Field(default=0.60, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_LOW_THRESHOLD")
    size_scale_medium_threshold: float = Field(default=0.75, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_MEDIUM_THRESHOLD")
    size_scale_very_low: float = Field(default=0.35, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_VERY_LOW")
    size_scale_low: float = Field(default=0.55, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_LOW")
    size_scale_medium: float = Field(default=0.75, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_MEDIUM")
    size_scale_full: float = Field(default=1.00, ge=0.0, le=1.0, validation_alias="SIZE_SCALE_FULL")


# ── Orchestration / loop settings ───────────────────────────────────────────

class OrchestrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    loop_interval_seconds: int = Field(default=5, ge=1, le=600, validation_alias="LOOP_INTERVAL_SECONDS")
    reconcile_every_n_loops: int = Field(default=60, ge=1, validation_alias="RECONCILE_EVERY_N_LOOPS")
    candle_server_port: int = Field(default=5555, ge=1, le=65535, validation_alias="CANDLE_SERVER_PORT")
    scan_cooldown_seconds: int = Field(default=300, ge=0, validation_alias="SCAN_COOLDOWN_SECONDS")
    scan_cooldown_seconds_london_ny: int = Field(default=60, ge=0, validation_alias="SCAN_COOLDOWN_SECONDS_LONDON_NY")
    scan_cooldown_seconds_asia: int = Field(default=120, ge=0, validation_alias="SCAN_COOLDOWN_SECONDS_ASIA")
    btc_priority_symbol: str = Field(default="BTCUSD", validation_alias="BTC_PRIORITY_SYMBOL")
    btc_priority_scan_cooldown_seconds: int = Field(default=8, ge=0, validation_alias="BTC_PRIORITY_SCAN_COOLDOWN_SECONDS")
    event_driven_rescan_on_new_candle: bool = Field(default=True, validation_alias="EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE")
    scan_workers_min: int = Field(default=2, ge=1, validation_alias="ORCHESTRATION_SCAN_WORKERS_MIN")
    scan_workers_max: int = Field(default=10, ge=1, validation_alias="ORCHESTRATION_SCAN_WORKERS_MAX")
    scan_workers_default: int = Field(default=6, ge=1, validation_alias="ORCHESTRATION_SCAN_WORKERS_DEFAULT")
    adaptive_workers_enabled: bool = Field(default=True, validation_alias="ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED")
    target_scan_ms: float = Field(default=15000, ge=0, validation_alias="ORCHESTRATION_TARGET_SCAN_MS")
    target_rank_ms: float = Field(default=200, ge=0, validation_alias="ORCHESTRATION_TARGET_RANK_MS")
    target_exec_ms: float = Field(default=800, ge=0, validation_alias="ORCHESTRATION_TARGET_EXEC_MS")
    target_total_ms: float = Field(default=60000, ge=0, validation_alias="ORCHESTRATION_TARGET_TOTAL_MS")
    max_signals_per_iteration: int = Field(default=20, ge=1, validation_alias="ORCHESTRATION_MAX_SIGNALS_PER_ITERATION")
    enable_iteration_trace: bool = Field(default=True, validation_alias="ORCHESTRATION_ENABLE_ITERATION_TRACE")
    scan_error_rate_abort: float = Field(default=0.70, ge=0.0, le=1.0, validation_alias="ORCHESTRATION_SCAN_ERROR_RATE_ABORT")
    scan_error_min_samples: int = Field(default=5, ge=1, validation_alias="ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES")
    hard_budget_enabled: bool = Field(default=True, validation_alias="ORCHESTRATION_HARD_BUDGET_ENABLED")
    max_scan_ms: float = Field(default=90000, ge=0, validation_alias="ORCHESTRATION_MAX_SCAN_MS")
    max_rank_ms: float = Field(default=1000, ge=0, validation_alias="ORCHESTRATION_MAX_RANK_MS")
    max_exec_ms: float = Field(default=3000, ge=0, validation_alias="ORCHESTRATION_MAX_EXEC_MS")
    max_iteration_ms: float = Field(default=120000, ge=0, validation_alias="ORCHESTRATION_MAX_ITERATION_MS")
    exec_budget_council_margin_ms: float = Field(default=350, ge=0, validation_alias="ORCHESTRATION_EXEC_BUDGET_COUNCIL_MARGIN_MS")
    symbol_max_fail_count: int = Field(default=20, ge=1, validation_alias="SYMBOL_MAX_FAIL_COUNT")
    symbol_disable_seconds: int = Field(default=1800, ge=0, validation_alias="SYMBOL_DISABLE_SECONDS")
    permanent_fault_symbols: str = Field(default="", validation_alias="PERMANENT_FAULT_SYMBOLS")
    market_closed_sleep_total_seconds: int = Field(default=300, ge=1, validation_alias="MARKET_CLOSED_SLEEP_TOTAL_SECONDS")
    market_closed_sleep_interval_seconds: int = Field(default=10, ge=1, validation_alias="MARKET_CLOSED_SLEEP_INTERVAL_SECONDS")
    htf_cache_ttl_m15_seconds: float = Field(default=20, ge=0, validation_alias="HTF_CACHE_TTL_M15_SECONDS")
    htf_cache_ttl_m5_seconds: float = Field(default=15, ge=0, validation_alias="HTF_CACHE_TTL_M5_SECONDS")
    htf_cache_ttl_m30_seconds: float = Field(default=30, ge=0, validation_alias="HTF_CACHE_TTL_M30_SECONDS")
    htf_cache_ttl_h4_seconds: float = Field(default=120, ge=0, validation_alias="HTF_CACHE_TTL_H4_SECONDS")
    htf_cache_ttl_d1_seconds: float = Field(default=300, ge=0, validation_alias="HTF_CACHE_TTL_D1_SECONDS")
    htf_cache_ttl_multiplier_london_ny: float = Field(default=0.75, ge=0.0, validation_alias="HTF_CACHE_TTL_MULTIPLIER_LONDON_NY")
    htf_cache_ttl_multiplier_asia: float = Field(default=1.35, ge=0.0, validation_alias="HTF_CACHE_TTL_MULTIPLIER_ASIA")


# ── Opportunity lifecycle settings ─────────────────────────────────────────

class OpportunitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="OPPORTUNITY_PHASE_ENABLED")
    rollover_seconds: int = Field(default=900, ge=0, validation_alias="OPPORTUNITY_ROLLOVER_SECONDS")
    watch_window_seconds: int = Field(default=180, ge=0, validation_alias="OPPORTUNITY_WATCH_WINDOW_SECONDS")
    hedge_timeout_seconds: int = Field(default=300, ge=0, validation_alias="OPPORTUNITY_HEDGE_TIMEOUT_SECONDS")
    min_recovery_confidence: float = Field(default=0.62, ge=0.0, le=1.0, validation_alias="OPPORTUNITY_MIN_RECOVERY_CONFIDENCE")
    fallback_max_spread_pct: float = Field(default=0.003, ge=0.0, validation_alias="OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT")
    shock_lookback_seconds: int = Field(default=5, ge=0, validation_alias="OPPORTUNITY_SHOCK_LOOKBACK_SECONDS")
    shock_drop_threshold: float = Field(default=0.0015, ge=0.0, validation_alias="OPPORTUNITY_SHOCK_DROP_THRESHOLD")
    require_shock_for_fast_lane: bool = Field(default=True, validation_alias="OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE")
    live_enabled: bool = Field(default=False, validation_alias="OPPORTUNITY_LIVE_ENABLED")


# ── Protection layer settings ─────────────────────────────────────────────

class ProtectionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="PROTECTIONS_ENABLED")
    cooldown_minutes: int = Field(default=10, ge=0, validation_alias="PROTECTION_COOLDOWN_MINUTES")
    stoploss_guard_lookback_minutes: int = Field(default=180, ge=0, validation_alias="PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES")
    stoploss_guard_trade_limit: int = Field(default=3, ge=0, validation_alias="PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT")
    stoploss_guard_lock_minutes: int = Field(default=60, ge=0, validation_alias="PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES")
    global_loss_guard_lookback_minutes: int = Field(default=120, ge=0, validation_alias="PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES")
    global_loss_guard_max_losses: int = Field(default=4, ge=0, validation_alias="PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES")
    global_loss_guard_lock_minutes: int = Field(default=45, ge=0, validation_alias="PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES")
    consecutive_reject_limit: int = Field(default=5, ge=2, validation_alias="CONSECUTIVE_REJECT_LIMIT")
    consecutive_reject_cooldown_minutes: int = Field(default=15, ge=1, validation_alias="CONSECUTIVE_REJECT_COOLDOWN_MINUTES")


# ── Time-phase confidence gate settings ───────────────────────────────────

class TimePhaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=False, validation_alias="TIME_PHASE_CONFIDENCE_ENABLED")
    bucket_minutes: int = Field(default=15, ge=1, validation_alias="TIME_PHASE_BUCKET_MINUTES")
    early_max_minute: int = Field(default=3, ge=0, validation_alias="TIME_PHASE_EARLY_MAX_MINUTE")
    mid_max_minute: int = Field(default=11, ge=0, validation_alias="TIME_PHASE_MID_MAX_MINUTE")
    min_conf_early: float = Field(default=0.55, ge=0.0, le=1.0, validation_alias="TIME_PHASE_MIN_CONF_EARLY")
    min_conf_mid: float = Field(default=0.50, ge=0.0, le=1.0, validation_alias="TIME_PHASE_MIN_CONF_MID")
    min_conf_late: float = Field(default=0.48, ge=0.0, le=1.0, validation_alias="TIME_PHASE_MIN_CONF_LATE")


# ── Telegram settings ─────────────────────────────────────────────────────

class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TELEGRAM__", extra="ignore")

    bot_token: str = Field(default="", validation_alias="BOT_TOKEN")
    chat_id: str = Field(default="", validation_alias="CHAT_ID")
    noise_filter_enabled: bool = Field(default=True, validation_alias="NOISE_FILTER_ENABLED")
    dedupe_window_seconds: int = Field(default=180, ge=0, validation_alias="DEDUPE_WINDOW_SECONDS")
    rate_limit_per_minute: int = Field(default=20, ge=0, validation_alias="RATE_LIMIT_PER_MINUTE")
    suppression_report_every: int = Field(default=10, ge=0, validation_alias="SUPPRESSION_REPORT_EVERY")
    chart_days: int = Field(default=30, ge=1, validation_alias="CHART_DAYS")
    allowed_usernames: tuple[str, ...] = Field(default_factory=tuple)
    allowed_user_ids: tuple[int, ...] = Field(default_factory=tuple)

    @field_validator("allowed_usernames", mode="before")
    @classmethod
    def _parse_usernames(cls, v: Any) -> tuple[str, ...]:
        if isinstance(v, list):
            return tuple(str(x).strip().lstrip("@").lower() for x in v if x)
        if isinstance(v, str):
            return tuple(
                u.strip().lstrip("@").lower()
                for u in v.replace(";", ",").split(",")
                if u.strip()
            )
        return v or ()

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _parse_user_ids(cls, v: Any) -> tuple[int, ...]:
        if isinstance(v, list):
            return tuple(int(x) for x in v if str(x).strip().isdigit())
        if isinstance(v, str):
            return tuple(
                int(v.strip())
                for v in v.replace(";", ",").split(",")
                if v.strip().isdigit()
            )
        return v or ()


# ── Intelligence / data feed settings ─────────────────────────────────────

class IntelligenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    alpha_vantage_key: str = Field(default="", validation_alias="ALPHA_VANTAGE_KEY")
    twelve_data_key: str = Field(default="", validation_alias="TWELVE_DATA_KEY")
    fred_api_key: str = Field(default="", validation_alias="FRED_API_KEY")
    yfinance_enabled: bool = Field(default=True, validation_alias="YFINANCE_ENABLED")
    sweep_interval_minutes: int = Field(default=15, ge=1, validation_alias="INTELLIGENCE_SWEEP_INTERVAL_MINUTES")
    mt5_db_sync_interval_seconds: int = Field(default=300, ge=0, validation_alias="MT5_DB_SYNC_INTERVAL_SECONDS")
    news_calendar_source: str = Field(default="static", validation_alias="NEWS_CALENDAR_SOURCE")
    finnhub_api_key: str = Field(default="", validation_alias="FINNHUB_API_KEY")
    news_blackout_minutes: int = Field(default=15, ge=0, validation_alias="NEWS_BLACKOUT_MINUTES")
    crucix_url: str = Field(default="https://crucix-pi.vercel.app", validation_alias="CRUCIX_URL")


# ── ML / learning system settings ─────────────────────────────────────────

class LearningSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    default_confidence: float = Field(default=0.5, validation_alias="DEFAULT_CONFIDENCE")
    initial_confidence: float = Field(default=0.5, validation_alias="INITIAL_CONFIDENCE")
    confidence_allow: float = Field(default=0.3, validation_alias="CONFIDENCE_ALLOW")
    confidence_reduced: float = Field(default=0.5, validation_alias="CONFIDENCE_REDUCED")
    confidence_full: float = Field(default=0.7, validation_alias="CONFIDENCE_FULL")
    confidence_disable_threshold: float = Field(default=0.2, validation_alias="CONFIDENCE_DISABLE_THRESHOLD")
    metrics_log_every_n_loops: int = Field(default=5, ge=1, validation_alias="METRICS_LOG_EVERY_N_LOOPS")


# ── Backtest settings ─────────────────────────────────────────────────────

class BacktestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    commission_per_lot_per_side: float = Field(default=0.0001, ge=0.0, validation_alias="BACKTEST_COMMISSION_PER_LOT_PER_SIDE")
    walk_forward_enabled: bool = Field(default=False, validation_alias="BACKTEST_WALK_FORWARD_ENABLED")
    walk_forward_window_days: int = Field(default=90, ge=1, validation_alias="BACKTEST_WALK_FORWARD_WINDOW_DAYS")


# ── Logging / misc settings ────────────────────────────────────────────────

class MiscSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    daily_summary_hour: int = Field(default=17, ge=0, le=23, validation_alias="DAILY_SUMMARY_HOUR")
    timezone: str = Field(default="Europe/Paris", validation_alias="TIMEZONE")
    default_symbol: str = Field(default="BTCUSD", validation_alias="DEFAULT_SYMBOL")
    default_timeframe: str = Field(default="H1", validation_alias="DEFAULT_TIMEFRAME")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    db_path: str = Field(
        default="",
        validation_alias="DB_PATH",
    )
    encryption_key: str = Field(default="", validation_alias="ENCRYPTION_KEY")
    sma_fast_period: int = Field(default=10, ge=1, validation_alias="SMA_FAST_PERIOD")
    sma_slow_period: int = Field(default=50, ge=1, validation_alias="SMA_SLOW_PERIOD")
    sentry_dsn: str = Field(default="", validation_alias="MISC_SENTRY_DSN")


# ── Market session settings ───────────────────────────────────────────────

class SessionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SESSION__", extra="ignore")

    allowed_sessions: list[str] = Field(default=["asian", "london", "overlap"])
    blocked_days: list[str] = Field(default=["Saturday", "Sunday"])
    mtf_min_alignment: float = Field(default=0.0, ge=0.0, le=1.0)
    weekend_symbols: str = Field(
        default="BTCUSD,ETHUSD,BNBUSD,SOLUSD,XRPUSD,ADAUSD,DOTUSD,LTCUSD,EOSUSD,XLMUSD,TRXUSD",
    )

    @field_validator("allowed_sessions", "blocked_days", mode="before")
    @classmethod
    def _parse_list_str(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if x]
        if isinstance(v, str):
            return _parse_list_str(v)
        return v or []


# ── Strategy plugin settings ─────────────────────────────────────────────────

class StrategyPluginSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STRATEGY_PLUGIN__", extra="ignore")

    plugins: tuple[str, ...] = Field(default_factory=tuple)
    fail_fast: bool = Field(default=False)

    @field_validator("plugins", mode="before")
    @classmethod
    def _parse_plugins(cls, v: Any) -> tuple[str, ...]:
        if isinstance(v, list):
            return tuple(str(x).strip() for x in v if x)
        if isinstance(v, str):
            return _parse_tuple_str(v)
        return v or ()


# ── OpenRouter / LLM settings ─────────────────────────────────────────────

class OpenRouterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    base_url: str = Field(default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL")
    model: str = Field(default="anthropic/claude-3-haiku", validation_alias="OPENROUTER_MODEL")
    fallback_enabled: bool = Field(default=False, validation_alias="OPENROUTER_FALLBACK_ENABLED")


# ── MCP server settings ─────────────────────────────────────────────────────

class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=False, validation_alias="MCP_SERVER_ENABLED")
    port: int = Field(default=8080, ge=1, le=65535, validation_alias="MCP_SERVER_PORT")


# ── HKU Marketplace settings ─────────────────────────────────────────────

class HKUSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HKU_", extra="ignore")

    enabled: bool = Field(default=False)
    api_url: str = Field(default="")
    api_key: str = Field(default="")
    signal_discount: float = Field(default=0.80, ge=0.0, le=1.0)
    publish_on_strategy: bool = Field(default=True)
    publish_on_discussion: bool = Field(default=True)
    feed_limit: int = Field(default=10, ge=1, le=50)
    circuit_breaker_timeout_secs: int = Field(default=300, ge=60)
    copy_trading_enabled: bool = Field(default=False)
    copy_leader_ids: list[str] = Field(default_factory=list)
    copy_margin_fraction: float = Field(default=0.05, ge=0.01, le=0.25)
    copy_max_trades: int = Field(default=3, ge=1, le=10)
    copy_min_winrate: float = Field(default=0.55, ge=0.0, le=1.0)
    copy_sl_atr: float = Field(default=1.5, ge=0.5, le=5.0)
    copy_tp_atr: float = Field(default=2.5, ge=0.5, le=10.0)

    @field_validator("copy_leader_ids", mode="before")
    @classmethod
    def _parse_copy_leader_ids(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if x]
        if isinstance(v, str):
            return _parse_list_str(v)
        return v or []


# ── Tool system settings ───────────────────────────────────────────────────

class ToolSystemSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    enabled: bool = Field(default=True, validation_alias="TOOL_SYSTEM_ENABLED")
    autorun_every_n_loops: int = Field(default=5, ge=1, validation_alias="TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS")
    strict_critical: bool = Field(default=True, validation_alias="TOOL_SYSTEM_STRICT_CRITICAL")
    max_actions_per_cycle: int = Field(default=8, ge=0, validation_alias="TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE")
    warning_spike_threshold: int = Field(default=2, ge=0, validation_alias="TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD")
    emergency_recovery_cycles: int = Field(default=2, ge=0, validation_alias="TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES")
    emergency_symbols: str = Field(
        default="BTCUSD,ETHUSD,XAUUSD,EURUSD",
        validation_alias="TOOL_SYSTEM_EMERGENCY_SYMBOLS",
    )
    emergency_max_risk_per_trade: float = Field(default=0.005, ge=0.0, le=1.0, validation_alias="TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE")
    emergency_max_open_trades: int = Field(default=1, ge=0, validation_alias="TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES")
    reweight_lookback_hours: int = Field(default=48, ge=0, validation_alias="TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS")
    reweight_min_trades: int = Field(default=4, ge=0, validation_alias="TOOL_SYSTEM_REWEIGHT_MIN_TRADES")


# ── Execution failure backoff settings ─────────────────────────────────────

class ExecutionFailureSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    autotrading_error_cooldown_seconds: int = Field(default=300, ge=0, validation_alias="EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS")
    pending_confirm_timeout_seconds: float = Field(default=4.0, ge=0.0, validation_alias="EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS")
    pending_confirm_poll_interval_seconds: float = Field(default=0.25, ge=0.0, validation_alias="EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS")
    spread_reject_cooldown_hits: int = Field(default=3, ge=0, validation_alias="SPREAD_REJECT_COOLDOWN_HITS")
    spread_reject_cooldown_seconds: int = Field(default=300, ge=0, validation_alias="SPREAD_REJECT_COOLDOWN_SECONDS")


# ── Data validation settings ───────────────────────────────────────────────

class DataValidationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    stuck_quote_threshold: int = Field(default=10, ge=0, validation_alias="STUCK_QUOTE_THRESHOLD")
    stuck_quote_threshold_crypto: int = Field(default=14, ge=0, validation_alias="STUCK_QUOTE_THRESHOLD_CRYPTO")
    spike_percent_threshold: float = Field(default=2.0, ge=0.0, validation_alias="SPIKE_PERCENT_THRESHOLD")


# ── Root settings model ───────────────────────────────────────────────────

class _Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        extra="ignore",
    )

    demo_mode: bool = Field(default=False, validation_alias="DEMO_MODE")
    bot_profile: str = Field(default="custom", validation_alias="BOT_PROFILE")

    broker: BrokerSettings = Field(default_factory=BrokerSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    guard: GuardSettings = Field(default_factory=GuardSettings)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)
    sniper: SniperSettings = Field(default_factory=SniperSettings)
    deferred: DeferredSettings = Field(default_factory=DeferredSettings)
    fast_lane: FastLaneSettings = Field(default_factory=FastLaneSettings)
    instant_entry: InstantEntrySettings = Field(default_factory=InstantEntrySettings)
    exposure: ExposureSettings = Field(default_factory=ExposureSettings)
    neural: NeuralSettings = Field(default_factory=NeuralSettings)
    garch: GarchSettings = Field(default_factory=GarchSettings)
    ict: ICTSettings = Field(default_factory=ICTSettings)
    orchestration: OrchestrationSettings = Field(default_factory=OrchestrationSettings)
    opportunity: OpportunitySettings = Field(default_factory=OpportunitySettings)
    protection: ProtectionSettings = Field(default_factory=ProtectionSettings)
    time_phase: TimePhaseSettings = Field(default_factory=TimePhaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    intelligence: IntelligenceSettings = Field(default_factory=IntelligenceSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    misc: MiscSettings = Field(default_factory=MiscSettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    strategy_plugin: StrategyPluginSettings = Field(default_factory=StrategyPluginSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    tool_system: ToolSystemSettings = Field(default_factory=ToolSystemSettings)
    hku: HKUSettings = Field(default_factory=HKUSettings)
    execution_failure: ExecutionFailureSettings = Field(default_factory=ExecutionFailureSettings)
    data_validation: DataValidationSettings = Field(default_factory=DataValidationSettings)


# ── Apply profile overrides ────────────────────────────────────────────────

def _apply_profile_overrides(s: _Settings) -> _Settings:
    """Apply opinionated runtime profiles after env parsing."""
    overrides: dict[str, dict[str, object]] = {
        "dev": {
            "demo_mode": True,
            ("fast_lane", "enabled"): True,
            ("instant_entry", "enabled"): True,
            ("risk", "max_risk_per_trade"): 0.005,
            ("risk", "max_open_trades"): 2,
            ("risk", "max_daily_loss"): 0.02,
        },
        "paper": {
            "demo_mode": True,
            ("fast_lane", "enabled"): False,
            ("instant_entry", "enabled"): False,
            ("risk", "max_risk_per_trade"): 0.003,
            ("risk", "max_open_trades"): 2,
            ("risk", "max_daily_loss"): 0.015,
        },
        "live-safe": {
            "demo_mode": False,
            ("fast_lane", "enabled"): False,
            ("instant_entry", "enabled"): False,
            ("risk", "max_risk_per_trade"): 0.005,
            ("risk", "max_open_trades"): 2,
            ("risk", "max_daily_loss"): 0.02,
            ("risk", "risk_validation_profile"): "strict",
        },
        "live-full": {
            "demo_mode": False,
            ("fast_lane", "enabled"): True,
            ("instant_entry", "enabled"): True,
            ("risk", "max_risk_per_trade"): 0.01,
            ("risk", "max_open_trades"): 4,
            ("risk", "max_daily_loss"): 0.03,
            ("risk", "risk_validation_profile"): "agile",
        },
    }

    profile = overrides.get(s.bot_profile)
    if not profile:
        return s

    for key, value in profile.items():
        if isinstance(key, tuple):
            sub_model, field_name = key
            sub = getattr(s, sub_model)
            setattr(sub, field_name, value)
        else:
            setattr(s, key, value)

    return s


# ── Build and validate settings ──────────────────────────────────────────

settings = _apply_profile_overrides(_Settings())


# ── Backward-compatible flat exports ─────────────────────────────────────
# All existing code uses `from config.settings import BROKER_ACCOUNT` etc.
# These re-export every setting as a module-level variable so no existing
# imports break.  New code should prefer the structured `settings` object.

# Mode
DEMO_MODE: bool = settings.demo_mode
BOT_PROFILE: str = settings.bot_profile

# Broker
BROKER_ACCOUNT: str = settings.broker.account
BROKER_PASSWORD: str = settings.broker.password
BROKER_SERVER: str = settings.broker.server

# Risk
MAX_RISK_PER_TRADE: float = settings.risk.max_risk_per_trade
MAX_OPEN_TRADES: int = settings.risk.max_open_trades
MAX_DAILY_LOSS: float = settings.risk.max_daily_loss
MAX_MONTHLY_LOSS: float = settings.risk.max_monthly_loss
MAX_SPREAD_PIPS: float = settings.risk.max_spread_pips
MAX_SPREAD_PIPS_COMMODITY: float = settings.risk.max_spread_pips_commodity
MAX_SPREAD_PIPS_EXOTIC: float = settings.risk.max_spread_pips_exotic
MAX_SPREAD_PCT_CRYPTO: float = settings.risk.max_spread_pct_crypto
MAX_SPREAD_POINTS_INDEX: float = settings.risk.max_spread_points_index
DRAWDOWN_COOLDOWN_HOURS: int = settings.risk.drawdown_cooldown_hours
MIN_LOT_SIZE: float = settings.risk.min_lot_size
MAX_LOT_SIZE: float = settings.risk.max_lot_size
FIXED_LOT_SIZE: float = settings.risk.fixed_lot_size
POSITION_SIZE_MODE: str = settings.risk.position_size_mode
POSITION_SIZE_FIXED_LOT: float = settings.risk.position_size_fixed_lot
POSITION_SIZE_FIXED_RISK_AMOUNT: float = settings.risk.position_size_fixed_risk_amount
KELLY_MIN_TRADES: int = settings.risk.kelly_min_trades
KELLY_LOOKBACK_DAYS: int = settings.risk.kelly_lookback_days
KELLY_HALF: bool = settings.risk.kelly_half
RISK_VALIDATION_PROFILE: str = settings.risk.risk_validation_profile
RISK_AGILE_HIGH_CONF_THRESHOLD: float = settings.risk.risk_agile_high_conf_threshold
RISK_AGILE_SPREAD_MULTIPLIER: float = settings.risk.risk_agile_spread_multiplier

# Guard
GUARD_PIPELINE_ENABLED: bool = settings.guard.enabled
GUARD_COOLDOWN_SECONDS: int = settings.guard.cooldown_seconds
GUARD_MAX_DAILY_LOSS_PCT: float = settings.guard.max_daily_loss_pct
GUARD_MAX_VIX: float = settings.guard.max_vix
GUARD_FEED_STALENESS_SECONDS: float = settings.guard.feed_staleness_seconds

# Execution / TP
TP1_CLOSE_PERCENT: float = settings.execution.tp1_close_percent
TP2_CLOSE_PERCENT: float = settings.execution.tp2_close_percent
TP3_CLOSE_PERCENT: float = settings.execution.tp3_close_percent
TP4_CLOSE_PERCENT: float = settings.execution.tp4_close_percent
TRAILING_STOP_DISTANCE_PIPS: float = settings.execution.trailing_stop_distance_pips
COMMISSION_PER_LOT: float = settings.execution.commission_per_lot
COMMISSION_PER_LOT_CRYPTO: float = settings.execution.commission_per_lot_crypto
COMMISSION_PER_LOT_COMMODITY: float = settings.execution.commission_per_lot_commodity
COMMISSION_PER_LOT_EXOTIC: float = settings.execution.commission_per_lot_exotic
BREAKEVEN_SPREAD_OFFSET: bool = settings.execution.breakeven_spread_offset
LIMIT_ENTRY_MAX_DISTANCE_ATR: float = settings.execution.limit_entry_max_distance_atr
LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO: float = settings.execution.limit_entry_max_distance_atr_crypto

# Sniper
SNIPER_ENTRY_ENABLED: bool = settings.sniper.enabled
SNIPER_CONF_THRESHOLD: float = settings.sniper.conf_threshold
SNIPER_TIMEOUT_MINUTES: float = settings.sniper.timeout_minutes
SNIPER_MAX_ENTRY_ATR_DISTANCE: float = settings.sniper.max_entry_atr_distance
SNIPER_FIB_MIN_DEPTH: str = settings.sniper.fib_min_depth
SNIPER_FIB_MAX_DEPTH: str = settings.sniper.fib_max_depth

# Deferred
DEFERRED_ENTRY_ENABLED: bool = settings.deferred.enabled
DEFERRED_ENTRY_MAX_AGE_SECONDS: int = settings.deferred.max_age_seconds
DEFERRED_ENTRY_MAX_ATR_DISTANCE: float = settings.deferred.max_atr_distance
DEFERRED_ENTRY_MIN_CONF: float = settings.deferred.min_conf
DEFERRED_ENTRY_TTL_SECONDS: int = settings.deferred.ttl_seconds

# Fast lane
FAST_LANE_ENABLED: bool = settings.fast_lane.enabled
FAST_LANE_MAX_SIGNALS: int = settings.fast_lane.max_signals
FAST_LANE_CLOSE_ON_FULL_REJECT: bool = settings.fast_lane.close_on_full_reject

# Instant entry
INSTANT_ENTRY_ENABLED: bool = settings.instant_entry.enabled
INSTANT_ENTRY_MIN_CONFIDENCE: float = settings.instant_entry.min_confidence

# Exposure
EXPOSURE_ENABLED: bool = settings.exposure.enabled
EXPOSURE_REDUCE_THRESHOLD: float = settings.exposure.reduce_threshold
EXPOSURE_CASH_THRESHOLD: float = settings.exposure.cash_threshold
EXPOSURE_WIN_RATE_LOOKBACK: int = settings.exposure.win_rate_lookback

# Neural
NEURAL_MIN_CANDLES: int = settings.neural.min_candles
NEURAL_SEQ_LEN: int = settings.neural.seq_len
NEURAL_HIDDEN_SIZE: int = settings.neural.hidden_size
NEURAL_NUM_LAYERS: int = settings.neural.num_layers
NEURAL_TRAIN_EPOCHS: int = settings.neural.train_epochs
NEURAL_RETRAIN_EVERY: int = settings.neural.retrain_every
NEURAL_MIN_CONFIDENCE: float = settings.neural.min_confidence
LGBM_ENSEMBLE_ENABLED: bool = settings.neural.lgbm_ensemble_enabled
KALMAN_ENABLED: bool = settings.neural.kalman_enabled

# GARCH
GARCH_ENABLED: bool = settings.garch.enabled
GARCH_HIGH_VOL_THRESHOLD: float = settings.garch.high_vol_threshold

# ICT
ICT_MIN_CONFIDENCE: int = settings.ict.min_confidence
H4_CANDLE_COUNT: int = settings.ict.h4_candle_count
D1_CANDLE_COUNT: int = settings.ict.d1_candle_count
M30_CANDLE_COUNT: int = settings.ict.m30_candle_count
M15_CANDLE_COUNT: int = settings.ict.m15_candle_count
M5_CANDLE_COUNT: int = settings.ict.m5_candle_count
MTF_ALIGNMENT_BOOST: float = settings.ict.mtf_alignment_boost
MTF_D1_VETO: bool = settings.ict.mtf_d1_veto
REGIME_ADX_TRENDING: float = settings.ict.regime_adx_trending
REGIME_ADX_RANGING: float = settings.ict.regime_adx_ranging
REGIME_CONFIDENCE_PENALTY: float = settings.ict.regime_confidence_penalty
TP_TRENDING_TP1_MULT: float = settings.ict.tp_trending_tp1_mult
TP_TRENDING_TP2_MULT: float = settings.ict.tp_trending_tp2_mult
TP_TRENDING_TP3_MULT: float = settings.ict.tp_trending_tp3_mult
TP_TRENDING_TP4_MULT: float = settings.ict.tp_trending_tp4_mult
TP_RANGING_TP1_MULT: float = settings.ict.tp_ranging_tp1_mult
TP_RANGING_TP2_MULT: float = settings.ict.tp_ranging_tp2_mult
TP_RANGING_TP3_MULT: float = settings.ict.tp_ranging_tp3_mult
MAX_HOURS_IN_TRADE: int = settings.ict.max_hours_in_trade
MIN_ICT_SCORE_CRYPTO: float = settings.ict.min_ict_score_crypto
MIN_CONF_TRENDING: float = settings.ict.min_conf_trending
MIN_CONF_RANGING: float = settings.ict.min_conf_ranging
MIN_CONF_VOLATILE: float = settings.ict.min_conf_volatile
MIN_CONF_UNKNOWN: float = settings.ict.min_conf_unknown
MIN_CONF_CRYPTO_BONUS: float = settings.ict.min_conf_crypto_bonus
MIN_CONF_EXOTIC_BONUS: float = settings.ict.min_conf_exotic_bonus
SIZE_SCALE_VERY_LOW_THRESHOLD: float = settings.ict.size_scale_very_low_threshold
SIZE_SCALE_LOW_THRESHOLD: float = settings.ict.size_scale_low_threshold
SIZE_SCALE_MEDIUM_THRESHOLD: float = settings.ict.size_scale_medium_threshold
SIZE_SCALE_VERY_LOW: float = settings.ict.size_scale_very_low
SIZE_SCALE_LOW: float = settings.ict.size_scale_low
SIZE_SCALE_MEDIUM: float = settings.ict.size_scale_medium
SIZE_SCALE_FULL: float = settings.ict.size_scale_full

# Orchestration
LOOP_INTERVAL_SECONDS: int = settings.orchestration.loop_interval_seconds
RECONCILE_EVERY_N_LOOPS: int = settings.orchestration.reconcile_every_n_loops
CANDLE_SERVER_PORT: int = settings.orchestration.candle_server_port
SCAN_COOLDOWN_SECONDS: int = settings.orchestration.scan_cooldown_seconds
SCAN_COOLDOWN_SECONDS_LONDON_NY: int = settings.orchestration.scan_cooldown_seconds_london_ny
SCAN_COOLDOWN_SECONDS_ASIA: int = settings.orchestration.scan_cooldown_seconds_asia
BTC_PRIORITY_SYMBOL: str = settings.orchestration.btc_priority_symbol
BTC_PRIORITY_SCAN_COOLDOWN_SECONDS: int = settings.orchestration.btc_priority_scan_cooldown_seconds
EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE: bool = settings.orchestration.event_driven_rescan_on_new_candle
ORCHESTRATION_SCAN_WORKERS_MIN: int = settings.orchestration.scan_workers_min
ORCHESTRATION_SCAN_WORKERS_MAX: int = settings.orchestration.scan_workers_max
ORCHESTRATION_SCAN_WORKERS_DEFAULT: int = settings.orchestration.scan_workers_default
ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED: bool = settings.orchestration.adaptive_workers_enabled
ORCHESTRATION_TARGET_SCAN_MS: float = settings.orchestration.target_scan_ms
ORCHESTRATION_TARGET_RANK_MS: float = settings.orchestration.target_rank_ms
ORCHESTRATION_TARGET_EXEC_MS: float = settings.orchestration.target_exec_ms
ORCHESTRATION_TARGET_TOTAL_MS: float = settings.orchestration.target_total_ms
ORCHESTRATION_MAX_SIGNALS_PER_ITERATION: int = settings.orchestration.max_signals_per_iteration
ORCHESTRATION_ENABLE_ITERATION_TRACE: bool = settings.orchestration.enable_iteration_trace
ORCHESTRATION_SCAN_ERROR_RATE_ABORT: float = settings.orchestration.scan_error_rate_abort
ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES: int = settings.orchestration.scan_error_min_samples
ORCHESTRATION_HARD_BUDGET_ENABLED: bool = settings.orchestration.hard_budget_enabled
ORCHESTRATION_MAX_SCAN_MS: float = settings.orchestration.max_scan_ms
ORCHESTRATION_MAX_RANK_MS: float = settings.orchestration.max_rank_ms
ORCHESTRATION_MAX_EXEC_MS: float = settings.orchestration.max_exec_ms
ORCHESTRATION_MAX_ITERATION_MS: float = settings.orchestration.max_iteration_ms
ORCHESTRATION_EXEC_BUDGET_COUNCIL_MARGIN_MS: float = settings.orchestration.exec_budget_council_margin_ms
SYMBOL_MAX_FAIL_COUNT: int = settings.orchestration.symbol_max_fail_count
SYMBOL_DISABLE_SECONDS: int = settings.orchestration.symbol_disable_seconds
PERMANENT_FAULT_SYMBOLS: set[str] = set(
    s.strip() for s in settings.orchestration.permanent_fault_symbols.split(",") if s.strip()
)
MARKET_CLOSED_SLEEP_TOTAL_SECONDS: int = settings.orchestration.market_closed_sleep_total_seconds
MARKET_CLOSED_SLEEP_INTERVAL_SECONDS: int = settings.orchestration.market_closed_sleep_interval_seconds
HTF_CACHE_TTL_M15_SECONDS: float = settings.orchestration.htf_cache_ttl_m15_seconds
HTF_CACHE_TTL_M5_SECONDS: float = settings.orchestration.htf_cache_ttl_m5_seconds
HTF_CACHE_TTL_M30_SECONDS: float = settings.orchestration.htf_cache_ttl_m30_seconds
HTF_CACHE_TTL_H4_SECONDS: float = settings.orchestration.htf_cache_ttl_h4_seconds
HTF_CACHE_TTL_D1_SECONDS: float = settings.orchestration.htf_cache_ttl_d1_seconds
HTF_CACHE_TTL_MULTIPLIER_LONDON_NY: float = settings.orchestration.htf_cache_ttl_multiplier_london_ny
HTF_CACHE_TTL_MULTIPLIER_ASIA: float = settings.orchestration.htf_cache_ttl_multiplier_asia

# Opportunity
OPPORTUNITY_PHASE_ENABLED: bool = settings.opportunity.enabled
OPPORTUNITY_ROLLOVER_SECONDS: int = settings.opportunity.rollover_seconds
OPPORTUNITY_WATCH_WINDOW_SECONDS: int = settings.opportunity.watch_window_seconds
OPPORTUNITY_HEDGE_TIMEOUT_SECONDS: int = settings.opportunity.hedge_timeout_seconds
OPPORTUNITY_MIN_RECOVERY_CONFIDENCE: float = settings.opportunity.min_recovery_confidence
OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT: float = settings.opportunity.fallback_max_spread_pct
OPPORTUNITY_SHOCK_LOOKBACK_SECONDS: int = settings.opportunity.shock_lookback_seconds
OPPORTUNITY_SHOCK_DROP_THRESHOLD: float = settings.opportunity.shock_drop_threshold
OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE: bool = settings.opportunity.require_shock_for_fast_lane
OPPORTUNITY_LIVE_ENABLED: bool = settings.opportunity.live_enabled

# Protection
PROTECTIONS_ENABLED: bool = settings.protection.enabled
PROTECTION_COOLDOWN_MINUTES: int = settings.protection.cooldown_minutes
PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES: int = settings.protection.stoploss_guard_lookback_minutes
PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT: int = settings.protection.stoploss_guard_trade_limit
PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES: int = settings.protection.stoploss_guard_lock_minutes
PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES: int = settings.protection.global_loss_guard_lookback_minutes
PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES: int = settings.protection.global_loss_guard_max_losses
PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES: int = settings.protection.global_loss_guard_lock_minutes
CONSECUTIVE_REJECT_LIMIT: int = settings.protection.consecutive_reject_limit
CONSECUTIVE_REJECT_COOLDOWN_MINUTES: int = settings.protection.consecutive_reject_cooldown_minutes

# Time phase
TIME_PHASE_CONFIDENCE_ENABLED: bool = settings.time_phase.enabled
TIME_PHASE_BUCKET_MINUTES: int = settings.time_phase.bucket_minutes
TIME_PHASE_EARLY_MAX_MINUTE: int = settings.time_phase.early_max_minute
TIME_PHASE_MID_MAX_MINUTE: int = settings.time_phase.mid_max_minute
TIME_PHASE_MIN_CONF_EARLY: float = settings.time_phase.min_conf_early
TIME_PHASE_MIN_CONF_MID: float = settings.time_phase.min_conf_mid
TIME_PHASE_MIN_CONF_LATE: float = settings.time_phase.min_conf_late

# Telegram
TELEGRAM_BOT_TOKEN: str = settings.telegram.bot_token
TELEGRAM_CHAT_ID: str = settings.telegram.chat_id
TELEGRAM_NOISE_FILTER_ENABLED: bool = settings.telegram.noise_filter_enabled
TELEGRAM_DEDUPE_WINDOW_SECONDS: int = settings.telegram.dedupe_window_seconds
TELEGRAM_RATE_LIMIT_PER_MINUTE: int = settings.telegram.rate_limit_per_minute
TELEGRAM_SUPPRESSION_REPORT_EVERY: int = settings.telegram.suppression_report_every
TELEGRAM_CHART_DAYS: int = settings.telegram.chart_days
TELEGRAM_ALLOWED_USERNAMES: tuple[str, ...] = settings.telegram.allowed_usernames
TELEGRAM_ALLOWED_USER_IDS: tuple[int, ...] = settings.telegram.allowed_user_ids

# Intelligence
ALPHA_VANTAGE_KEY: str = settings.intelligence.alpha_vantage_key
TWELVE_DATA_KEY: str = settings.intelligence.twelve_data_key
FRED_API_KEY: str = settings.intelligence.fred_api_key
YFINANCE_ENABLED: bool = settings.intelligence.yfinance_enabled
INTELLIGENCE_SWEEP_INTERVAL_MINUTES: int = settings.intelligence.sweep_interval_minutes
MT5_DB_SYNC_INTERVAL_SECONDS: int = settings.intelligence.mt5_db_sync_interval_seconds
NEWS_CALENDAR_SOURCE: str = settings.intelligence.news_calendar_source
FINNHUB_API_KEY: str = settings.intelligence.finnhub_api_key
NEWS_BLACKOUT_MINUTES: int = settings.intelligence.news_blackout_minutes
ANTHROPIC_API_KEY: str = settings.intelligence.anthropic_api_key
DEEPSEEK_API_KEY: str = settings.intelligence.deepseek_api_key
DEEPSEEK_MODEL: str = "deepseek-chat"
CRUCIX_URL: str = settings.intelligence.crucix_url

# Learning
DEFAULT_CONFIDENCE: float = settings.learning.default_confidence
INITIAL_CONFIDENCE: float = settings.learning.initial_confidence
CONFIDENCE_ALLOW: float = settings.learning.confidence_allow
CONFIDENCE_REDUCED: float = settings.learning.confidence_reduced
CONFIDENCE_FULL: float = settings.learning.confidence_full
CONFIDENCE_DISABLE_THRESHOLD: float = settings.learning.confidence_disable_threshold
METRICS_LOG_EVERY_N_LOOPS: int = settings.learning.metrics_log_every_n_loops

# Backtest
BACKTEST_COMMISSION_PER_LOT_PER_SIDE: float = settings.backtest.commission_per_lot_per_side
BACKTEST_WALK_FORWARD_ENABLED: bool = settings.backtest.walk_forward_enabled
BACKTEST_WALK_FORWARD_WINDOW_DAYS: int = settings.backtest.walk_forward_window_days

# Misc
LOG_LEVEL: str = settings.misc.log_level
SENTRY_DSN: str = settings.misc.sentry_dsn
DAILY_SUMMARY_HOUR: int = settings.misc.daily_summary_hour
TIMEZONE: str = settings.misc.timezone
DEFAULT_SYMBOL: str = settings.misc.default_symbol
DEFAULT_TIMEFRAME: str = settings.misc.default_timeframe
DATABASE_URL: str = settings.misc.database_url
DB_PATH: str = settings.misc.db_path
ENCRYPTION_KEY: str = settings.misc.encryption_key
SMA_FAST_PERIOD: int = settings.misc.sma_fast_period
SMA_SLOW_PERIOD: int = settings.misc.sma_slow_period

# Session
ENTRY_ALLOWED_SESSIONS: list = settings.session.allowed_sessions
ENTRY_BLOCKED_DAYS: list = settings.session.blocked_days
MTF_MIN_ALIGNMENT: float = settings.session.mtf_min_alignment
WEEKEND_SYMBOLS: str = settings.session.weekend_symbols

# Strategy plugins
STRATEGY_PLUGINS: tuple[str, ...] = settings.strategy_plugin.plugins
STRATEGY_PLUGIN_FAIL_FAST: bool = settings.strategy_plugin.fail_fast

# OpenRouter
OPENROUTER_API_KEY: str = settings.openrouter.api_key
OPENROUTER_BASE_URL: str = settings.openrouter.base_url
OPENROUTER_MODEL: str = settings.openrouter.model
OPENROUTER_FALLBACK_ENABLED: bool = settings.openrouter.fallback_enabled

# MCP
MCP_SERVER_PORT: int = settings.mcp.port
MCP_SERVER_ENABLED: bool = settings.mcp.enabled

# Tool system
TOOL_SYSTEM_ENABLED: bool = settings.tool_system.enabled
TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS: int = settings.tool_system.autorun_every_n_loops
TOOL_SYSTEM_STRICT_CRITICAL: bool = settings.tool_system.strict_critical
TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE: int = settings.tool_system.max_actions_per_cycle
TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD: int = settings.tool_system.warning_spike_threshold
TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES: int = settings.tool_system.emergency_recovery_cycles
TOOL_SYSTEM_EMERGENCY_SYMBOLS: str = settings.tool_system.emergency_symbols
TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE: float = settings.tool_system.emergency_max_risk_per_trade
TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES: int = settings.tool_system.emergency_max_open_trades
TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS: int = settings.tool_system.reweight_lookback_hours
TOOL_SYSTEM_REWEIGHT_MIN_TRADES: int = settings.tool_system.reweight_min_trades

# Execution failure
EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS: int = settings.execution_failure.autotrading_error_cooldown_seconds
EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS: float = settings.execution_failure.pending_confirm_timeout_seconds
EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS: float = settings.execution_failure.pending_confirm_poll_interval_seconds
SPREAD_REJECT_COOLDOWN_HITS: int = settings.execution_failure.spread_reject_cooldown_hits
SPREAD_REJECT_COOLDOWN_SECONDS: int = settings.execution_failure.spread_reject_cooldown_seconds

# Data validation
STUCK_QUOTE_THRESHOLD: int = settings.data_validation.stuck_quote_threshold
STUCK_QUOTE_THRESHOLD_CRYPTO: int = settings.data_validation.stuck_quote_threshold_crypto
SPIKE_PERCENT_THRESHOLD: float = settings.data_validation.spike_percent_threshold

# Neural models dir (special — computed path)
NEURAL_MODELS_DIR: str = str(
    Path(__file__).resolve().parent.parent / "models" / "neural"
)

# HKU Marketplace
HKU_ENABLED: bool = settings.hku.enabled
HKU_API_URL: str = settings.hku.api_url
HKU_API_KEY: str = settings.hku.api_key
HKU_SIGNAL_DISCOUNT: float = settings.hku.signal_discount
HKU_PUBLISH_ON_STRATEGY: bool = settings.hku.publish_on_strategy
HKU_PUBLISH_ON_DISCUSSION: bool = settings.hku.publish_on_discussion
HKU_FEED_LIMIT: int = settings.hku.feed_limit
HKU_CIRCUIT_BREAKER_TIMEOUT_SECS: int = settings.hku.circuit_breaker_timeout_secs
HKU_COPY_TRADING_ENABLED: bool = settings.hku.copy_trading_enabled
HKU_COPY_LEADER_IDS: list[str] = settings.hku.copy_leader_ids
HKU_COPY_MARGIN_FRACTION: float = settings.hku.copy_margin_fraction
HKU_COPY_MAX_TRADES: int = settings.hku.copy_max_trades
HKU_COPY_MIN_WINRATE: float = settings.hku.copy_min_winrate
HKU_COPY_SL_ATR: float = settings.hku.copy_sl_atr
HKU_COPY_TP_ATR: float = settings.hku.copy_tp_atr
