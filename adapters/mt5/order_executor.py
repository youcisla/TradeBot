"""MetaTrader 5 order execution.

Handles order placement with SL/TP pre-validation, volume normalization,
partial close, order modification, and position queries.
"""

from __future__ import annotations

import logging
import time
from typing import Any, cast

import MetaTrader5 as _mt5

mt5 = cast(Any, _mt5)

from broker.connector import MAGIC, BrokerConnector, OrderResult, PositionInfo
from config import settings

logger = logging.getLogger(__name__)


def place_order(
    connector,
    symbol: str,
    direction: str,
    lot_size: float,
    sl: float,
    tp: float | None = None,
    comment: str = "",
) -> OrderResult:
    broker_sym = connector.resolve(symbol)
    mt5.symbol_select(broker_sym, True)
    tick = mt5.symbol_info_tick(broker_sym)
    if tick is None:
        return OrderResult(success=False, message=f"No tick for {symbol}")

    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    fill_price = tick.ask if direction == "BUY" else tick.bid

    si = mt5.symbol_info(broker_sym)
    point = float(si.point) if si is not None else 0.00001
    raw_stops = float(si.trade_stops_level) if si is not None else 0.0
    min_dist = max(raw_stops, 1.0) * point
    sl_check_price = tick.bid if direction == "BUY" else tick.ask

    if sl > 0:
        if direction == "BUY" and sl >= fill_price - min_dist:
            return OrderResult(
                success=False,
                message=(
                    f"10016: BUY stop_loss={sl:.5f} is at or above "
                    f"fill_price={fill_price:.5f} (min_dist={min_dist:.5f}) "
                    f"— signal stale, market moved"
                ),
            )
        if direction == "SELL" and sl <= fill_price + min_dist:
            return OrderResult(
                success=False,
                message=(
                    f"10016: SELL stop_loss={sl:.5f} is at or below "
                    f"fill_price={fill_price:.5f} (min_dist={min_dist:.5f}) "
                    f"— signal stale, market moved"
                ),
            )
        if direction == "SELL" and sl <= sl_check_price + min_dist:
            logger.warning(
                "10016 risk: SELL %s sl=%.5f <= current_bid=%.5f + min_dist=%.5f "
                "(raw_stops=%.1f pts, point=%.6f). Omitting SL and retrying without it.",
                symbol, sl, sl_check_price, min_dist, raw_stops, point,
            )
            sl = 0.0
        elif direction == "BUY" and sl >= sl_check_price - min_dist:
            logger.warning(
                "10016 risk: BUY %s sl=%.5f >= current_ask=%.5f - min_dist=%.5f "
                "(raw_stops=%.1f pts, point=%.6f). Omitting SL and retrying without it.",
                symbol, sl, sl_check_price, min_dist, raw_stops, point,
            )
            sl = 0.0

    if tp is not None and tp > 0:
        if direction == "BUY" and tp <= fill_price + min_dist:
            logger.warning(
                "Omitting broker TP for BUY %s: tp=%.5f <= fill=%.5f (stale)",
                symbol, tp, fill_price,
            )
            tp = None
        elif direction == "SELL" and tp >= fill_price - min_dist:
            logger.warning(
                "Omitting broker TP for SELL %s: tp=%.5f >= fill=%.5f (stale)",
                symbol, tp, fill_price,
            )
            tp = None

    requested_volume = float(lot_size)
    normalized_volume = normalize_volume(broker_sym, requested_volume)
    if normalized_volume <= 0:
        return OrderResult(
            success=False,
            message=(
                f"Invalid lot size for {symbol}: requested={requested_volume:.4f} "
                "cannot be normalized to broker volume rules"
            ),
        )
    if abs(normalized_volume - requested_volume) > 1e-9:
        logger.info(
            "Volume normalized for %s: requested %.4f -> %.4f",
            symbol,
            requested_volume,
            normalized_volume,
        )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": broker_sym,
        "volume": normalized_volume,
        "type": order_type,
        "price": fill_price,
        "sl": float(sl) if sl > 0 else 0.0,
        "deviation": 20,
        "magic": 202603,
        "comment": sanitize_comment(comment),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if tp is not None and tp > 0:
        request["tp"] = float(tp)

    result = mt5.order_send(request)
    if result is None:
        # IPC timeout.  The request may still have reached the broker, so a
        # position can exist with no OrderResult to prove it.  Reconcile before
        # declaring failure — otherwise the position is orphaned: live at the
        # broker, invisible to the bot, with no SL/TP management.
        recovered = _recover_ambiguous_order(broker_sym, direction)
        if recovered is not None:
            logger.error(
                "order_send returned None for %s but position %d exists — adopting it",
                symbol,
                recovered.broker_ticket,
            )
            return recovered
        return OrderResult(success=False, message=f"order_send returned None: {mt5.last_error()}")

    if result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL:
        # IOC filled only part of the request.  A real position exists and must
        # be tracked at its actual size rather than discarded as a failure.
        logger.warning(
            "Partial fill for %s: requested %.4f, filled %.4f",
            symbol,
            normalized_volume,
            result.volume,
        )
        return OrderResult(
            success=True,
            order_id=str(result.order),
            broker_ticket=result.order,
            filled_lots=result.volume,
            fill_price=result.price,
            message=f"partial fill {result.volume}/{normalized_volume}",
        )

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return OrderResult(
            success=False,
            message=f"MT5 error {result.retcode}: {result.comment}",
        )

    return OrderResult(
        success=True,
        order_id=str(result.order),
        broker_ticket=result.order,
        filled_lots=result.volume,
        fill_price=result.price,
        message="OK",
    )


