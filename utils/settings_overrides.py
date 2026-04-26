"""
Settings override system — runtime persistence via bot_settings_overrides table.
Architecture: Next.js → bot_commands (command queue) → TradingBot reads and applies.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

# Global in-memory cache + lock
_OVERRIDES: dict[str, str] = {}
_LOCK = threading.RLock()

# ── Dot-notation key map ────────────────────────────────────────────────────────
# Maps "sub_model.field" → (sub_model_name, attribute_name)
# Used by apply_overrides() to call setattr(settings.<sub_model>, <attr>, <value>)

_KEY_MAP: dict[str, tuple[str, str]] = {
    # broker
    "broker.account":               ("broker", "account"),
    "broker.password":              ("broker", "password"),
    "broker.server":                ("broker", "server"),
    "broker.platform":              ("broker", "platform"),
    # risk
    "risk.max_risk_per_trade":      ("risk", "max_risk_per_trade"),
    "risk.max_open_trades":         ("risk", "max_open_trades"),
    "risk.max_daily_loss":          ("risk", "max_daily_loss"),
    "risk.max_monthly_loss":        ("risk", "max_monthly_loss"),
    "risk.max_spread_pips":         ("risk", "max_spread_pips"),
    "risk.max_spread_pips_commodity":("risk", "max_spread_pips_commodity"),
    "risk.max_spread_pips_exotic":  ("risk", "max_spread_pips_exotic"),
    "risk.max_spread_pct_crypto":   ("risk", "max_spread_pct_crypto"),
    "risk.max_spread_points_index": ("risk", "max_spread_points_index"),
    "risk.drawdown_cooldown_hours": ("risk", "drawdown_cooldown_hours"),
    "risk.min_lot_size":            ("risk", "min_lot_size"),
    "risk.max_lot_size":            ("risk", "max_lot_size"),
    "risk.fixed_lot_size":          ("risk", "fixed_lot_size"),
    "risk.position_size_mode":      ("risk", "position_size_mode"),
    "risk.position_size_fixed_lot": ("risk", "position_size_fixed_lot"),
    "risk.position_size_fixed_risk_amount":("risk","position_size_fixed_risk_amount"),
    "risk.kelly_min_trades":        ("risk", "kelly_min_trades"),
    "risk.kelly_lookback_days":     ("risk", "kelly_lookback_days"),
    "risk.kelly_half":              ("risk", "kelly_half"),
    "risk.risk_validation_profile": ("risk", "risk_validation_profile"),
    "risk.risk_agile_high_conf_threshold":("risk","risk_agile_high_conf_threshold"),
    "risk.risk_agile_spread_multiplier":("risk","risk_agile_spread_multiplier"),
    # guard
    "guard.enabled":                ("guard", "enabled"),
    "guard.cooldown_seconds":       ("guard", "cooldown_seconds"),
    "guard.max_daily_loss_pct":     ("guard", "max_daily_loss_pct"),
    "guard.max_vix":                ("guard", "max_vix"),
    "guard.feed_staleness_seconds": ("guard", "feed_staleness_seconds"),
    # execution
    "execution.tp1_close_percent": ("execution", "tp1_close_percent"),
    "execution.tp2_close_percent": ("execution", "tp2_close_percent"),
    "execution.tp3_close_percent": ("execution", "tp3_close_percent"),
    "execution.tp4_close_percent": ("execution", "tp4_close_percent"),
    "execution.trailing_stop_distance_pips":("execution","trailing_stop_distance_pips"),
    "execution.commission_per_lot": ("execution", "commission_per_lot"),
    "execution.commission_per_lot_crypto":("execution","commission_per_lot_crypto"),
    "execution.commission_per_lot_commodity":("execution","commission_per_lot_commodity"),
    "execution.commission_per_lot_exotic":("execution","commission_per_lot_exotic"),
    "execution.breakeven_spread_offset":("execution","breakeven_spread_offset"),
    "execution.limit_entry_max_distance_atr":("execution","limit_entry_max_distance_atr"),
    "execution.limit_entry_max_distance_atr_crypto":("execution","limit_entry_max_distance_atr_crypto"),
    # sniper
    "sniper.enabled":               ("sniper", "enabled"),
    "sniper.conf_threshold":       ("sniper", "conf_threshold"),
    "sniper.timeout_minutes":      ("sniper", "timeout_minutes"),
    "sniper.max_entry_atr_distance":("sniper","max_entry_atr_distance"),
    "sniper.fib_min_depth":        ("sniper", "fib_min_depth"),
    "sniper.fib_max_depth":        ("sniper", "fib_max_depth"),
    # deferred
    "deferred.enabled":             ("deferred", "enabled"),
    "deferred.max_age_seconds":     ("deferred", "max_age_seconds"),
    "deferred.max_atr_distance":   ("deferred", "max_atr_distance"),
    "deferred.min_conf":           ("deferred", "min_conf"),
    "deferred.ttl_seconds":         ("deferred", "ttl_seconds"),
    # fastlane
    "fastlane.enabled":            ("fastlane", "enabled"),
    "fastlane.max_signals":         ("fastlane", "max_signals"),
    "fastlane.close_on_full_reject":("fastlane","close_on_full_reject"),
    # instant_entry
    "instant_entry.enabled":       ("instant_entry", "enabled"),
    "instant_entry.min_confidence":("instant_entry","min_confidence"),
    # exposure
    "exposure.enabled":            ("exposure", "enabled"),
    "exposure.reduce_threshold":   ("exposure", "reduce_threshold"),
    "exposure.cash_threshold":     ("exposure", "cash_threshold"),
    "exposure.win_rate_lookback":  ("exposure", "win_rate_lookback"),
    # neural
    "neural.min_candles":          ("neural", "min_candles"),
    "neural.seq_len":              ("neural", "seq_len"),
    "neural.hidden_size":          ("neural", "hidden_size"),
    "neural.num_layers":          ("neural", "num_layers"),
    "neural.train_epochs":         ("neural", "train_epochs"),
    "neural.retrain_every":        ("neural", "retrain_every"),
    "neural.min_confidence":       ("neural", "min_confidence"),
    "neural.lgbm_ensemble_enabled":("neural","lgbm_ensemble_enabled"),
    "neural.kalman_enabled":       ("neural","kalman_enabled"),
    # garch
    "garch.enabled":               ("garch", "enabled"),
    "garch.high_vol_threshold":    ("garch", "high_vol_threshold"),
    # ict
    "ict.min_confidence":          ("ict", "min_confidence"),
    "ict.h4_candle_count":         ("ict", "h4_candle_count"),
    "ict.d1_candle_count":        ("ict", "d1_candle_count"),
    "ict.m30_candle_count":       ("ict", "m30_candle_count"),
    "ict.m15_candle_count":       ("ict", "m15_candle_count"),
    "ict.m5_candle_count":        ("ict", "m5_candle_count"),
    "ict.mtf_alignment_boost":     ("ict", "mtf_alignment_boost"),
    "ict.mtf_d1_veto":            ("ict", "mtf_d1_veto"),
    "ict.regime_adx_trending":     ("ict", "regime_adx_trending"),
    "ict.regime_adx_ranging":      ("ict", "regime_adx_ranging"),
    "ict.regime_confidence_penalty":("ict","regime_confidence_penalty"),
    "ict.tp_trending_tp1_mult":    ("ict", "tp_trending_tp1_mult"),
    "ict.tp_trending_tp2_mult":    ("ict", "tp_trending_tp2_mult"),
    "ict.tp_trending_tp3_mult":    ("ict", "tp_trending_tp3_mult"),
    "ict.tp_trending_tp4_mult":    ("ict", "tp_trending_tp4_mult"),
    "ict.tp_ranging_tp1_mult":     ("ict", "tp_ranging_tp1_mult"),
    "ict.tp_ranging_tp2_mult":     ("ict", "tp_ranging_tp2_mult"),
    "ict.tp_ranging_tp3_mult":     ("ict", "tp_ranging_tp3_mult"),
    "ict.max_hours_in_trade":      ("ict", "max_hours_in_trade"),
    "ict.min_ict_score_crypto":    ("ict", "min_ict_score_crypto"),
    # orchestration
    "orchestration.trading_enabled":    ("orchestration","trading_enabled"),
    "orchestration.scan_interval_sec":   ("orchestration","scan_interval_sec"),
    "orchestration.scan_start":          ("orchestration","scan_start"),
    "orchestration.scan_end":            ("orchestration","scan_end"),
    "orchestration.debate_enabled":      ("orchestration","debate_enabled"),
    "orchestration.exposure_enabled":    ("orchestration","exposure_enabled"),
    "orchestration.auto_train_lgbm":     ("orchestration","auto_train_lgbm"),
    "orchestration.auto_train_frequency":("orchestration","auto_train_frequency"),
    # opportunity
    "opportunity.min_opportunity_score": ("opportunity","min_opportunity_score"),
    "opportunity.max_per_symbol":        ("opportunity","max_per_symbol"),
    "opportunity.scan_timeout_sec":      ("opportunity","scan_timeout_sec"),
    # protection
    "protection.max_adverse_execution":  ("protection","max_adverse_execution"),
    "protection.max_slippage_pct":      ("protection","max_slippage_pct"),
    "protection.cancel_after_sec":       ("protection","cancel_after_sec"),
    "protection.retry_attempts":         ("protection","retry_attempts"),
    "protection.retry_delay_ms":         ("protection","retry_delay_ms"),
    # time_phase
    "time_phase.enabled":           ("time_phase", "enabled"),
    "time_phase.check_interval":    ("time_phase", "check_interval"),
    "time_phase.close_before_news":("time_phase","close_before_news"),
    # telegram
    "telegram.bot_token":           ("telegram", "bot_token"),
    "telegram.allowed_users":       ("telegram", "allowed_users"),
    "telegram.admin_user_id":       ("telegram", "admin_user_id"),
    "telegram.trading_enabled":     ("telegram", "trading_enabled"),
    "telegram.alerts_enabled":      ("telegram", "alerts_enabled"),
    "telegram.summary_enabled":     ("telegram", "summary_enabled"),
    "telegram.pnl_enabled":         ("telegram", "pnl_enabled"),
    # intelligence
    "intelligence.enabled":               ("intelligence","enabled"),
    "intelligence.sweep_interval_min":     ("intelligence","sweep_interval_min"),
    "intelligence.max_news_lookback_h":    ("intelligence","max_news_lookback_h"),
    "intelligence.daily_loss_cap_pct":     ("intelligence","daily_loss_cap_pct"),
    "intelligence.equity_cap_pct":          ("intelligence","equity_cap_pct"),
    "intelligence.vix_threshold":           ("intelligence","vix_threshold"),
    "intelligence.use_fred":               ("intelligence","use_fred"),
    "intelligence.use_yfinance":           ("intelligence","use_yfinance"),
    "intelligence.use_eia":                ("intelligence","use_eia"),
    "intelligence.use_gdelt":              ("intelligence","use_gdelt"),
    "intelligence.use_crucix":             ("intelligence","use_crucix"),
    # learning
    "learning.enabled":              ("learning", "enabled"),
    "learning.learning_interval_min":("learning","learning_interval_min"),
    "learning.min_trades_for_update":("learning","min_trades_for_update"),
    "learning.confidence_lr":        ("learning", "confidence_lr"),
    "learning.decay_rate":           ("learning", "decay_rate"),
    # hku
    "hku.enabled":                  ("hku", "enabled"),
    "hku.api_url":                  ("hku", "api_url"),
    "hku.api_key":                  ("hku", "api_key"),
    "hku.agent_id":                 ("hku", "agent_id"),
    "hku.signal_discount":          ("hku", "signal_discount"),
    "hku.rate_limit_per_min":       ("hku", "rate_limit_per_min"),
    "hku.circuit_breaker_threshold":("hku","circuit_breaker_threshold"),
}


# ── Low-level DB operations ──────────────────────────────────────────────────────

def load_overrides(db) -> dict[str, str]:
    """
    Load all overrides from bot_settings_overrides into the in-memory cache.
    Called once at bot startup after Database() is initialized.
    """
    with _LOCK:
        conn = db._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT key, value FROM bot_settings_overrides")
                    rows = cur.fetchall()
                    _OVERRIDES.clear()
                    for row in rows:
                        _OVERRIDES[row[0]] = row[1]
                    logging.info("Loaded %d settings overrides from DB", len(_OVERRIDES))
                    return dict(_OVERRIDES)
        finally:
            db._put_conn(conn)


def get_overrides() -> dict[str, str]:
    """Return a copy of the current in-memory overrides."""
    with _LOCK:
        return dict(_OVERRIDES)


def set_override(db, key: str, value: str) -> None:
    """
    Upsert a single override into bot_settings_overrides and update the cache.
    Called when the bot processes a SET_OVERRIDE command from Next.js.
    """
    with _LOCK:
        conn = db._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO bot_settings_overrides (key, value, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                        """,
                        (key, value),
                    )
                _OVERRIDES[key] = value
                logging.info("Override set: %s = %s", key, value)
        finally:
            db._put_conn(conn)


