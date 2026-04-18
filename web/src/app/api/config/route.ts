import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

interface ConfigGroup {
  label: string;
  items: { key: string; value: string; description?: string }[];
}

export async function GET() {
  const env = process.env;

  const groups: ConfigGroup[] = [
    {
      label: "Risk",
      items: [
        { key: "MAX_RISK_PER_TRADE",    value: env.MAX_RISK_PER_TRADE    ?? "0.02" },
        { key: "MAX_DAILY_LOSS",        value: env.MAX_DAILY_LOSS        ?? "0.05" },
        { key: "MAX_MONTHLY_LOSS",      value: env.MAX_MONTHLY_LOSS      ?? "0.10" },
        { key: "MAX_OPEN_TRADES",       value: env.MAX_OPEN_TRADES       ?? "12" },
        { key: "MAX_LOT_SIZE",          value: env.MAX_LOT_SIZE           ?? "50" },
        { key: "POSITION_SIZE_MODE",     value: env.POSITION_SIZE_MODE    ?? "equity_pct" },
        { key: "KELLY_HALF",            value: env.KELLY_HALF             ?? "true" },
        { key: "KELLY_MIN_TRADES",       value: env.KELLY_MIN_TRADES      ?? "30" },
        { key: "KELLY_LOOKBACK_DAYS",   value: env.KELLY_LOOKBACK_DAYS   ?? "90" },
      ],
    },
    {
      label: "Execution",
      items: [
        { key: "TP1_CLOSE_PCT",         value: env.TP1_CLOSE_PCT         ?? "0.40" },
        { key: "TP2_CLOSE_PCT",         value: env.TP2_CLOSE_PCT         ?? "0.30" },
        { key: "TP3_CLOSE_PCT",          value: env.TP3_CLOSE_PCT          ?? "0.20" },
        { key: "TP4_CLOSE_PCT",          value: env.TP4_CLOSE_PCT          ?? "0.10" },
        { key: "BREAKEVEN_TRIGGER_PCT",  value: env.BREAKEVEN_TRIGGER_PCT  ?? "0.50" },
        { key: "PARTIAL_CLOSE_ENABLED",  value: env.PARTIAL_CLOSE_ENABLED  ?? "true" },
        { key: "MAX_SPREAD_PIPS",        value: env.MAX_SPREAD_PIPS        ?? "8.0" },
      ],
    },
    {
      label: "Orchestration",
      items: [
        { key: "SCAN_INTERVAL_SECONDS",    value: env.SCAN_INTERVAL_SECONDS    ?? "60" },
        { key: "RECONCILE_EVERY_N_LOOPS", value: env.RECONCILE_EVERY_N_LOOPS  ?? "10" },
        { key: "MT5_DB_SYNC_INTERVAL",    value: env.MT5_DB_SYNC_INTERVAL    ?? "60" },
        { key: "LOOP_SLEEP_SECONDS",      value: env.LOOP_SLEEP_SECONDS      ?? "5" },
      ],
    },
    {
      label: "Sniper / Fast Lane",
      items: [
        { key: "SNIPER_ENABLED",    value: env.SNIPER_ENABLED    ?? "false" },
        { key: "FASTLANE_ENABLED",  value: env.FASTLANE_ENABLED  ?? "false" },
        { key: "INSTANT_ENTRY_ENABLED", value: env.INSTANT_ENTRY_ENABLED ?? "false" },
      ],
    },
    {
      label: "ICT",
      items: [
        { key: "ICT_ENABLED",           value: env.ICT_ENABLED           ?? "true" },
        { key: "SWEEP_THRESHOLD_PCT",   value: env.SWEEP_THRESHOLD_PCT   ?? "0.60" },
        { key: "OB_CONFIRMANCE_PCT",    value: env.OB_CONFIRMANCE_PCT    ?? "0.70" },
        { key: "FVG_CONFIRMANCE_PCT",   value: env.FVG_CONFIRMANCE_PCT   ?? "0.70" },
      ],
    },
    {
      label: "Neural / ML",
      items: [
        { key: "LGBM_ENSEMBLE_ENABLED",  value: env.LGBM_ENSEMBLE_ENABLED  ?? "false" },
        { key: "GARCH_ENABLED",          value: env.GARCH_ENABLED          ?? "false" },
        { key: "LSTM_LOOKBACK_BARS",     value: env.LSTM_LOOKBACK_BARS     ?? "100" },
        { key: "WFO_ENABLED",             value: env.WFO_ENABLED             ?? "true" },
        { key: "WFO_PERIOD_DAYS",         value: env.WFO_PERIOD_DAYS         ?? "30" },
      ],
    },
    {
      label: "Intelligence",
      items: [
        { key: "CRUCIX_ENABLED",    value: env.CRUCIX_ENABLED    ?? "false" },
        { key: "CRUCIX_URL",       value: env.CRUCIX_URL       ?? "https://crucix-pi.vercel.app/" },
        { key: "VIX_SOURCE",        value: env.VIX_SOURCE        ?? "yfinance" },
        { key: "NEWS_FILTER_ENABLED", value: env.NEWS_FILTER_ENABLED ?? "true" },
      ],
    },
    {
      label: "Telegram",
      items: [
        { key: "TELEGRAM_ENABLED",  value: env.TELEGRAM_ENABLED  ?? "false" },
        { key: "TELEGRAM_BOT_TOKEN", value: env.TELEGRAM_BOT_TOKEN ? "***" : "(not set)" },
        { key: "TELEGRAM_CHAT_ID",   value: env.TELEGRAM_CHAT_ID  ?? "(not set)" },
      ],
    },
  ];

  return NextResponse.json({ groups });
}
