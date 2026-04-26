/**
 * Settings registry — field definitions for the runtime settings editor.
 * Each field: key (dot-notation), label, type, validation bounds, tab group.
 * Override badge (green dot) shown if field has an active DB override.
 */

export type FieldType = "bool" | "float" | "int" | "str";

export interface SettingsField {
  key: string;
  label: string;
  type: FieldType;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  hint?: string;
}

export interface SettingsGroup {
  id: string;
  label: string;
  fields: SettingsField[];
}

const RISK_FIELDS: SettingsField[] = [
  { key: "risk.max_risk_per_trade",      label: "Max Risk per Trade",   type: "float", min: 0.0001, max: 0.50,  step: 0.001,  hint: "Fraction of equity risked per trade" },
  { key: "risk.max_daily_loss",         label: "Max Daily Loss %",      type: "float", min: 0.001,  max: 0.50,  step: 0.001  },
  { key: "risk.max_monthly_loss",       label: "Max Monthly Loss %",   type: "float", min: 0.001,  max: 0.99,  step: 0.001  },
  { key: "risk.max_open_trades",        label: "Max Open Trades",      type: "int",   min: 1,      max: 50,    step: 1      },
  { key: "risk.max_spread_pips",        label: "Max Spread (pips)",     type: "float", min: 0,      max: 50,    step: 0.1    },
  { key: "risk.max_lot_size",           label: "Max Lot Size",          type: "float", min: 0.01,   max: 50,    step: 0.01   },
  { key: "risk.min_lot_size",           label: "Min Lot Size",          type: "float", min: 0.01,   max: 50,    step: 0.01   },
  { key: "risk.fixed_lot_size",         label: "Fixed Lot Size",        type: "float", min: 0,      max: 50,    step: 0.01   },
  { key: "risk.position_size_mode",      label: "Position Sizing Mode", type: "str",   options: ["equity_pct","fixed_lot","fixed_risk_amount","kelly"] },
  { key: "risk.kelly_half",             label: "Kelly Half-Kelly",      type: "bool"                                        },
  { key: "risk.kelly_min_trades",        label: "Kelly Min Trades",     type: "int",   min: 2,      max: 200,   step: 1      },
  { key: "risk.kelly_lookback_days",     label: "Kelly Lookback (days)",type: "int",   min: 7,      max: 365,   step: 1      },
  { key: "risk.drawdown_cooldown_hours",label: "Drawdown Cooldown (h)", type: "int",   min: 0,      max: 168,   step: 1      },
];

const EXECUTION_FIELDS: SettingsField[] = [
  { key: "execution.tp1_close_percent", label: "TP1 Close %",          type: "float", min: 0,      max: 1.0,    step: 0.01  },
  { key: "execution.tp2_close_percent", label: "TP2 Close %",          type: "float", min: 0,      max: 1.0,    step: 0.01  },
  { key: "execution.tp3_close_percent", label: "TP3 Close %",          type: "float", min: 0,      max: 1.0,    step: 0.01  },
  { key: "execution.tp4_close_percent", label: "TP4 Close %",          type: "float", min: 0,      max: 1.0,    step: 0.01  },
  { key: "execution.trailing_stop_distance_pips", label: "Trailing Stop (pips)", type: "float", min: 0, max: 200, step: 0.5 },
  { key: "execution.commission_per_lot", label: "Commission/Lot ($)",   type: "float", min: 0,      max: 100,    step: 0.5   },
  { key: "execution.breakeven_spread_offset", label: "Breakeven Spread Offset", type: "bool" },
  { key: "execution.limit_entry_max_distance_atr", label: "Limit ATR Distance", type: "float", min: 0, max: 5, step: 0.05 },
  { key: "execution.cancel_after_sec",  label: "Cancel After (sec)",    type: "int",   min: 5,      max: 300,    step: 1    },
  { key: "execution.retry_attempts",    label: "Retry Attempts",      type: "int",   min: 0,      max: 10,     step: 1    },
  { key: "execution.retry_delay_ms",     label: "Retry Delay (ms)",   type: "int",   min: 100,    max: 5000,   step: 100  },
];

