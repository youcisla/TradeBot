"""All configurable parameters for the trading bot.

Validated at startup via Pydantic.  All values are also re-exported as
flat module-level variables so existing code (`from config.settings import
BROKER_ACCOUNT`) continues to work without any changes.

New code should prefer the structured ``settings`` object::

    from config.settings import settings
    if settings.risk.max_risk_per_trade > 0.05:
        ...

Environment variables are loaded from ``.env`` in the project root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Load .env ────────────────────────────────────────────────────────────
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


# ── Broker settings ───────────────────────────────────────────────────────

class BrokerSettings(BaseModel):
    account: str = ""
    password: str = ""
    server: str = ""


# ── Risk settings ─────────────────────────────────────────────────────────

class RiskSettings(BaseModel):
    max_risk_per_trade: float = Field(default=0.02, ge=0.0001, le=0.50)
    max_open_trades: int = Field(default=5, ge=1, le=50)
    max_daily_loss: float = Field(default=0.05, ge=0.001, le=0.50)
    max_monthly_loss: float = Field(default=0.10, ge=0.001, le=0.99)
    max_spread_pips: float = Field(default=8.0, ge=0.0)
    max_spread_pips_commodity: float = Field(default=10.0, ge=0.0)
    max_spread_pips_exotic: float = Field(default=15.0, ge=0.0)
    max_spread_pct_crypto: float = Field(default=2.5, ge=0.0)
    max_spread_points_index: float = Field(default=5.0, ge=0.0)
    drawdown_cooldown_hours: int = Field(default=24, ge=0)
    min_lot_size: float = Field(default=0.01, ge=0.0)
    max_lot_size: float = Field(default=50.0, ge=0.0)
    fixed_lot_size: float = Field(default=0.0, ge=0.0)
    position_size_mode: str = "equity_pct"
    position_size_fixed_lot: float = Field(default=0.10, ge=0.0)
    position_size_fixed_risk_amount: float = Field(default=100.0, ge=0.0)
    kelly_min_trades: int = Field(default=20, ge=2)
    kelly_lookback_days: int = Field(default=90, ge=7)
    kelly_half: bool = True
    risk_validation_profile: str = "agile"
    risk_agile_high_conf_threshold: float = Field(default=0.74, ge=0.0, le=1.0)
    risk_agile_spread_multiplier: float = Field(default=1.35, ge=0.0)

    @field_validator("position_size_mode", mode="before")
    @classmethod
    def _lowercase_str(cls, v: str) -> str:
        return str(v).lower()


# ── Guard pipeline settings ───────────────────────────────────────────────

class GuardSettings(BaseModel):
    enabled: bool = True
    cooldown_seconds: int = Field(default=300, ge=0)
    max_daily_loss_pct: float = Field(default=0.05, ge=0.0, le=1.0)
    max_vix: float = Field(default=40.0, ge=0.0)
    feed_staleness_seconds: float = Field(default=120.0, ge=0.0)


# ── Execution / TP settings ───────────────────────────────────────────────

class ExecutionSettings(BaseModel):
    tp1_close_percent: float = Field(default=0.40, ge=0.0, le=1.0)
    tp2_close_percent: float = Field(default=0.30, ge=0.0, le=1.0)
    tp3_close_percent: float = Field(default=0.20, ge=0.0, le=1.0)
    tp4_close_percent: float = Field(default=0.10, ge=0.0, le=1.0)
    trailing_stop_distance_pips: float = Field(default=20.0, ge=0.0)
    commission_per_lot: float = Field(default=7.0, ge=0.0)
    commission_per_lot_crypto: float = Field(default=7.0, ge=0.0)
    commission_per_lot_commodity: float = Field(default=7.0, ge=0.0)
    commission_per_lot_exotic: float = Field(default=7.0, ge=0.0)
    breakeven_spread_offset: bool = True
    limit_entry_max_distance_atr: float = Field(default=0.5, ge=0.0)
    limit_entry_max_distance_atr_crypto: float = Field(default=2.0, ge=0.0)

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

class SniperSettings(BaseModel):
    enabled: bool = True
    conf_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    timeout_minutes: float = Field(default=30.0, ge=0.0)
    max_entry_atr_distance: float = Field(default=0.55, ge=0.0)
    fib_min_depth: str = "acceptable"
    fib_max_depth: str = "deep"

    @field_validator("fib_min_depth", "fib_max_depth", mode="before")
    @classmethod
    def _lowercase_str(cls, v: str) -> str:
        return str(v).lower()


class DeferredSettings(BaseModel):
    enabled: bool = True
    max_age_seconds: int = Field(default=900, ge=0)
    max_atr_distance: float = Field(default=0.35, ge=0.0)
    min_conf: float = Field(default=0.60, ge=0.0, le=1.0)
    ttl_seconds: int = Field(default=900, ge=0)


# ── Fast lane / instant entry settings ─────────────────────────────────────

class FastLaneSettings(BaseModel):
    enabled: bool = True
    max_signals: int = Field(default=1, ge=0)
    close_on_full_reject: bool = True


class InstantEntrySettings(BaseModel):
    enabled: bool = True
    min_confidence: float = Field(default=0.78, ge=0.0, le=1.0)


class ExposureSettings(BaseModel):
    enabled: bool = False
    reduce_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    cash_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    win_rate_lookback: int = Field(default=10, ge=1)


# ── ML / neural settings ─────────────────────────────────────────────────

class NeuralSettings(BaseModel):
    min_candles: int = Field(default=65, ge=1)
    seq_len: int = Field(default=50, ge=1)
    hidden_size: int = Field(default=128, ge=1)
    num_layers: int = Field(default=2, ge=1)
    train_epochs: int = Field(default=100, ge=1)
    retrain_every: int = Field(default=20, ge=1)
    min_confidence: float = Field(default=0.55, ge=0.0, le=1.0)
    lgbm_ensemble_enabled: bool = True
    kalman_enabled: bool = Field(default=False)


class GarchSettings(BaseModel):
    enabled: bool = True
    high_vol_threshold: float = Field(default=2.0, ge=0.0)


# ── ICT strategy settings ─────────────────────────────────────────────────

class ICTSettings(BaseModel):
    min_confidence: int = Field(default=30, ge=0, le=100)
    h4_candle_count: int = Field(default=200, ge=1)
    d1_candle_count: int = Field(default=20, ge=1)
    m30_candle_count: int = Field(default=100, ge=1)
    m15_candle_count: int = Field(default=250, ge=1)
    m5_candle_count: int = Field(default=100, ge=1)
    mtf_alignment_boost: float = Field(default=0.05, ge=0.0, le=1.0)
    mtf_d1_veto: bool = True
    regime_adx_trending: float = Field(default=25.0, ge=0.0)
    regime_adx_ranging: float = Field(default=20.0, ge=0.0)
    regime_confidence_penalty: float = Field(default=0.10, ge=0.0, le=1.0)
    tp_trending_tp1_mult: float = Field(default=1.5, ge=0.0)
    tp_trending_tp2_mult: float = Field(default=2.5, ge=0.0)
    tp_trending_tp3_mult: float = Field(default=4.0, ge=0.0)
    tp_trending_tp4_mult: float = Field(default=6.0, ge=0.0)
    tp_ranging_tp1_mult: float = Field(default=0.8, ge=0.0)
    tp_ranging_tp2_mult: float = Field(default=1.5, ge=0.0)
    tp_ranging_tp3_mult: float = Field(default=2.5, ge=0.0)
    max_hours_in_trade: int = Field(default=48, ge=0)
    min_ict_score_crypto: float = Field(default=35.0, ge=0.0)
    # confidence floors by regime
    min_conf_trending: float = Field(default=0.40, ge=0.0, le=1.0)
    min_conf_ranging: float = Field(default=0.40, ge=0.0, le=1.0)
    min_conf_volatile: float = Field(default=0.40, ge=0.0, le=1.0)
    min_conf_unknown: float = Field(default=0.40, ge=0.0, le=1.0)
    min_conf_crypto_bonus: float = Field(default=0.03, ge=0.0, le=1.0)
    min_conf_exotic_bonus: float = Field(default=0.04, ge=0.0, le=1.0)
    # size-scale thresholds
    size_scale_very_low_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    size_scale_low_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    size_scale_medium_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    size_scale_very_low: float = Field(default=0.35, ge=0.0, le=1.0)
    size_scale_low: float = Field(default=0.55, ge=0.0, le=1.0)
    size_scale_medium: float = Field(default=0.75, ge=0.0, le=1.0)
    size_scale_full: float = Field(default=1.00, ge=0.0, le=1.0)


# ── Orchestration / loop settings ───────────────────────────────────────────

class OrchestrationSettings(BaseModel):
    loop_interval_seconds: int = Field(default=5, ge=1, le=600)
    reconcile_every_n_loops: int = Field(default=60, ge=1)
    candle_server_port: int = Field(default=5555, ge=1, le=65535)
    scan_cooldown_seconds: int = Field(default=300, ge=0)
    scan_cooldown_seconds_london_ny: int = Field(default=60, ge=0)
    scan_cooldown_seconds_asia: int = Field(default=120, ge=0)
    btc_priority_symbol: str = "BTCUSD"
    btc_priority_scan_cooldown_seconds: int = Field(default=8, ge=0)
    event_driven_rescan_on_new_candle: bool = True
    # orchestration perf
    scan_workers_min: int = Field(default=2, ge=1)
    scan_workers_max: int = Field(default=10, ge=1)
    scan_workers_default: int = Field(default=6, ge=1)
    adaptive_workers_enabled: bool = True
    target_scan_ms: float = Field(default=15000, ge=0)
    target_rank_ms: float = Field(default=200, ge=0)
    target_exec_ms: float = Field(default=800, ge=0)
    target_total_ms: float = Field(default=60000, ge=0)
    max_signals_per_iteration: int = Field(default=20, ge=1)
    enable_iteration_trace: bool = True
    scan_error_rate_abort: float = Field(default=0.70, ge=0.0, le=1.0)
    scan_error_min_samples: int = Field(default=5, ge=1)
    hard_budget_enabled: bool = True
    max_scan_ms: float = Field(default=90000, ge=0)
    max_rank_ms: float = Field(default=1000, ge=0)
    max_exec_ms: float = Field(default=3000, ge=0)
    max_iteration_ms: float = Field(default=120000, ge=0)
    exec_budget_council_margin_ms: float = Field(default=350, ge=0)
    # symbol fault — raised from 12/3600 after Apr 2026 stuck-quote cascade
    # that disabled all 43 equity symbols simultaneously. 20 failures + 30-min
    # cooldown gives transient broker hiccups more slack before kicking in.
    symbol_max_fail_count: int = Field(default=20, ge=1)
    symbol_disable_seconds: int = Field(default=1800, ge=0)
    # market closed sleep (total = sleep_total / sleep_interval, e.g. 300/10 = 30 iterations × 10s = 5 min)
    market_closed_sleep_total_seconds: int = Field(default=300, ge=1)
    market_closed_sleep_interval_seconds: int = Field(default=10, ge=1)
    # HTF cache TTLs
    htf_cache_ttl_m15_seconds: float = Field(default=20, ge=0)
    htf_cache_ttl_m5_seconds: float = Field(default=15, ge=0)
    htf_cache_ttl_m30_seconds: float = Field(default=30, ge=0)
    htf_cache_ttl_h4_seconds: float = Field(default=120, ge=0)
    htf_cache_ttl_d1_seconds: float = Field(default=300, ge=0)
    htf_cache_ttl_multiplier_london_ny: float = Field(default=0.75, ge=0.0)
    htf_cache_ttl_multiplier_asia: float = Field(default=1.35, ge=0.0)


# ── Opportunity lifecycle settings ─────────────────────────────────────────

class OpportunitySettings(BaseModel):
    enabled: bool = True
    rollover_seconds: int = Field(default=900, ge=0)
    watch_window_seconds: int = Field(default=180, ge=0)
    hedge_timeout_seconds: int = Field(default=300, ge=0)
    min_recovery_confidence: float = Field(default=0.62, ge=0.0, le=1.0)
    fallback_max_spread_pct: float = Field(default=0.003, ge=0.0)
    shock_lookback_seconds: int = Field(default=5, ge=0)
    shock_drop_threshold: float = Field(default=0.0015, ge=0.0)
    require_shock_for_fast_lane: bool = True
    live_enabled: bool = False


# ── Protection layer settings ──────────────────────────────────────────────

class ProtectionSettings(BaseModel):
    enabled: bool = True
    cooldown_minutes: int = Field(default=10, ge=0)
    stoploss_guard_lookback_minutes: int = Field(default=180, ge=0)
    stoploss_guard_trade_limit: int = Field(default=3, ge=0)
    stoploss_guard_lock_minutes: int = Field(default=60, ge=0)
    global_loss_guard_lookback_minutes: int = Field(default=120, ge=0)
    global_loss_guard_max_losses: int = Field(default=4, ge=0)
    global_loss_guard_lock_minutes: int = Field(default=45, ge=0)
    # Consecutive-reject circuit breaker (gabagool pattern)
    consecutive_reject_limit: int = Field(default=5, ge=2)
    consecutive_reject_cooldown_minutes: int = Field(default=15, ge=1)


# ── Time-phase confidence gate settings ───────────────────────────────────

class TimePhaseSettings(BaseModel):
    enabled: bool = False
    bucket_minutes: int = Field(default=15, ge=1)
    early_max_minute: int = Field(default=3, ge=0)
    mid_max_minute: int = Field(default=11, ge=0)
    min_conf_early: float = Field(default=0.55, ge=0.0, le=1.0)
    min_conf_mid: float = Field(default=0.50, ge=0.0, le=1.0)
    min_conf_late: float = Field(default=0.48, ge=0.0, le=1.0)


# ── Telegram settings ──────────────────────────────────────────────────────

class TelegramSettings(BaseModel):
    bot_token: str = ""
    chat_id: str = ""
    noise_filter_enabled: bool = True
    dedupe_window_seconds: int = Field(default=180, ge=0)
    rate_limit_per_minute: int = Field(default=20, ge=0)
    suppression_report_every: int = Field(default=10, ge=0)
    chart_days: int = Field(default=30, ge=1)
    allowed_usernames: tuple[str, ...] = Field(default_factory=tuple)
    allowed_user_ids: tuple[int, ...] = Field(default_factory=tuple)


# ── Intelligence / data feed settings ─────────────────────────────────────

class IntelligenceSettings(BaseModel):
    deepseek_api_key: str = ""
    alpha_vantage_key: str = ""
    twelve_data_key: str = ""
    fred_api_key: str = ""
    yfinance_enabled: bool = True
    sweep_interval_minutes: int = Field(default=15, ge=1)
    mt5_db_sync_interval_seconds: int = Field(default=300, ge=0)
    news_calendar_source: str = "static"
    finnhub_api_key: str = ""
    news_blackout_minutes: int = Field(default=15, ge=0)
    crucix_url: str = "https://crucix-pi.vercel.app"


# ── ML / learning system settings ─────────────────────────────────────────

class LearningSettings(BaseModel):
    default_confidence: float = 0.5
    initial_confidence: float = 0.5
    confidence_allow: float = 0.3
    confidence_reduced: float = 0.5
    confidence_full: float = 0.7
    confidence_disable_threshold: float = 0.2
    metrics_log_every_n_loops: int = Field(default=5, ge=1)


# ── Backtest settings ──────────────────────────────────────────────────────

class BacktestSettings(BaseModel):
    commission_per_lot_per_side: float = Field(default=0.0001, ge=0.0)
    walk_forward_enabled: bool = False
    walk_forward_window_days: int = Field(default=90, ge=1)


# ── Logging / misc settings ────────────────────────────────────────────────

class MiscSettings(BaseModel):
    log_level: str = "INFO"
    daily_summary_hour: int = Field(default=17, ge=0, le=23)
    timezone: str = "Europe/Paris"
    default_symbol: str = "BTCUSD"
    default_timeframe: str = "H1"
    database_url: str = ""
    db_path: str = ""
    encryption_key: str = ""
    sma_fast_period: int = Field(default=10, ge=1)
    sma_slow_period: int = Field(default=50, ge=1)


# ── Market session settings ────────────────────────────────────────────────

class SessionSettings(BaseModel):
    allowed_sessions: list[str] = ["asian", "london", "overlap"]
    blocked_days: list[str] = ["Saturday", "Sunday"]
    mtf_min_alignment: float = Field(default=0.0, ge=0.0, le=1.0)
    weekend_symbols: str = "BTCUSD,ETHUSD,BNBUSD,SOLUSD,XRPUSD,ADAUSD,DOTUSD,LTCUSD,EOSUSD,XLMUSD,TRXUSD"


# ── Strategy plugin settings ─────────────────────────────────────────────────

class StrategyPluginSettings(BaseModel):
    plugins: tuple[str, ...] = Field(default_factory=tuple)
    fail_fast: bool = False


# ── OpenRouter / LLM settings (disabled code) ─────────────────────────────

class OpenRouterSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "anthropic/claude-3-haiku"
    fallback_enabled: bool = False


# ── MCP server settings ─────────────────────────────────────────────────────

class MCPSettings(BaseModel):
    enabled: bool = False
    port: int = Field(default=8080, ge=1, le=65535)


# ── HKU Marketplace settings ──────────────────────────────────────────────

class HKUSettings(BaseModel):
    enabled: bool = False
    api_url: str = ""
    api_key: str = ""
    signal_discount: float = Field(default=0.80, ge=0.0, le=1.0)
    publish_on_strategy: bool = True
    publish_on_discussion: bool = True
    feed_limit: int = Field(default=10, ge=1, le=50)
    circuit_breaker_timeout_secs: int = Field(default=300, ge=60)
    # Copy trading
    copy_trading_enabled: bool = False
    copy_leader_ids: list[str] = Field(default_factory=list)
    copy_margin_fraction: float = Field(default=0.05, ge=0.01, le=0.25)
    copy_max_trades: int = Field(default=3, ge=1, le=10)
    copy_min_winrate: float = Field(default=0.55, ge=0.0, le=1.0)
    copy_sl_atr: float = Field(default=1.5, ge=0.5, le=5.0)
    copy_tp_atr: float = Field(default=2.5, ge=0.5, le=10.0)


# ── Tool system settings ───────────────────────────────────────────────────

class ToolSystemSettings(BaseModel):
    enabled: bool = True
    autorun_every_n_loops: int = Field(default=5, ge=1)
    strict_critical: bool = True
    max_actions_per_cycle: int = Field(default=8, ge=0)
    warning_spike_threshold: int = Field(default=2, ge=0)
    emergency_recovery_cycles: int = Field(default=2, ge=0)
    emergency_symbols: str = "BTCUSD,ETHUSD,XAUUSD,EURUSD"
    emergency_max_risk_per_trade: float = Field(default=0.005, ge=0.0, le=1.0)
    emergency_max_open_trades: int = Field(default=1, ge=0)
    reweight_lookback_hours: int = Field(default=48, ge=0)
    reweight_min_trades: int = Field(default=4, ge=0)


# ── Execution failure backoff settings ──────────────────────────────────────

class ExecutionFailureSettings(BaseModel):
    autotrading_error_cooldown_seconds: int = Field(default=300, ge=0)
    pending_confirm_timeout_seconds: float = Field(default=4.0, ge=0.0)
    pending_confirm_poll_interval_seconds: float = Field(default=0.25, ge=0.0)
    spread_reject_cooldown_hits: int = Field(default=3, ge=0)
    spread_reject_cooldown_seconds: int = Field(default=300, ge=0)


# ── Data validation settings ────────────────────────────────────────────────

class DataValidationSettings(BaseModel):
    stuck_quote_threshold: int = Field(default=10, ge=0)
    stuck_quote_threshold_crypto: int = Field(default=14, ge=0)
    spike_percent_threshold: float = Field(default=2.0, ge=0.0)


# ── DeepSeek settings (disabled code — kept for reference) ─────────────────

class DeepSeekSettings(BaseModel):
    api_key: str = ""
    model: str = "deepseek-chat"
    quick_model: str = "deepseek-chat"
    deep_model: str = "deepseek-reasoner"
    min_confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    schema_version: str = "v1"
    cache_minutes: int = Field(default=30, ge=0)
    r_mult_tolerance: float = Field(default=0.25, ge=0.0)
    quick_timeout_seconds: float = Field(default=10, ge=0.0)
    deep_timeout_seconds: float = Field(default=8, ge=0.0)
    enable_deep_verify: bool = True
    deep_verify_min_confidence: float = Field(default=0.78, ge=0.0, le=1.0)
    agent_swarm_enabled: bool = False
    agent_swarm_max_agents: int = Field(default=3, ge=1)
    agent_swarm_profiles: str = ""
    mesh_enabled: bool = True
    mesh_min_active_agents: int = Field(default=2, ge=0)
    mesh_latency_penalty: float = Field(default=0.25, ge=0.0, le=1.0)
    mesh_trust_alpha: float = Field(default=0.18, ge=0.0, le=1.0)
    mesh_min_trust: float = Field(default=0.15, ge=0.0, le=1.0)
    mesh_max_trust: float = Field(default=0.95, ge=0.0, le=1.0)
    metrics_log_every: int = Field(default=25, ge=1)


# ── Root settings model ─────────────────────────────────────────────────────

class _Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mode
    demo_mode: bool = False
    bot_profile: str = "custom"

    # Sub-models
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


def _get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _build_settings() -> _Settings:
    """Build the settings object manually from env vars.

    We parse env vars ourselves and construct sub-models so that:
    1. Pydantic validation runs on all values
    2. Existing code that reads env vars directly (os.getenv in this module)
       keeps working
    """
    # Parse tuple fields that need custom handling
    telegram_usernames_raw = _get_env("TELEGRAM_ALLOWED_USERNAMES", "")
    telegram_usernames = tuple(
        u.strip().lstrip("@").lower()
        for u in telegram_usernames_raw.replace(";", ",").split(",")
        if u.strip()
    )
    telegram_user_ids = tuple(
        int(v.strip())
        for v in _get_env("TELEGRAM_ALLOWED_USER_IDS", "").replace(";", ",").split(",")
        if v.strip().isdigit()
    )
    entry_allowed_sessions = [
        s.strip() for s in _get_env("ENTRY_ALLOWED_SESSIONS", "asian,london,overlap").split(",")
        if s.strip()
    ]
    entry_blocked_days = [
        d.strip() for d in _get_env("ENTRY_BLOCKED_DAYS", "Saturday,Sunday").split(",")
        if d.strip()
    ]
    strategy_plugins = tuple(
        s.strip() for s in _get_env("STRATEGY_PLUGINS", "").split(",") if s.strip()
    )
    weekend_symbols = _get_env(
        "WEEKEND_SYMBOLS",
        "BTCUSD,ETHUSD,BNBUSD,SOLUSD,XRPUSD,ADAUSD,DOTUSD,LTCUSD,EOSUSD,XLMUSD,TRXUSD",
    )
    misc_db_path = _get_env(
        "DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "trading_bot.db"),
    )

    def _bool(name: str, default: str) -> bool:
        return _get_env(name, default).lower() == "true"

    def _int(name: str, default: str) -> int:
        return int(_get_env(name, default))

    def _float(name: str, default: str) -> float:
        return float(_get_env(name, default))

    def _str(name: str, default: str) -> str:
        return _get_env(name, default)

    demo_mode = _bool("DEMO_MODE", "false")
    bot_profile = _str("BOT_PROFILE", "custom").strip().lower()

    # Broker
    broker = BrokerSettings(
        account=_str("BROKER_ACCOUNT", ""),
        password=_str("BROKER_PASSWORD", ""),
        server=_str("BROKER_SERVER", ""),
    )

    # Risk
    risk = RiskSettings(
        max_risk_per_trade=_float("MAX_RISK_PER_TRADE", "0.02"),
        max_open_trades=_int("MAX_OPEN_TRADES", "12"),
        max_daily_loss=_float("MAX_DAILY_LOSS", "0.05"),
        max_monthly_loss=_float("MAX_MONTHLY_LOSS", "0.10"),
        max_spread_pips=_float("MAX_SPREAD_PIPS", "8.0"),
        max_spread_pips_commodity=_float("MAX_SPREAD_PIPS_COMMODITY", "10.0"),
        max_spread_pips_exotic=_float("MAX_SPREAD_PIPS_EXOTIC", "15.0"),
        max_spread_pct_crypto=_float("MAX_SPREAD_PCT_CRYPTO", "2.5"),
        max_spread_points_index=_float("MAX_SPREAD_POINTS_INDEX", "5.0"),
        drawdown_cooldown_hours=_int("DRAWDOWN_COOLDOWN_HOURS", "24"),
        min_lot_size=_float("MIN_LOT_SIZE", "0.01"),
        max_lot_size=_float("MAX_LOT_SIZE", "50.0"),
        fixed_lot_size=_float("FIXED_LOT_SIZE", "0.0"),
        position_size_mode=_str("POSITION_SIZE_MODE", "equity_pct").lower(),
        position_size_fixed_lot=_float("POSITION_SIZE_FIXED_LOT", "0.10"),
        position_size_fixed_risk_amount=_float("POSITION_SIZE_FIXED_RISK_AMOUNT", "100.0"),
        kelly_min_trades=_int("KELLY_MIN_TRADES", "20"),
        kelly_lookback_days=_int("KELLY_LOOKBACK_DAYS", "90"),
        kelly_half=_bool("KELLY_HALF", "true"),
        risk_validation_profile=_str("RISK_VALIDATION_PROFILE", "agile").lower(),
        risk_agile_high_conf_threshold=_float("RISK_AGILE_HIGH_CONF_THRESHOLD", "0.74"),
        risk_agile_spread_multiplier=_float("RISK_AGILE_SPREAD_MULTIPLIER", "1.35"),
    )

    # Guard
    guard = GuardSettings(
        enabled=_bool("GUARD_PIPELINE_ENABLED", "true"),
        cooldown_seconds=_int("GUARD_COOLDOWN_SECONDS", "300"),
        max_daily_loss_pct=_float("GUARD_MAX_DAILY_LOSS_PCT", "0.05"),
        max_vix=_float("GUARD_MAX_VIX", "40.0"),
        feed_staleness_seconds=_float("GUARD_FEED_STALENESS_SECONDS", "120"),
    )

    # Execution
    execution = ExecutionSettings(
        tp1_close_percent=_float("TP1_CLOSE_PERCENT", "0.40"),
        tp2_close_percent=_float("TP2_CLOSE_PERCENT", "0.30"),
        tp3_close_percent=_float("TP3_CLOSE_PERCENT", "0.20"),
        tp4_close_percent=_float("TP4_CLOSE_PERCENT", "0.10"),
        trailing_stop_distance_pips=_float("TRAILING_STOP_DISTANCE_PIPS", "20"),
        commission_per_lot=_float("COMMISSION_PER_LOT", "7.0"),
        commission_per_lot_crypto=_float("COMMISSION_PER_LOT_CRYPTO", "7.0"),
        commission_per_lot_commodity=_float("COMMISSION_PER_LOT_COMMODITY", "7.0"),
        commission_per_lot_exotic=_float("COMMISSION_PER_LOT_EXOTIC", "7.0"),
        breakeven_spread_offset=_bool("BREAKEVEN_SPREAD_OFFSET", "true"),
        limit_entry_max_distance_atr=_float("LIMIT_ENTRY_MAX_DISTANCE_ATR", "0.5"),
        limit_entry_max_distance_atr_crypto=_float("LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO", "2.0"),
    )

    # Sniper
    sniper = SniperSettings(
        enabled=_bool("SNIPER_ENTRY_ENABLED", "true"),
        conf_threshold=_float("SNIPER_CONF_THRESHOLD", "0.55"),
        timeout_minutes=_float("SNIPER_TIMEOUT_MINUTES", "30.0"),
        max_entry_atr_distance=_float("SNIPER_MAX_ENTRY_ATR_DISTANCE", "0.55"),
        fib_min_depth=_str("SNIPER_FIB_MIN_DEPTH", "acceptable").lower(),
        fib_max_depth=_str("SNIPER_FIB_MAX_DEPTH", "deep").lower(),
    )

    # Deferred
    deferred = DeferredSettings(
        enabled=_bool("DEFERRED_ENTRY_ENABLED", "true"),
        max_age_seconds=_int("DEFERRED_ENTRY_MAX_AGE_SECONDS", "900"),
        max_atr_distance=_float("DEFERRED_ENTRY_MAX_ATR_DISTANCE", "0.35"),
        min_conf=_float("DEFERRED_ENTRY_MIN_CONF", "0.60"),
        ttl_seconds=_int("DEFERRED_ENTRY_TTL_SECONDS", "900"),
    )

    # Fast lane
    fast_lane = FastLaneSettings(
        enabled=_bool("FAST_LANE_ENABLED", "true"),
        max_signals=_int("FAST_LANE_MAX_SIGNALS", "1"),
        close_on_full_reject=_bool("FAST_LANE_CLOSE_ON_FULL_REJECT", "true"),
    )

    # Instant entry
    instant_entry = InstantEntrySettings(
        enabled=_bool("INSTANT_ENTRY_ENABLED", "true"),
        min_confidence=_float("INSTANT_ENTRY_MIN_CONFIDENCE", "0.78"),
    )

    # Exposure
    exposure = ExposureSettings(
        enabled=_bool("EXPOSURE_ENABLED", "false"),
        reduce_threshold=_float("EXPOSURE_REDUCE_THRESHOLD", "0.40"),
        cash_threshold=_float("EXPOSURE_CASH_THRESHOLD", "0.20"),
        win_rate_lookback=_int("EXPOSURE_WIN_RATE_LOOKBACK", "10"),
    )

    # Neural
    neural = NeuralSettings(
        min_candles=_int("NEURAL_MIN_CANDLES", "65"),
        seq_len=_int("NEURAL_SEQ_LEN", "50"),
        hidden_size=_int("NEURAL_HIDDEN_SIZE", "128"),
        num_layers=_int("NEURAL_NUM_LAYERS", "2"),
        train_epochs=_int("NEURAL_TRAIN_EPOCHS", "100"),
        retrain_every=_int("NEURAL_RETRAIN_EVERY", "20"),
        min_confidence=_float("NEURAL_MIN_CONFIDENCE", "0.55"),
        lgbm_ensemble_enabled=_bool("LGBM_ENSEMBLE_ENABLED", "true"),
        kalman_enabled=_bool("KALMAN_ENABLED", "false"),
    )

    # GARCH
    garch = GarchSettings(
        enabled=_bool("GARCH_ENABLED", "true"),
        high_vol_threshold=_float("GARCH_HIGH_VOL_THRESHOLD", "2.0"),
    )

    # ICT
    ict = ICTSettings(
        min_confidence=_int("ICT_MIN_CONFIDENCE", "30"),
        h4_candle_count=_int("H4_CANDLE_COUNT", "200"),
        d1_candle_count=_int("D1_CANDLE_COUNT", "20"),
        m30_candle_count=_int("M30_CANDLE_COUNT", "100"),
        m15_candle_count=_int("M15_CANDLE_COUNT", "250"),
        m5_candle_count=_int("M5_CANDLE_COUNT", "100"),
        mtf_alignment_boost=_float("MTF_ALIGNMENT_BOOST", "0.05"),
        mtf_d1_veto=_bool("MTF_D1_VETO", "true"),
        regime_adx_trending=_float("REGIME_ADX_TRENDING", "25.0"),
        regime_adx_ranging=_float("REGIME_ADX_RANGING", "20.0"),
        regime_confidence_penalty=_float("REGIME_CONFIDENCE_PENALTY", "0.10"),
        tp_trending_tp1_mult=_float("TP_TRENDING_TP1_MULT", "1.5"),
        tp_trending_tp2_mult=_float("TP_TRENDING_TP2_MULT", "2.5"),
        tp_trending_tp3_mult=_float("TP_TRENDING_TP3_MULT", "4.0"),
        tp_trending_tp4_mult=_float("TP_TRENDING_TP4_MULT", "6.0"),
        tp_ranging_tp1_mult=_float("TP_RANGING_TP1_MULT", "0.8"),
        tp_ranging_tp2_mult=_float("TP_RANGING_TP2_MULT", "1.5"),
        tp_ranging_tp3_mult=_float("TP_RANGING_TP3_MULT", "2.5"),
        max_hours_in_trade=_int("MAX_HOURS_IN_TRADE", "48"),
        min_ict_score_crypto=_float("MIN_ICT_SCORE_CRYPTO", "35.0"),
        min_conf_trending=_float("MIN_CONF_TRENDING", "0.40"),
        min_conf_ranging=_float("MIN_CONF_RANGING", "0.40"),
        min_conf_volatile=_float("MIN_CONF_VOLATILE", "0.40"),
        min_conf_unknown=_float("MIN_CONF_UNKNOWN", "0.40"),
        min_conf_crypto_bonus=_float("MIN_CONF_CRYPTO_BONUS", "0.03"),
        min_conf_exotic_bonus=_float("MIN_CONF_EXOTIC_BONUS", "0.04"),
        size_scale_very_low_threshold=_float("SIZE_SCALE_VERY_LOW_THRESHOLD", "0.45"),
        size_scale_low_threshold=_float("SIZE_SCALE_LOW_THRESHOLD", "0.60"),
        size_scale_medium_threshold=_float("SIZE_SCALE_MEDIUM_THRESHOLD", "0.75"),
        size_scale_very_low=_float("SIZE_SCALE_VERY_LOW", "0.35"),
        size_scale_low=_float("SIZE_SCALE_LOW", "0.55"),
        size_scale_medium=_float("SIZE_SCALE_MEDIUM", "0.75"),
        size_scale_full=_float("SIZE_SCALE_FULL", "1.00"),
    )

    # Orchestration
    orchestration = OrchestrationSettings(
        loop_interval_seconds=_int("LOOP_INTERVAL_SECONDS", "5"),
        reconcile_every_n_loops=_int("RECONCILE_EVERY_N_LOOPS", "60"),
        candle_server_port=_int("CANDLE_SERVER_PORT", "5555"),
        scan_cooldown_seconds=_int("SCAN_COOLDOWN_SECONDS", "300"),
        scan_cooldown_seconds_london_ny=_int("SCAN_COOLDOWN_SECONDS_LONDON_NY", "60"),
        scan_cooldown_seconds_asia=_int("SCAN_COOLDOWN_SECONDS_ASIA", "120"),
        btc_priority_symbol=_str("BTC_PRIORITY_SYMBOL", "BTCUSD"),
        btc_priority_scan_cooldown_seconds=_int("BTC_PRIORITY_SCAN_COOLDOWN_SECONDS", "8"),
        event_driven_rescan_on_new_candle=_bool("EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE", "true"),
        scan_workers_min=_int("ORCHESTRATION_SCAN_WORKERS_MIN", "2"),
        scan_workers_max=_int("ORCHESTRATION_SCAN_WORKERS_MAX", "10"),
        scan_workers_default=_int("ORCHESTRATION_SCAN_WORKERS_DEFAULT", "6"),
        adaptive_workers_enabled=_bool("ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED", "true"),
        target_scan_ms=_float("ORCHESTRATION_TARGET_SCAN_MS", "15000"),
        target_rank_ms=_float("ORCHESTRATION_TARGET_RANK_MS", "200"),
        target_exec_ms=_float("ORCHESTRATION_TARGET_EXEC_MS", "800"),
        target_total_ms=_float("ORCHESTRATION_TARGET_TOTAL_MS", "60000"),
        max_signals_per_iteration=_int("ORCHESTRATION_MAX_SIGNALS_PER_ITERATION", "20"),
        enable_iteration_trace=_bool("ORCHESTRATION_ENABLE_ITERATION_TRACE", "true"),
        scan_error_rate_abort=_float("ORCHESTRATION_SCAN_ERROR_RATE_ABORT", "0.70"),
        scan_error_min_samples=_int("ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES", "5"),
        hard_budget_enabled=_bool("ORCHESTRATION_HARD_BUDGET_ENABLED", "true"),
        max_scan_ms=_float("ORCHESTRATION_MAX_SCAN_MS", "90000"),
        max_rank_ms=_float("ORCHESTRATION_MAX_RANK_MS", "1000"),
        max_exec_ms=_float("ORCHESTRATION_MAX_EXEC_MS", "3000"),
        max_iteration_ms=_float("ORCHESTRATION_MAX_ITERATION_MS", "120000"),
        exec_budget_council_margin_ms=_float("ORCHESTRATION_EXEC_BUDGET_COUNCIL_MARGIN_MS", "350"),
        symbol_max_fail_count=_int("SYMBOL_MAX_FAIL_COUNT", "20"),
        symbol_disable_seconds=_int("SYMBOL_DISABLE_SECONDS", "1800"),
        htf_cache_ttl_m15_seconds=_float("HTF_CACHE_TTL_M15_SECONDS", "20"),
        htf_cache_ttl_m5_seconds=_float("HTF_CACHE_TTL_M5_SECONDS", "15"),
        htf_cache_ttl_m30_seconds=_float("HTF_CACHE_TTL_M30_SECONDS", "30"),
        htf_cache_ttl_h4_seconds=_float("HTF_CACHE_TTL_H4_SECONDS", "120"),
        htf_cache_ttl_d1_seconds=_float("HTF_CACHE_TTL_D1_SECONDS", "300"),
        htf_cache_ttl_multiplier_london_ny=_float("HTF_CACHE_TTL_MULTIPLIER_LONDON_NY", "0.75"),
        htf_cache_ttl_multiplier_asia=_float("HTF_CACHE_TTL_MULTIPLIER_ASIA", "1.35"),
    )

    # Opportunity
    opportunity = OpportunitySettings(
        enabled=_bool("OPPORTUNITY_PHASE_ENABLED", "true"),
        rollover_seconds=_int("OPPORTUNITY_ROLLOVER_SECONDS", "900"),
        watch_window_seconds=_int("OPPORTUNITY_WATCH_WINDOW_SECONDS", "180"),
        hedge_timeout_seconds=_int("OPPORTUNITY_HEDGE_TIMEOUT_SECONDS", "300"),
        min_recovery_confidence=_float("OPPORTUNITY_MIN_RECOVERY_CONFIDENCE", "0.62"),
        fallback_max_spread_pct=_float("OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT", "0.003"),
        shock_lookback_seconds=_int("OPPORTUNITY_SHOCK_LOOKBACK_SECONDS", "5"),
        shock_drop_threshold=_float("OPPORTUNITY_SHOCK_DROP_THRESHOLD", "0.0015"),
        require_shock_for_fast_lane=_bool("OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE", "true"),
        live_enabled=_bool("OPPORTUNITY_LIVE_ENABLED", "false"),
    )

    # Protection
    protection = ProtectionSettings(
        enabled=_bool("PROTECTIONS_ENABLED", "true"),
        cooldown_minutes=_int("PROTECTION_COOLDOWN_MINUTES", "10"),
        stoploss_guard_lookback_minutes=_int("PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES", "180"),
        stoploss_guard_trade_limit=_int("PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT", "3"),
        stoploss_guard_lock_minutes=_int("PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES", "60"),
        global_loss_guard_lookback_minutes=_int("PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES", "120"),
        global_loss_guard_max_losses=_int("PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES", "4"),
        global_loss_guard_lock_minutes=_int("PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES", "45"),
        consecutive_reject_limit=_int("CONSECUTIVE_REJECT_LIMIT", "5"),
        consecutive_reject_cooldown_minutes=_int("CONSECUTIVE_REJECT_COOLDOWN_MINUTES", "15"),
    )

    # Time phase
    time_phase = TimePhaseSettings(
        enabled=_bool("TIME_PHASE_CONFIDENCE_ENABLED", "false"),
        bucket_minutes=_int("TIME_PHASE_BUCKET_MINUTES", "15"),
        early_max_minute=_int("TIME_PHASE_EARLY_MAX_MINUTE", "3"),
        mid_max_minute=_int("TIME_PHASE_MID_MAX_MINUTE", "11"),
        min_conf_early=_float("TIME_PHASE_MIN_CONF_EARLY", "0.55"),
        min_conf_mid=_float("TIME_PHASE_MIN_CONF_MID", "0.50"),
        min_conf_late=_float("TIME_PHASE_MIN_CONF_LATE", "0.48"),
    )

    # Telegram
    telegram = TelegramSettings(
        bot_token=_str("TELEGRAM_BOT_TOKEN", ""),
        chat_id=_str("TELEGRAM_CHAT_ID", ""),
        noise_filter_enabled=_bool("TELEGRAM_NOISE_FILTER_ENABLED", "true"),
        dedupe_window_seconds=_int("TELEGRAM_DEDUPE_WINDOW_SECONDS", "180"),
        rate_limit_per_minute=_int("TELEGRAM_RATE_LIMIT_PER_MINUTE", "20"),
        suppression_report_every=_int("TELEGRAM_SUPPRESSION_REPORT_EVERY", "10"),
        chart_days=_int("TELEGRAM_CHART_DAYS", "30"),
        allowed_usernames=telegram_usernames,
        allowed_user_ids=telegram_user_ids,
    )

    # Intelligence
    intelligence = IntelligenceSettings(
        deepseek_api_key=_str("DEEPSEEK_API_KEY", ""),
        alpha_vantage_key=_str("ALPHA_VANTAGE_KEY", ""),
        twelve_data_key=_str("TWELVE_DATA_KEY", ""),
        fred_api_key=_str("FRED_API_KEY", ""),
        yfinance_enabled=_bool("YFINANCE_ENABLED", "true"),
        sweep_interval_minutes=_int("INTELLIGENCE_SWEEP_INTERVAL_MINUTES", "15"),
        mt5_db_sync_interval_seconds=_int("MT5_DB_SYNC_INTERVAL_SECONDS", "300"),
        news_calendar_source=_str("NEWS_CALENDAR_SOURCE", "static"),
        finnhub_api_key=_str("FINNHUB_API_KEY", ""),
        news_blackout_minutes=_int("NEWS_BLACKOUT_MINUTES", "15"),
        crucix_url=_str("CRUCIX_URL", "https://crucix-pi.vercel.app"),
    )

    # Learning
    learning = LearningSettings(
        default_confidence=0.5,
        initial_confidence=0.5,
        confidence_allow=0.3,
        confidence_reduced=0.5,
        confidence_full=0.7,
        confidence_disable_threshold=0.2,
        metrics_log_every_n_loops=_int("METRICS_LOG_EVERY_N_LOOPS", "5"),
    )

    # Backtest
    backtest = BacktestSettings(
        commission_per_lot_per_side=_float("BACKTEST_COMMISSION_PER_LOT_PER_SIDE", "0.0001"),
        walk_forward_enabled=_bool("BACKTEST_WALK_FORWARD_ENABLED", "false"),
        walk_forward_window_days=_int("BACKTEST_WALK_FORWARD_WINDOW_DAYS", "90"),
    )

    # Misc
    misc = MiscSettings(
        log_level=_str("LOG_LEVEL", "INFO"),
        daily_summary_hour=_int("DAILY_SUMMARY_HOUR", "17"),
        timezone=_str("TIMEZONE", "Europe/Paris"),
        default_symbol=_str("DEFAULT_SYMBOL", "BTCUSD"),
        default_timeframe=_str("DEFAULT_TIMEFRAME", "H1"),
        database_url=_str("DATABASE_URL", ""),
        db_path=misc_db_path,
        encryption_key=_str("ENCRYPTION_KEY", ""),
        sma_fast_period=_int("SMA_FAST_PERIOD", "10"),
        sma_slow_period=_int("SMA_SLOW_PERIOD", "50"),
    )

    # Session
    session = SessionSettings(
        allowed_sessions=entry_allowed_sessions,
        blocked_days=entry_blocked_days,
        mtf_min_alignment=_float("MTF_MIN_ALIGNMENT", "0.0"),
        weekend_symbols=weekend_symbols,
    )

    # Strategy plugins
    strategy_plugin = StrategyPluginSettings(
        plugins=strategy_plugins,
        fail_fast=_bool("STRATEGY_PLUGIN_FAIL_FAST", "false"),
    )

    # OpenRouter
    openrouter = OpenRouterSettings(
        api_key=_str("OPENROUTER_API_KEY", ""),
        base_url=_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=_str("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
        fallback_enabled=_bool("OPENROUTER_FALLBACK_ENABLED", "false"),
    )

    # MCP
    mcp = MCPSettings(
        enabled=_bool("MCP_SERVER_ENABLED", "false"),
        port=_int("MCP_SERVER_PORT", "8080"),
    )

    # Tool system
    tool_system = ToolSystemSettings(
        enabled=_bool("TOOL_SYSTEM_ENABLED", "true"),
        autorun_every_n_loops=_int("TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS", "5"),
        strict_critical=_bool("TOOL_SYSTEM_STRICT_CRITICAL", "true"),
        max_actions_per_cycle=_int("TOOL_SYSTEM_MAX_ACTIONS_PER_CYCLE", "8"),
        warning_spike_threshold=_int("TOOL_SYSTEM_WARNING_SPIKE_THRESHOLD", "2"),
        emergency_recovery_cycles=_int("TOOL_SYSTEM_EMERGENCY_RECOVERY_CYCLES", "2"),
        emergency_symbols=_str("TOOL_SYSTEM_EMERGENCY_SYMBOLS", "BTCUSD,ETHUSD,XAUUSD,EURUSD"),
        emergency_max_risk_per_trade=_float("TOOL_SYSTEM_EMERGENCY_MAX_RISK_PER_TRADE", "0.005"),
        emergency_max_open_trades=_int("TOOL_SYSTEM_EMERGENCY_MAX_OPEN_TRADES", "1"),
        reweight_lookback_hours=_int("TOOL_SYSTEM_REWEIGHT_LOOKBACK_HOURS", "48"),
        reweight_min_trades=_int("TOOL_SYSTEM_REWEIGHT_MIN_TRADES", "4"),
    )

    # Execution failure
    execution_failure = ExecutionFailureSettings(
        autotrading_error_cooldown_seconds=_int("EXEC_AUTOTRADING_ERROR_COOLDOWN_SECONDS", "300"),
        pending_confirm_timeout_seconds=_float("EXEC_PENDING_CONFIRM_TIMEOUT_SECONDS", "4.0"),
        pending_confirm_poll_interval_seconds=_float("EXEC_PENDING_CONFIRM_POLL_INTERVAL_SECONDS", "0.25"),
        spread_reject_cooldown_hits=_int("SPREAD_REJECT_COOLDOWN_HITS", "3"),
        spread_reject_cooldown_seconds=_int("SPREAD_REJECT_COOLDOWN_SECONDS", "300"),
    )

    # Data validation
    data_validation = DataValidationSettings(
        stuck_quote_threshold=_int("STUCK_QUOTE_THRESHOLD", "10"),
        stuck_quote_threshold_crypto=_int("STUCK_QUOTE_THRESHOLD_CRYPTO", "14"),
        spike_percent_threshold=_float("SPIKE_PERCENT_THRESHOLD", "2.0"),
    )

    # HKU
    hku = HKUSettings(
        enabled=_bool("HKU_ENABLED", "false"),
        api_url=_str("HKU_API_URL", ""),
        api_key=_str("HKU_API_KEY", ""),
        signal_discount=_float("HKU_SIGNAL_DISCOUNT", "0.80"),
        publish_on_strategy=_bool("HKU_PUBLISH_ON_STRATEGY", "true"),
        publish_on_discussion=_bool("HKU_PUBLISH_ON_DISCUSSION", "true"),
        feed_limit=_int("HKU_FEED_LIMIT", "10"),
        circuit_breaker_timeout_secs=_int("HKU_CIRCUIT_BREAKER_TIMEOUT_SECS", "300"),
    )

    return _Settings(
        demo_mode=demo_mode,
        bot_profile=bot_profile,
        broker=broker,
        risk=risk,
        guard=guard,
        execution=execution,
        sniper=sniper,
        deferred=deferred,
        fast_lane=fast_lane,
        instant_entry=instant_entry,
        exposure=exposure,
        neural=neural,
        garch=garch,
        ict=ict,
        orchestration=orchestration,
        opportunity=opportunity,
        protection=protection,
        time_phase=time_phase,
        telegram=telegram,
        intelligence=intelligence,
        learning=learning,
        backtest=backtest,
        misc=misc,
        session=session,
        strategy_plugin=strategy_plugin,
        openrouter=openrouter,
        mcp=mcp,
        tool_system=tool_system,
        execution_failure=execution_failure,
        data_validation=data_validation,
        hku=hku,
    )


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

settings = _apply_profile_overrides(_build_settings())


# ── Backward-compatible flat exports ──────────────────────────────────────
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
DEEPSEEK_API_KEY: str = settings.intelligence.deepseek_api_key
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