def clear_override(db, key: str) -> None:
    """Delete an override and remove from cache."""
    with _LOCK:
        conn = db._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM bot_settings_overrides WHERE key = %s", (key,)
                    )
                _OVERRIDES.pop(key, None)
                logging.info("Override cleared: %s", key)
        finally:
            db._put_conn(conn)


# ── Apply to live settings object ───────────────────────────────────────────────

def _get_field_info(model_cls, attr_name: str) -> type:
    """Get the Python type annotation for a Pydantic model field."""
    field_info = model_cls.model_fields.get(attr_name)
    if field_info is None:
        return str
    return field_info.annotation


def apply_overrides(db, settings) -> None:
    """
    Load overrides from DB and apply them to the live settings object.
    This is called at bot startup AFTER Database() is initialized,
    and whenever a SET_OVERRIDE command is processed.
    """
    conn = db._get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM bot_settings_overrides")
                rows = cur.fetchall()
        applied = 0
        for row in rows:
            key, value = row[0], row[1]
            if key not in _KEY_MAP:
                logging.warning("Override key '%s' not in _KEY_MAP — skipping", key)
                continue
            sub_model_name, attr_name = _KEY_MAP[key]
            sub_model = getattr(settings, sub_model_name, None)
            if sub_model is None:
                logging.warning("Settings has no sub-model '%s' — skipping", sub_model_name)
                continue
            field_type = _get_field_info(sub_model.__class__, attr_name)
            try:
                coerced = _coerce(value, field_type)
                setattr(sub_model, attr_name, coerced)
                applied += 1
            except Exception as exc:
                logging.error(
                    "Failed to apply override %s = %s (%s): %s",
                    key, value, field_type.__name__ if hasattr(field_type, "__name__") else str(field_type), exc
                )
        logging.info("Applied %d settings overrides", applied)
    finally:
        db._put_conn(conn)


def _coerce(value: str, field_type: type) -> Any:
    """Cast a DB string value to its field's Python type."""
    # Unwrap Optional[T] → T
    origin = getattr(field_type, "__origin__", None)
    args = getattr(field_type, "__args__", ())
    if origin is type(None):
        field_type = type(None)
    elif origin is not None and len(args) == 2 and args[1] is type(None):
        field_type = args[0]

    if field_type is bool:
        return value.lower() in ("true", "1", "yes", "on")
    if field_type is int:
        return int(value)
    if field_type is float:
        return float(value)
    if field_type is str:
        return str(value)
    # fallback: try int then float then str
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return str(value)