const ORCHESTRATION_FIELDS: SettingsField[] = [
  { key: "orchestration.trading_enabled",       label: "Trading Enabled",          type: "bool" },
  { key: "orchestration.scan_interval_sec",      label: "Scan Interval (sec)",      type: "int",   min: 5,   max: 300,  step: 5  },
  { key: "orchestration.scan_start",             label: "Scan Start (HH:MM)",       type: "str"                                  },
  { key: "orchestration.scan_end",               label: "Scan End (HH:MM)",         type: "str"                                  },
  { key: "orchestration.debate_enabled",         label: "LLM Debate Gate",          type: "bool"                                 },
  { key: "orchestration.exposure_enabled",        label: "Exposure Guard",          type: "bool"                                 },
  { key: "orchestration.auto_train_lgbm",        label: "Auto-train LGBM",          type: "bool"                                 },
  { key: "orchestration.auto_train_frequency",   label: "Auto-train Frequency",    type: "int",   min: 10, max: 10000, step: 10 },
];

const ICT_FIELDS: SettingsField[] = [
  { key: "ict.min_confidence",          label: "Min ICT Score %",         type: "int",   min: 0,   max: 100, step: 1   },
  { key: "ict.h4_candle_count",          label: "H4 Candle Count",        type: "int",   min: 10,  max: 500, step: 10  },
  { key: "ict.d1_candle_count",          label: "D1 Candle Count",        type: "int",   min: 5,   max: 100, step: 5   },
  { key: "ict.m30_candle_count",          label: "M30 Candle Count",       type: "int",   min: 20,  max: 500, step: 10  },
  { key: "ict.m15_candle_count",          label: "M15 Candle Count",       type: "int",   min: 20,  max: 1000,step: 10  },
  { key: "ict.m5_candle_count",          label: "M5 Candle Count",        type: "int",   min: 20,  max: 500, step: 10  },
  { key: "ict.mtf_alignment_boost",       label: "MTF Alignment Boost",    type: "float", min: 0,   max: 0.2,  step: 0.01 },
  { key: "ict.mtf_d1_veto",               label: "D1 Veto",                type: "bool"                                 },
  { key: "ict.regime_adx_trending",      label: "ADX Trending Threshold", type: "float", min: 0,   max: 100,  step: 0.5 },
  { key: "ict.regime_adx_ranging",        label: "ADX Ranging Threshold", type: "float", min: 0,   max: 100,  step: 0.5 },
  { key: "ict.max_hours_in_trade",        label: "Max Hours in Trade",    type: "int",   min: 0,   max: 168,  step: 1   },
  { key: "ict.tp_trending_tp1_mult",       label: "TP1 Mult (Trending)",    type: "float", min: 0,   max: 10,   step: 0.1  },
  { key: "ict.tp_trending_tp3_mult",      label: "TP3 Mult (Trending)",    type: "float", min: 0,   max: 10,   step: 0.1  },
  { key: "ict.tp_ranging_tp1_mult",       label: "TP1 Mult (Ranging)",    type: "float", min: 0,   max: 10,   step: 0.1  },
];

const ML_FIELDS: SettingsField[] = [
  { key: "neural.min_confidence",           label: "Min Confidence",          type: "float", min: 0, max: 1.0, step: 0.01 },
  { key: "neural.min_candles",              label: "Min Candles for Train",  type: "int",   min: 10, max: 1000, step: 10 },
  { key: "neural.seq_len",                  label: "Sequence Length",        type: "int",   min: 10, max: 200,  step: 5  },
  { key: "neural.hidden_size",             label: "Hidden Size",            type: "int",   min: 32, max: 512,  step: 32 },
  { key: "neural.num_layers",               label: "Num Layers",             type: "int",   min: 1,  max: 8,    step: 1  },
  { key: "neural.train_epochs",             label: "Train Epochs",           type: "int",   min: 1,  max: 500,  step: 1  },
  { key: "neural.retrain_every",           label: "Retrain Every (bars)",   type: "int",   min: 1,  max: 1000, step: 10 },
  { key: "neural.lgbm_ensemble_enabled",    label: "LGBM Ensemble",           type: "bool"                              },
  { key: "neural.kalman_enabled",            label: "Kalman Filter",          type: "bool"                              },
  { key: "garch.enabled",                  label: "GARCH Regime",           type: "bool"                              },
  { key: "garch.high_vol_threshold",       label: "GARCH Vol Threshold",    type: "float", min: 0, max: 10,  step: 0.1 },
];

