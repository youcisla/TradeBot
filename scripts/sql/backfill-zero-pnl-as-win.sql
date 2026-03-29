-- Backfill: treat breakeven (pnl = 0) as WIN in existing data
-- Safe to run multiple times.
--
-- What this updates:
-- 1) trade_scores.score rows where pnl = 0
--    Old base score for pnl=0 was -2 (loss branch), new base is +1 (win branch).
--    Bonus terms are unchanged, so score delta is always +3.
-- 2) performance_snapshots for day/week/month
--    Recomputes trades, wins, losses, total_pnl, avg_score, win_rate from trade_scores
--    using the same period boundaries used by the app.

BEGIN;

-- 1) Adjust historical scores for breakeven trades
-- Idempotent guard:
--   Legacy pnl=0 scores were in the loss bucket and therefore <= 0.
--   Reconciled pnl=0 scores are > 0.
UPDATE trade_scores
SET score = score + 3
WHERE pnl = 0
  AND score <= 0;

-- 2) Recompute daily snapshots: period_key format 'YYYY-MM-DD'
WITH day_stats AS (
  SELECT
    p.period_type,
    p.period_key,
    COUNT(ts.*) AS trades,
    COUNT(*) FILTER (WHERE ts.pnl >= 0) AS wins,
    COUNT(*) FILTER (WHERE ts.pnl < 0) AS losses,
    COALESCE(SUM(ts.pnl), 0) AS total_pnl,
    COALESCE(AVG(ts.score), 0) AS avg_score
  FROM performance_snapshots p
  LEFT JOIN trade_scores ts
    ON p.period_type = 'day'
   AND ts.created_at >= p.period_key::date
   AND ts.created_at <  (p.period_key::date + INTERVAL '1 day')
  WHERE p.period_type = 'day'
  GROUP BY p.period_type, p.period_key
)
UPDATE performance_snapshots p
SET
  trades = ds.trades,
  wins = ds.wins,
  losses = ds.losses,
  total_pnl = ds.total_pnl,
  avg_score = ds.avg_score,
  win_rate = CASE WHEN ds.trades > 0 THEN ROUND((ds.wins::numeric / ds.trades::numeric), 4) ELSE 0 END
FROM day_stats ds
WHERE p.period_type = ds.period_type
  AND p.period_key = ds.period_key;

-- 3) Recompute weekly snapshots: period_key format 'YYYY-Www' (ISO week)
WITH week_bounds AS (
  SELECT
    p.period_type,
    p.period_key,
    TO_DATE(p.period_key || '-1', 'IYYY-"W"IW-ID')::timestamp AS start_ts,
    (TO_DATE(p.period_key || '-1', 'IYYY-"W"IW-ID')::timestamp + INTERVAL '7 day') AS end_ts
  FROM performance_snapshots p
  WHERE p.period_type = 'week'
),
week_stats AS (
  SELECT
    wb.period_type,
    wb.period_key,
    COUNT(ts.*) AS trades,
    COUNT(*) FILTER (WHERE ts.pnl >= 0) AS wins,
    COUNT(*) FILTER (WHERE ts.pnl < 0) AS losses,
    COALESCE(SUM(ts.pnl), 0) AS total_pnl,
    COALESCE(AVG(ts.score), 0) AS avg_score
  FROM week_bounds wb
  LEFT JOIN trade_scores ts
    ON ts.created_at >= wb.start_ts
   AND ts.created_at <  wb.end_ts
  GROUP BY wb.period_type, wb.period_key
)
UPDATE performance_snapshots p
SET
  trades = ws.trades,
  wins = ws.wins,
  losses = ws.losses,
  total_pnl = ws.total_pnl,
  avg_score = ws.avg_score,
  win_rate = CASE WHEN ws.trades > 0 THEN ROUND((ws.wins::numeric / ws.trades::numeric), 4) ELSE 0 END
FROM week_stats ws
WHERE p.period_type = ws.period_type
  AND p.period_key = ws.period_key;

-- 4) Recompute monthly snapshots: period_key format 'YYYY-MM'
WITH month_bounds AS (
  SELECT
    p.period_type,
    p.period_key,
    TO_DATE(p.period_key || '-01', 'YYYY-MM-DD')::timestamp AS start_ts,
    (TO_DATE(p.period_key || '-01', 'YYYY-MM-DD')::timestamp + INTERVAL '1 month') AS end_ts
  FROM performance_snapshots p
  WHERE p.period_type = 'month'
),
month_stats AS (
  SELECT
    mb.period_type,
    mb.period_key,
    COUNT(ts.*) AS trades,
    COUNT(*) FILTER (WHERE ts.pnl >= 0) AS wins,
    COUNT(*) FILTER (WHERE ts.pnl < 0) AS losses,
    COALESCE(SUM(ts.pnl), 0) AS total_pnl,
    COALESCE(AVG(ts.score), 0) AS avg_score
  FROM month_bounds mb
  LEFT JOIN trade_scores ts
    ON ts.created_at >= mb.start_ts
   AND ts.created_at <  mb.end_ts
  GROUP BY mb.period_type, mb.period_key
)
UPDATE performance_snapshots p
SET
  trades = ms.trades,
  wins = ms.wins,
  losses = ms.losses,
  total_pnl = ms.total_pnl,
  avg_score = ms.avg_score,
  win_rate = CASE WHEN ms.trades > 0 THEN ROUND((ms.wins::numeric / ms.trades::numeric), 4) ELSE 0 END
FROM month_stats ms
WHERE p.period_type = ms.period_type
  AND p.period_key = ms.period_key;

COMMIT;

-- Optional verification checks:
-- SELECT COUNT(*) AS zero_pnl_rows, MIN(score), MAX(score)
-- FROM trade_scores
-- WHERE pnl = 0;
--
-- SELECT period_type, period_key, trades, wins, losses, win_rate
-- FROM performance_snapshots
-- ORDER BY period_type, period_key DESC
-- LIMIT 50;
