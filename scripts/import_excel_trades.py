"""
import_excel_trades.py
Backfills the trades table from ReportHistory-700074018.xlsx (MT5 statement export).

NOTE: This script is for BACKFILLING historical trades ONLY. For live trading,
the bot saves all trade data (P&L, swap, TP, close reason) directly from MT5
at close time via get_closed_pnl() and get_closed_swap(). The DB is the
single source of truth for trade history.

Data sources used:
  - Positions section → primary trade data (entry/exit prices, S/L, T/P,
    volume, direction, profit, swap).  One row = one closed trade.
    Scanning is DYNAMIC — no row limit, scans until "Orders" section.
  - Deals section      → links position ticket → deal ticket for broker_ticket;
    also provides strategy name.
"""

from __future__ import annotations

import logging, sys
from datetime import datetime
from pathlib import Path

import openpyxl
from psycopg2 import pool

# ── paths ──────────────────────────────────────────────────────────────────

import os, sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

EXCEL  = Path("C:/Users/Youcef/Downloads/ReportHistory-700074018.xlsx")
DB_URL = os.getenv("DATABASE_URL", "")

# ── logging ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────────────


def parse_time(val) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in (
            "%Y.%m.%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(val.strip(), fmt)
            except ValueError:
                pass
    return None


def insert_trade(cur, row: dict) -> None:
    sql = """
    INSERT INTO trades (
        id, symbol, strategy, direction,
        entry_price, lot_size, stop_loss,
        take_profit_1, take_profit_2, take_profit_3, take_profit_4,
        tp1_lots, tp2_lots, tp3_lots, tp4_lots,
        tp1_hit, tp2_hit, tp3_hit, tp4_hit,
        status, open_time, close_time,
        pnl, commission, swap, close_reason,
        broker_ticket, spread_at_entry
    ) VALUES (
        %(id)s, %(symbol)s, %(strategy)s, %(direction)s,
        %(entry_price)s, %(lot_size)s, %(stop_loss)s,
        %(take_profit_1)s, %(take_profit_2)s, %(take_profit_3)s, %(take_profit_4)s,
        %(tp1_lots)s, %(tp2_lots)s, %(tp3_lots)s, %(tp4_lots)s,
        %(tp1_hit)s, %(tp2_hit)s, %(tp3_hit)s, %(tp4_hit)s,
        %(status)s, %(open_time)s, %(close_time)s,
        %(pnl)s, %(commission)s, %(swap)s, %(close_reason)s,
        %(broker_ticket)s, %(spread_at_entry)s
    )
    ON CONFLICT (id) DO UPDATE SET
        symbol         = EXCLUDED.symbol,
        strategy       = EXCLUDED.strategy,
        direction      = EXCLUDED.direction,
        entry_price    = EXCLUDED.entry_price,
        lot_size       = EXCLUDED.lot_size,
        stop_loss      = EXCLUDED.stop_loss,
        take_profit_1  = EXCLUDED.take_profit_1,
        take_profit_2  = EXCLUDED.take_profit_2,
        take_profit_3  = EXCLUDED.take_profit_3,
        take_profit_4  = EXCLUDED.take_profit_4,
        tp1_lots       = EXCLUDED.tp1_lots,
        tp2_lots       = EXCLUDED.tp2_lots,
        tp3_lots       = EXCLUDED.tp3_lots,
        tp4_lots       = EXCLUDED.tp4_lots,
        tp1_hit        = EXCLUDED.tp1_hit,
        tp2_hit        = EXCLUDED.tp2_hit,
        tp3_hit        = EXCLUDED.tp3_hit,
        tp4_hit        = EXCLUDED.tp4_hit,
        status         = EXCLUDED.status,
        open_time      = EXCLUDED.open_time,
        close_time     = EXCLUDED.close_time,
        pnl            = EXCLUDED.pnl,
        commission     = EXCLUDED.commission,
        swap           = EXCLUDED.swap,
        close_reason   = EXCLUDED.close_reason,
        broker_ticket  = EXCLUDED.broker_ticket,
        spread_at_entry = EXCLUDED.spread_at_entry;
    """
    cur.execute(sql, row)


def upsert_bot_status(cur, balance: float, daily_pnl: float, equity: float) -> None:
    sql = """
    INSERT INTO bot_status (id, state, equity, open_trades, daily_pnl, balance)
    VALUES (1, 'stopped', %s, 0, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        equity     = EXCLUDED.equity,
        daily_pnl  = EXCLUDED.daily_pnl,
        balance    = EXCLUDED.balance,
        open_trades = EXCLUDED.open_trades;
    """
    cur.execute(sql, (equity, daily_pnl, balance))


# ── main ──────────────────────────────────────────────────────────────────


def main() -> None:
    logger.info("Loading Excel: %s", EXCEL)
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    ws = wb.active

    # ── 1. Parse Deals section (row 179 = header) ────────────────────────────
    # Columns: Time(0) Deal(1) Symbol(2) Type(3) Direction(4)
    #          Volume(5) Price(6) Order(7) Commission Swap Profit Balance Strategy
    #          col8    col9    col10     col11     col12    col13    col14

    deals_by_pos: dict[int, dict] = {}   # position_ticket → deal row

    in_deals:  list[dict] = []   # buy/sell 'in'  deal rows
    out_deals: list[dict] = []   # buy/sell 'out' deal rows

    DEALS_HEADER_ROW = 179
    deals_header = [c.value for c in ws[DEALS_HEADER_ROW]]
    logger.info("Deals header: %s", deals_header)

    # Find Deals section start by scanning for section header
    deals_start = None
    for i, row in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1):
        if row[0] == "Deals":
            deals_start = i + 1   # data starts one row after header
            break

    if deals_start is None:
        logger.error("Could not find 'Deals' section")
        return

    logger.info("Deals section data starts at row %d", deals_start)

    for i, row in enumerate(ws.iter_rows(min_row=deals_start, values_only=True), start=deals_start):
        if not row or row[0] is None:
            continue
        if not isinstance(row[0], str) or "20" not in row[0]:
            continue

        rec = {
            "row_idx":    i,
            "time":       parse_time(row[0]),
            "deal":       int(row[1]) if row[1] else 0,
            "symbol":     str(row[2]).strip() if row[2] else "",
            "type":       str(row[3]).strip().lower() if row[3] else "",
            "direction":  str(row[4]).strip().lower() if row[4] else "",
            "volume":     float(row[5]) if row[5] else 0.0,
            "price":      float(row[6]) if row[6] else 0.0,
            "order":      int(row[7]) if row[7] else 0,   # position ticket
            "commission": float(row[8]) if row[8] else 0.0,
            "swap":       float(row[9]) if row[9] else 0.0,
            "profit":     float(row[10]) if row[10] else 0.0,
            "balance":   float(row[11]) if row[11] else 0.0,
            "strategy":  str(row[13]).strip() if row[13] else "",
        }

        if rec["direction"] == "in":
            in_deals.append(rec)
            if rec["order"]:
                deals_by_pos[rec["order"]] = rec   # entry deal → strategy name
        elif rec["direction"] == "out":
            out_deals.append(rec)

    logger.info(
        "Deals:  in_deals=%d  out_deals=%d  deals_by_pos=%d",
        len(in_deals), len(out_deals), len(deals_by_pos),
    )

    # ── 2. Parse Positions section (row 6 = 'Positions' header, row 7 = col header) ──
    # Columns: Time(0) Position(1) Symbol(2) Type(3) Volume(4) Price(5)
    #          S/L(6) T/P(7) Time(8) Price(9) Commission Swap Profit
    #          col10 col11 col12

    POS_HEADER_ROW = 7   # column header row

    positions: list[dict] = []

    pos_header = [c.value for c in ws[POS_HEADER_ROW]]
    logger.info("Positions header: %s", pos_header)

    def safe_float(v):
        """Return float or None (None means skip this row)."""
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    # Scan dynamically — stop at the first row that doesn't have a valid position entry.
    # The "Orders" section has row[0] = "Open Time" which fails date parsing.
    for i, row in enumerate(ws.iter_rows(min_row=POS_HEADER_ROW + 1, values_only=True), start=POS_HEADER_ROW + 1):
        if not row or row[0] is None:
            continue
        # Stop when we hit the Orders section (row[0] no longer a date string)
        if isinstance(row[0], str) and "20" not in row[0]:
            break

        entry_price = safe_float(row[5])
        if entry_price is None:
            continue  # Skip malformed or non-position rows

        # Handle partial closes where volume is "0.01 / 0.01" — use first part
        vol_raw = row[4]
        if isinstance(vol_raw, str) and "/" in vol_raw:
            vol_raw = vol_raw.split("/")[0].strip()
            volume = float(vol_raw)
        else:
            volume = float(vol_raw) if vol_raw else 0.0

        rec = {
            "row_idx":     i,
            "entry_time":  parse_time(row[0]),
            "pos_ticket":  int(row[1]) if row[1] else 0,
            "symbol":      str(row[2]).strip() if row[2] else "",
            "type":        str(row[3]).strip().lower() if row[3] else "",
            "volume":      volume,
            "entry_price": entry_price,
            "sl":          safe_float(row[6]) or 0.0,
            "tp":          row[7],                         # T/P value or None
            "close_time":  parse_time(row[8]),
            "close_price": safe_float(row[9]) or 0.0,
            "commission":  safe_float(row[10]) or 0.0,
            "swap":        safe_float(row[11]) or 0.0,
            "profit":      safe_float(row[12]) or 0.0,     # P&L in account currency
        }

        if rec["pos_ticket"]:
            positions.append(rec)

    logger.info("Positions collected: %d", len(positions))

    # ── 3. Build trades list from Positions ──────────────────────────────
    # For each position row, look up the strategy from the linked Deal row.

    trades: list[dict] = []

    for pos in positions:
        pos_ticket = pos["pos_ticket"]

        # Get strategy from the Deals section via position ticket
        strategy = "ICT"
        deal_rec = deals_by_pos.get(pos_ticket, {})
        if deal_rec:
            strategy = deal_rec.get("strategy") or "ICT"
            if not strategy or strategy == "balance":
                strategy = "ICT"

        direction = "BUY" if pos["type"] in ("buy", "buy limit", "buy stop") else "SELL"

        trade_id = f"手工-{pos_ticket}"

        trades.append(
            {
                "id":              trade_id,
                "symbol":          pos["symbol"],
                "strategy":        strategy,
                "direction":      direction,
                "entry_price":     pos["entry_price"],
                "lot_size":       pos["volume"],
                "stop_loss":       pos["sl"],
                "take_profit_1":   float(pos["tp"]) if pos["tp"] else 0.0,
                "take_profit_2":   0.0,
                "take_profit_3":   0.0,
                "take_profit_4":   0.0,
                "tp1_lots":        0.0,
                "tp2_lots":        0.0,
                "tp3_lots":        0.0,
                "tp4_lots":        0.0,
                "tp1_hit":         False,
                "tp2_hit":         False,
                "tp3_hit":         False,
                "tp4_hit":         False,
                "status":          "CLOSED",
                "open_time":       pos["entry_time"],
                "close_time":      pos["close_time"],
                "pnl":             round(pos["profit"], 2),
                "commission":     pos["commission"],
                "swap":           pos["swap"],
                "close_reason":    "",
                "broker_ticket":  pos_ticket,
                "spread_at_entry": 0.0,
            }
        )

    logger.info("Built %d trades from Positions", len(trades))

    # Sort by close_time for summary
    trades_sorted = sorted(trades, key=lambda t: t["close_time"] or datetime.min)

    # ── 4. DB write ─────────────────────────────────────────────────────

    logger.info("Connecting to DB …")
    db_pool = pool.ThreadedConnectionPool(1, 1, dsn=DB_URL)
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()

        cur.execute("DELETE FROM trades WHERE status = 'CLOSED';")
        logger.info("Cleared existing CLOSED trades")

        inserted = 0
        for t in trades_sorted:
            insert_trade(cur, t)
            inserted += 1

        conn.commit()
        logger.info("Inserted %d trades", inserted)

        # ── bot_status ──────────────────────────────────────────────────
        # Starting balance from the first balance row in Deals (initial deposit = 1000)
        # Final balance from the last deal row in the Excel (row 296 shows Balance: 215.17)
        if positions:
            # Find the opening balance row from Deals section (balance=1000, type='balance')
            opening_deal = next(
                (d for d in in_deals if d["symbol"] == "" and d["balance"] >= 999),
                None,
            )
            start_balance = opening_deal["balance"] if opening_deal else 1000.0

            # Final balance: scan the end of the Excel for "Balance:" summary row
            final_balance = 215.17   # hardcoded from last deal + summary row
            for i, row in enumerate(ws.iter_rows(min_row=deals_start, values_only=True), start=deals_start):
                if row[0] == "Balance:" and row[3]:
                    final_balance = float(row[3])
                    break

            final_equity = final_balance  # no open positions

            # Daily P&L: today's closed trades only
            today = datetime.now().date()
            today_trades = [
                t for t in trades_sorted
                if t["close_time"] and t["close_time"].date() == today
            ]
            daily_pnl = sum(t["pnl"] for t in today_trades)

            # balance = current account balance (final running balance, not deposit)
            # equity  = balance + floating P&L = final_balance (no open positions)
            upsert_bot_status(cur, final_balance, daily_pnl, final_equity)
            conn.commit()
            logger.info(
                "bot_status: balance=%.2f  equity=%.2f  daily_pnl=%.2f",
                final_balance, final_equity, daily_pnl,
            )

        # ── summary ────────────────────────────────────────────────────
        wins  = [t for t in trades_sorted if t["pnl"] > 0]
        loss  = [t for t in trades_sorted if t["pnl"] < 0]
        net   = sum(t["pnl"] for t in trades_sorted)
        logger.info(
            "SUMMARY  total=%d  wins=%d  losses=%d  net=%+.2f",
            len(trades_sorted), len(wins), len(loss), net,
        )

        symbols = sorted(set(t["symbol"] for t in trades_sorted))
        for sym in symbols:
            st = [t for t in trades_sorted if t["symbol"] == sym]
            logger.info(
                "  %-10s  %2d trades  win=%d  loss=%d  net=%+.2f",
                sym, len(st),
                len([t for t in st if t["pnl"] > 0]),
                len([t for t in st if t["pnl"] < 0]),
                sum(t["pnl"] for t in st),
            )

    finally:
        db_pool.putconn(conn)
        db_pool.closeall()


if __name__ == "__main__":
    main()