def _recover_ambiguous_order(broker_sym: str, direction: str) -> OrderResult | None:
    """Find a position this bot may have opened despite an ambiguous result.

    Only positions carrying this bot's magic number are considered, so a trade
    placed by hand or by another EA is never silently adopted.
    """
    positions = mt5.positions_get(symbol=broker_sym)
    if not positions:
        return None
    for pos in positions:
        if getattr(pos, "magic", 0) != MAGIC:
            continue
        pos_dir = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        if pos_dir != direction:
            continue
        return OrderResult(
            success=True,
            order_id=str(pos.ticket),
            broker_ticket=pos.ticket,
            filled_lots=float(pos.volume),
            fill_price=float(pos.price_open),
            message="recovered after ambiguous order_send",
        )
    return None


def modify_order(
    connector,
    ticket: int,
    sl: float | None = None,
    tp: float | None = None,
) -> bool:
    pos = get_position(ticket)
    if pos is None:
        logger.warning("modify_order: position %d not found", ticket)
        return False

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": pos.symbol,
        "sl": float(sl) if sl is not None else pos.sl,
        "tp": float(tp) if tp is not None else pos.tp,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(
            "modify_order failed for %d: %s",
            ticket,
            result.comment if result else mt5.last_error(),
        )
        return False
    return True


def close_partial(
    connector,
    ticket: int,
    symbol: str,
    lot_size: float,
    direction: str,
) -> bool:
    broker_sym = connector.resolve(symbol)
    mt5.symbol_select(broker_sym, True)

    close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(broker_sym)
    if tick is None:
        return False
    price = tick.bid if direction == "BUY" else tick.ask

    requested_volume = float(lot_size)
    max_attempts = 3
    backoff_ms = [250, 500, 1000]

    for attempt in range(1, max_attempts + 1):
        pos = get_position(ticket)
        if pos is None:
            logger.info(
                "close_partial %d: position gone, considering it closed",
                ticket,
            )
            return True

        live_volume = float(pos.volume)
        normalized_volume = _partial_close_volume(
            broker_sym, requested_volume, live_volume
        )
        if normalized_volume <= 0:
            logger.error(
                "close_partial rejected for %d (%s): live volume %.4f invalid for broker rules",
                ticket,
                symbol,
                live_volume,
            )
            return False

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_sym,
            "volume": normalized_volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": MAGIC,
            "comment": sanitize_comment("partial_close"),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(
                "close_partial %d succeeded: %.4f %s (attempt %d/%d)",
                ticket,
                normalized_volume,
                symbol,
                attempt,
                max_attempts,
            )
            return True

        logger.warning(
            "close_partial %d attempt %d/%d failed: %s (retrying…)",
            ticket,
            attempt,
            max_attempts,
            result.comment if result else mt5.last_error(),
        )

        if attempt < max_attempts:
            time.sleep(backoff_ms[attempt - 1] / 1000.0)

    logger.error(
        "close_partial exhausted all %d attempts for %d",
        max_attempts,
        ticket,
    )
    return False


