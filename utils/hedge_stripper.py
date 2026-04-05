"""hedge_stripper.py — detects and flags opposing positions on the same symbol.

Most retail prop-firm rules prohibit simultaneous BUY + SELL on the same
instrument.  The ``HedgeStripper`` scans the open-trade book, finds all such
"lock" positions, and returns close instructions for the *smaller* leg of
each hedge pair so the net is rolled to a single-direction position.

Usage::

    from utils.hedge_stripper import HedgeStripper, HedgePair

    hs = HedgeStripper()
    pairs = hs.find_hedges(open_trades)
    for pair in pairs:
        print(f"Close ticket {pair.close_ticket_id} ({pair.lots_to_close}L) to strip hedge")

Design constraints:
    - Only flags; does NOT execute closes itself
    - Fail-open: returns empty list on any error
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HedgePair:
    symbol: str
    buy_ticket_id: Any
    sell_ticket_id: Any
    buy_lots: float
    sell_lots: float
    net_lots: float           # positive = net BUY, negative = net SELL
    close_ticket_id: Any      # the smaller leg to close
    lots_to_close: float      # how many lots of that ticket to close


class HedgeStripper:
    """Identifies and recommends closure of hedge (lock) positions."""

    def find_hedges(self, open_trades: list) -> list[HedgePair]:
        """Return a list of hedge pairs found in *open_trades*.

        Parameters
        ----------
        open_trades : list of Trade-like objects.
            Each must expose ``.symbol``, ``.direction`` ("BUY"/"SELL"),
            ``.lot_size``, and ``.ticket_id`` (or ``.id``).
        """
        try:
            return self._scan(open_trades)
        except Exception as exc:  # noqa: BLE001
            logger.debug("HedgeStripper.find_hedges error: %s", exc)
            return []

    @staticmethod
    def _scan(open_trades: list) -> list[HedgePair]:
        # Group by symbol
        by_symbol: dict[str, list] = {}
        for t in open_trades:
            sym = getattr(t, "symbol", None) or getattr(t, "pair", "")
            by_symbol.setdefault(sym, []).append(t)

        pairs: list[HedgePair] = []

        for symbol, trades in by_symbol.items():
            buys = [t for t in trades if _direction(t) == "BUY"]
            sells = [t for t in trades if _direction(t) == "SELL"]

            if not buys or not sells:
                continue  # no opposing positions

            total_buy_lots = sum(_lots(t) for t in buys)
            total_sell_lots = sum(_lots(t) for t in sells)
            net = total_buy_lots - total_sell_lots

            # Identify the smaller-leg ticket to recommend closing
            if net >= 0:
                # Sell side is smaller (or equal)
                close_ticket = _ticket(sells[0])   # oldest/first sell
                lots_to_close = round(
                    min(total_sell_lots, total_buy_lots), 5
                )
            else:
                close_ticket = _ticket(buys[0])
                lots_to_close = round(
                    min(total_buy_lots, total_sell_lots), 5
                )

            # Use the first buy/sell ticket as representative
            pairs.append(HedgePair(
                symbol=symbol,
                buy_ticket_id=_ticket(buys[0]),
                sell_ticket_id=_ticket(sells[0]),
                buy_lots=round(total_buy_lots, 5),
                sell_lots=round(total_sell_lots, 5),
                net_lots=round(net, 5),
                close_ticket_id=close_ticket,
                lots_to_close=lots_to_close,
            ))

            logger.warning(
                "HedgeStripper: HEDGE detected on %s "
                "(%.5f BUY / %.5f SELL) → recommend closing ticket %s",
                symbol, total_buy_lots, total_sell_lots, close_ticket,
            )

        return pairs


# ── Helpers ───────────────────────────────────────────────────────────────

def _direction(trade) -> str:
    return str(getattr(trade, "direction", "") or getattr(trade, "type", "")).upper()


def _lots(trade) -> float:
    return float(getattr(trade, "lot_size", 0) or getattr(trade, "volume", 0))


def _ticket(trade):
    return getattr(trade, "ticket_id", None) or getattr(trade, "id", None)