const INTELLIGENCE_FIELDS: SettingsField[] = [
  { key: "intelligence.enabled",                label: "Intelligence Sweep",     type: "bool" },
  { key: "intelligence.sweep_interval_min",      label: "Sweep Interval (min)",  type: "int",   min: 1,  max: 1440, step: 1 },
  { key: "intelligence.max_news_lookback_h",    label: "News Lookback (h)",     type: "int",   min: 1,  max: 72,    step: 1 },
  { key: "intelligence.daily_loss_cap_pct",       label: "Daily Loss Cap %",      type: "float", min: 0, max: 0.5,  step: 0.001 },
  { key: "intelligence.equity_cap_pct",           label: "Equity Cap %",         type: "float", min: 0, max: 0.5,  step: 0.001 },
  { key: "intelligence.vix_threshold",           label: "VIX Threshold",         type: "float", min: 0, max: 100, step: 0.5 },
  { key: "intelligence.use_fred",                 label: "FRED Data",             type: "bool"                              },
  { key: "intelligence.use_yfinance",            label: "yfinance",              type: "bool"                              },
  { key: "intelligence.use_eia",                  label: "EIA Data",              type: "bool"                              },
  { key: "intelligence.use_gdelt",                label: "GDELT",                 type: "bool"                              },
  { key: "intelligence.use_crucix",             label: "Crucix",                type: "bool"                              },
];

const EXPOSURE_FIELDS: SettingsField[] = [
  { key: "exposure.enabled",              label: "Exposure Guard",        type: "bool"                              },
  { key: "exposure.reduce_threshold",       label: "Reduce Threshold",    type: "float", min: 0, max: 1.0, step: 0.01 },
  { key: "exposure.cash_threshold",           label: "Cash Threshold",      type: "float", min: 0, max: 1.0, step: 0.01 },
  { key: "exposure.win_rate_lookback",       label: "Win Rate Lookback",   type: "int",   min: 1, max: 100, step: 1   },
];

const HKU_FIELDS: SettingsField[] = [
  { key: "hku.enabled",                   label: "HKU Marketplace",      type: "bool"                              },
  { key: "hku.signal_discount",           label: "Signal Discount",       type: "float", min: 0, max: 1.0, step: 0.01 },
  { key: "hku.rate_limit_per_min",        label: "Rate Limit/min",       type: "int",   min: 1, max: 60,  step: 1   },
  { key: "hku.circuit_breaker_threshold", label: "Circuit Breaker",     type: "int",   min: 1, max: 20,  step: 1   },
];

export const SETTINGS_REGISTRY: SettingsGroup[] = [
  { id: "status",       label: "Status",        fields: []                   },
  { id: "risk",          label: "Risk",           fields: RISK_FIELDS         },
  { id: "execution",     label: "Execution",     fields: EXECUTION_FIELDS   },
  { id: "orchestration", label: "Orchestration", fields: ORCHESTRATION_FIELDS},
  { id: "ict",           label: "ICT Strategy",  fields: ICT_FIELDS          },
  { id: "ml",            label: "ML / Neural",   fields: ML_FIELDS           },
  { id: "intelligence",  label: "Intelligence",  fields: INTELLIGENCE_FIELDS},
  { id: "exposure",      label: "Exposure",      fields: EXPOSURE_FIELDS    },
  { id: "hku",           label: "HKU Marketplace",fields: HKU_FIELDS        },
];

export const FIELD_MAP: Record<string, SettingsField> = Object.fromEntries(
  SETTINGS_REGISTRY.flatMap((g) => g.fields.map((f) => [f.key, f]))
);