def _volume_min(symbol: str) -> float:
    """Broker minimum tradable volume for *symbol*, or 0.0 if unknown."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0
    return float(getattr(info, "volume_min", 0.0) or 0.0)


def _partial_close_volume(symbol: str, requested: float, live: float) -> float:
    """Volume to actually send for a partial close.

    Never exceeds what is open.  If the requested slice rounds below the
    broker's minimum, or closing it would strand a remainder smaller than that
    minimum, the whole position is closed instead — a dust remainder can never
    be closed later by any subsequent partial, so leaving one behind would
    permanently strand lots.
    """
    if requested <= 0 or live <= 0:
        return 0.0

    normalized = normalize_volume(symbol, min(requested, live), for_close=True)
    if normalized <= 0:
        return normalize_volume(symbol, live, for_close=True)

    remainder = live - normalized
    min_vol = _volume_min(symbol)
    if remainder > 1e-9 and 0.0 < remainder < min_vol:
        logger.info(
            "close_partial %s: closing full %.4f instead of %.4f "
            "(remainder %.4f below broker min %.4f)",
            symbol, live, normalized, remainder, min_vol,
        )
        return normalize_volume(symbol, live, for_close=True)
    return normalized


def close_order(connector, ticket: int, symbol: str, direction: str) -> bool:
    pos = get_position(ticket)
    if pos is None:
        logger.warning(
            "close_order: position %d not found (already closed?)",
            ticket,
        )
        return True

    return close_partial(connector, ticket, symbol, pos.volume, direction)


def get_open_positions() -> list[PositionInfo]:
    positions = mt5.positions_get()
    if positions is None:
        return []
    return [mt5_pos_to_info(p) for p in positions]


def get_position(ticket: int):
    positions = mt5.positions_get(ticket=ticket)
    if positions and len(positions) > 0:
        return positions[0]
    return None


def get_fill_size(order_id: str) -> float:
    deal = mt5.history_deals_get(ticket=int(order_id))
    if deal:
        return float(deal[0].volume)
    return 0.0


def mt5_pos_to_info(pos) -> PositionInfo:
    return PositionInfo(
        ticket=pos.ticket,
        symbol=pos.symbol,
        direction="BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
        lot_size=pos.volume,
        entry_price=pos.price_open,
        stop_loss=pos.sl,
        take_profit=getattr(pos, 'tp', None),
        current_price=pos.price_current,
        pnl=pos.profit,
        magic=getattr(pos, 'magic', 0),
        comment=getattr(pos, 'comment', ''),
    )


def normalize_volume(
    symbol: str,
    requested: float,
    for_close: bool = False,
) -> float:
    """Normalize volume to broker min/max/step rules. Returns 0.0 on invalid."""
    if not for_close:
        fixed_lot = getattr(settings, "FIXED_LOT_SIZE", None)
        if fixed_lot is not None and fixed_lot > 0:
            if requested != fixed_lot:
                logger.info(
                    "FIXED_LOT_SIZE enforced for %s: computed %.4f → %.4f",
                    symbol, requested, fixed_lot,
                )
            requested = fixed_lot

    if requested <= 0:
        return 0.0

    info = mt5.symbol_info(symbol)
    if info is None:
        return round(requested, 2)

    volume_min = float(getattr(info, "volume_min", 0.0) or 0.0)
    volume_max = float(getattr(info, "volume_max", 0.0) or 0.0)
    volume_step = float(getattr(info, "volume_step", 0.0) or 0.0)

    volume = requested
    if volume_step > 0:
        steps = int(volume / volume_step)
        volume = steps * volume_step

    if volume_min > 0 and volume < volume_min:
        return 0.0
    if volume_max > 0 and volume > volume_max:
        if volume_step > 0:
            steps = int(volume_max / volume_step)
            volume = steps * volume_step
        else:
            volume = volume_max

    if volume <= 0:
        return 0.0

    if volume_step > 0:
        decimals = max(
            0,
            len(f"{volume_step:.8f}".rstrip("0").split(".")[-1]),
        )
        return round(volume, decimals)
    return round(volume, 2)


def sanitize_comment(comment: str | None) -> str:
    """Return an MT5-safe order comment (short ASCII, max 29 chars)."""
    raw = str(comment or "")
    ascii_only = raw.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch for ch in ascii_only if 32 <= ord(ch) <= 126)
    compact = " ".join(cleaned.split())
    if not compact:
        compact = "bot"
    return compact[:29]
