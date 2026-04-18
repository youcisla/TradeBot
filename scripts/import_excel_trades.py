"""scripts/import_excel_trades.py — Bulk-import trades from the PU Prime MT5
Excel export (ReportHistory-700074018.xlsx) into the trades table.

Upsert by broker_ticket — re-running is safe (existing trades are updated, not duplicated).

Each row in the Excel Positions section has these fields:
  Col 0  → open_time   (str "YYYY.MM.DD HH:MM:SS")
  Col 1  → broker_ticket (int, the "Position" number)
  Col 2  → symbol      (str e.g. "XRPUSD")
  Col 3  → direction   ("buy" / "sell")
  Col 4  → volume     (str "0.01")
  Col 5  → entry_price (float)
  Col 6  → stop_loss   (float or None)
  Col 7  → take_profit (float or None)
  Col 9  → close_price (float)
  Col 10 → commission (float)
  Col 11 → swap       (float)
  Col 12 → pnl        (float)

Missing bot-side fields (filled with defaults):
  strategy='report', expected_edge_pct=0, snap_*=False,
  snap_market_condition='', snap_session='', snap_day_of_week=''

Usage:
  python scripts/import_excel_trades.py
  python scripts/import_excel_trades.py --file "path/to/ReportHistory-700074018.xlsx"
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import openpyxl
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import settings as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("import_excel_trades")


# ── date parsing ──────────────────────────────────────────────────────────────

def _parse_mt5_date(s) -> datetime | None:
    if s is None:
        return None
    if isinstance(s, datetime):
        return s.replace(tzinfo=UTC) if s.tzinfo is None else s.astimezone(UTC)
    try:
        dt = datetime.strptime(str(s).strip(), "%Y.%m.%d %H:%M:%S")
        return dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


# ── Excel row → trade dict ────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    """Return float or None — used to distinguish Positions (float price) from Orders ('market')."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None

def _parse_position_row(row) -> dict | None:
    """Convert an Excel Position row to a trades-INSERT-ready dict.

    Returns None if the row is not a valid trade (Orders section, balance rows, etc.).
    """
    col_type = str(row[3]).lower() if row[3] else ""
    if col_type not in ("buy", "sell"):
        return None

    # col 5 must be a real float — Orders rows have 'market' here
    entry_price = _safe_float(row[5])
    if entry_price is None:
        return None

    broker_ticket  = int(row[1]) if row[1] else 0
    symbol         = str(row[2]).strip() if row[2] else ""
    volume_raw     = row[4]
    stop_loss      = _safe_float(row[6]) or 0.0
    take_profit    = _safe_float(row[7]) or 0.0
    close_price    = _safe_float(row[9]) or 0.0
    commission     = _safe_float(row[10]) or 0.0
    swap           = _safe_float(row[11]) or 0.0
    pnl            = _safe_float(row[12]) or 0.0

    if not symbol or not broker_ticket:
        return None

    open_time = _parse_mt5_date(row[0])
    if open_time is None:
        return None

    close_time = _parse_mt5_date(row[8])

    # Handle partial closes: "0.01 / 0.01" → use first part
    if isinstance(volume_raw, str) and "/" in volume_raw:
        volume = _safe_float(volume_raw.split("/")[0].strip()) or 0.01
    else:
        volume = _safe_float(volume_raw) or 0.01

    return dict(
        id=f"rpt-{broker_ticket}",
        symbol=symbol,
        strategy="report",
        direction=col_type.upper(),
        entry_price=entry_price,
        lot_size=volume,
        stop_loss=stop_loss,
        take_profit_1=take_profit,
        take_profit_2=0.0,
        take_profit_3=0.0,
        take_profit_4=0.0,
        tp1_lots=volume,
        tp2_lots=0.0,
        tp3_lots=0.0,
        tp4_lots=0.0,
        tp1_hit=False,
        tp2_hit=False,
        tp3_hit=False,
        tp4_hit=False,
        structural_be=0.0,
        status="CLOSED",
        open_time=open_time,
        close_time=close_time,
        pnl=pnl,
        current_price=close_price or entry_price,
        commission=commission,
        swap=swap,
        expected_edge_pct=0.0,
        expected_pnl=0.0,
        close_reason="manual",
        broker_ticket=broker_ticket,
        spread_at_entry=0.0,
        snap_rsi_aligned=False,
        snap_trend_aligned=False,
        snap_volume_sufficient=False,
        snap_near_news_event=False,
        snap_market_condition="",
        snap_session="",
        snap_day_of_week="",
    )


# ── DB upsert ─────────────────────────────────────────────────────────────

