-- ╔══════════════════════════════════════════════════════════════╗
-- ║  TradingBot — Clean up mock / demo data                    ║
-- ║  Run manually in SSMS against the Supabase database.       ║
-- ║  MockConnector uses broker_ticket starting at 100,000.     ║
-- ╚══════════════════════════════════════════════════════════════╝

-- ── 1. Delete trade scores linked to mock trades ────────────
DELETE FROM trade_scores
WHERE trade_id IN (
    SELECT id FROM trades
    WHERE broker_ticket >= 100000
);

-- ── 2. Delete mock trades themselves ────────────────────────
DELETE FROM trades
WHERE broker_ticket >= 100000;

-- ── 3. Clear all agent events (optional — they repopulate) ──
-- Uncomment below if you want a fresh event feed:
-- DELETE FROM agent_events;

-- ── 4. Reset strategy confidence to default ─────────────────
-- Uncomment if you want strategies back to 0.50:
-- UPDATE strategy_confidence
-- SET confidence = 0.50,
--     total_trades = 0,
--     total_score = 0,
--     last_updated = NOW();

-- ── 5. Verify cleanup ──────────────────────────────────────
SELECT 'Remaining trades' AS check, COUNT(*) AS cnt FROM trades
UNION ALL
SELECT 'Remaining scores', COUNT(*) FROM trade_scores
UNION ALL
SELECT 'Remaining events', COUNT(*) FROM agent_events;