def _upsert_trade(cur, t: dict) -> None:
    cur.execute(
        """
        INSERT INTO trades (
            id, symbol, strategy, direction, entry_price, lot_size,
            stop_loss, take_profit_1, take_profit_2, take_profit_3,
            take_profit_4, tp1_lots, tp2_lots, tp3_lots, tp4_lots,
            tp1_hit, tp2_hit, tp3_hit, tp4_hit, structural_be, status,
            open_time, close_time, pnl, current_price, commission, swap,
            expected_edge_pct, expected_pnl,
            close_reason, broker_ticket, spread_at_entry,
            snap_rsi_aligned, snap_trend_aligned,
            snap_volume_sufficient, snap_near_news_event,
            snap_market_condition, snap_session, snap_day_of_week
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (id) DO UPDATE SET
            symbol          = EXCLUDED.symbol,
            direction       = EXCLUDED.direction,
            entry_price    = EXCLUDED.entry_price,
            lot_size        = EXCLUDED.lot_size,
            stop_loss       = EXCLUDED.stop_loss,
            take_profit_1   = EXCLUDED.take_profit_1,
            take_profit_2   = EXCLUDED.take_profit_2,
            take_profit_3   = EXCLUDED.take_profit_3,
            take_profit_4   = EXCLUDED.take_profit_4,
            tp1_lots        = EXCLUDED.tp1_lots,
            tp2_lots        = EXCLUDED.tp2_lots,
            tp3_lots        = EXCLUDED.tp3_lots,
            tp4_lots        = EXCLUDED.tp4_lots,
            tp1_hit         = EXCLUDED.tp1_hit,
            tp2_hit         = EXCLUDED.tp2_hit,
            tp3_hit         = EXCLUDED.tp3_hit,
            tp4_hit         = EXCLUDED.tp4_hit,
            structural_be   = EXCLUDED.structural_be,
            status          = EXCLUDED.status,
            open_time       = EXCLUDED.open_time,
            close_time      = EXCLUDED.close_time,
            pnl             = EXCLUDED.pnl,
            current_price   = EXCLUDED.current_price,
            commission      = EXCLUDED.commission,
            swap            = EXCLUDED.swap,
            expected_edge_pct = EXCLUDED.expected_edge_pct,
            expected_pnl     = EXCLUDED.expected_pnl,
            close_reason    = EXCLUDED.close_reason,
            broker_ticket  = EXCLUDED.broker_ticket,
            spread_at_entry = EXCLUDED.spread_at_entry,
            snap_rsi_aligned        = EXCLUDED.snap_rsi_aligned,
            snap_trend_aligned      = EXCLUDED.snap_trend_aligned,
            snap_volume_sufficient = EXCLUDED.snap_volume_sufficient,
            snap_near_news_event    = EXCLUDED.snap_near_news_event,
            snap_market_condition  = EXCLUDED.snap_market_condition,
            snap_session           = EXCLUDED.snap_session,
            snap_day_of_week       = EXCLUDED.snap_day_of_week
        """,
        (
            t["id"], t["symbol"], t["strategy"], t["direction"],
            t["entry_price"], t["lot_size"],
            t["stop_loss"], t["take_profit_1"], t["take_profit_2"], t["take_profit_3"],
            t["take_profit_4"],
            t["tp1_lots"], t["tp2_lots"], t["tp3_lots"], t["tp4_lots"],
            t["tp1_hit"], t["tp2_hit"], t["tp3_hit"], t["tp4_hit"], t["structural_be"],
            t["status"],
            t["open_time"], t["close_time"],
            t["pnl"], t["current_price"], t["commission"], t["swap"],
            t["expected_edge_pct"], t["expected_pnl"],
            t["close_reason"],
            t["broker_ticket"], t["spread_at_entry"],
            t["snap_rsi_aligned"], t["snap_trend_aligned"],
            t["snap_volume_sufficient"], t["snap_near_news_event"],
            t["snap_market_condition"], t["snap_session"], t["snap_day_of_week"],
        ),
    )


# ── main ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Import MT5 Excel trades into DB.")
    parser.add_argument(
        "--file", type=Path,
        default=Path("C:/Users/Youcef/Downloads/ReportHistory-700074018.xlsx"),
    )
    args = parser.parse_args()

    path: Path = args.file
    if not path.exists():
        logger.error("File not found: %s", path)
        return 1

    logger.info("Reading %s …", path)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(values_only=True))

    trade_rows = []
    for row in rows[7:]:
        t = _parse_position_row(row)
        if t is not None:
            trade_rows.append(t)

    logger.info("Parsed %d trade rows", len(trade_rows))

    conn = psycopg2.connect(cfg.DATABASE_URL)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT broker_ticket FROM trades "
            "WHERE id LIKE 'rpt-%%' AND broker_ticket IS NOT NULL"
        )
        existing = set(r[0] for r in cur.fetchall())
        cur.close()
        logger.info("Already in DB: %d trades", len(existing))

        new_rows = [t for t in trade_rows if t["broker_ticket"] not in existing]
        skipped  = len(trade_rows) - len(new_rows)
        logger.info("New trades: %d  (skipped %d already imported)", len(new_rows), skipped)

        if not new_rows:
            logger.info("Nothing to import.")
            return 0

        cur = conn.cursor()
        for t in new_rows:
            _upsert_trade(cur, t)
        conn.commit()
        cur.close()
        logger.info("Upserted %d trades.", len(new_rows))

        # Sanity check
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM trades "
            "WHERE status='CLOSED' AND pnl IS NOT NULL AND pnl != 0"
        )
        closed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM trades")
        total = cur.fetchone()[0]
        cur.close()
        logger.info("DB now: %d closed trades (non-zero pnl), %d total", closed, total)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
