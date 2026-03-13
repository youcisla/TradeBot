"""MetaTrader 5 broker connector.

Implements the BrokerConnector ABC using the MetaTrader5 Python package.
Works with any MT5 broker (PUPrime, ICMarkets, Pepperstone, etc.).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timezone

import MetaTrader5 as mt5

from broker.connector import BrokerConnector, OrderResult, PositionInfo
from config import settings
from models.market_data import Candle

logger = logging.getLogger(__name__)

# ── Timeframe mapping ────────────────────────────────────────────────────
_TF_MAP: dict[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


class MT5Connector(BrokerConnector):
    """Real MetaTrader 5 broker connection."""

    def __init__(self) -> None:
        self._connected = False

    # ── account ──────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not mt5.initialize():
            logger.error("MT5 initialize failed: %s", mt5.last_error())
            return False

        account = int(settings.BROKER_ACCOUNT)
        authorized = mt5.login(
            account,
            password=settings.BROKER_PASSWORD,
            server=settings.BROKER_SERVER,
        )
        if not authorized:
            logger.error("MT5 login failed: %s", mt5.last_error())
            mt5.shutdown()
            return False

        info = mt5.account_info()
        logger.info(
            "MT5 connected: account=%d  server=%s  balance=%.2f  leverage=%d",
            info.login, info.server, info.balance, info.leverage,
        )
        self._connected = True
        return True

    def get_available_symbols(self, candidates: list[str]) -> list[str]:
        """Return the subset of *candidates* that are visible in the MT5 terminal."""
        available = []
        for sym in candidates:
            info = mt5.symbol_info(sym)
            if info is not None and info.visible:
                available.append(sym)
            else:
                # Try enabling it
                mt5.symbol_select(sym, True)
                info = mt5.symbol_info(sym)
                if info is not None:
                    available.append(sym)
        return available

    def disconnect(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 disconnected")

    def get_balance(self) -> float:
        info = mt5.account_info()
        return float(info.balance) if info else 0.0

    def get_equity(self) -> float:
        info = mt5.account_info()
        return float(info.equity) if info else 0.0

    # ── market data ──────────────────────────────────────────────────────

    def get_tick(self, symbol: str) -> dict[str, float]:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            # Try enabling the symbol
            mt5.symbol_select(symbol, True)
            tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {symbol}: {mt5.last_error()}")
        spread = tick.ask - tick.bid
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": round(spread, 6),
            "volume": float(tick.volume),
        }

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        tf = _TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            logger.warning("No candle data for %s %s: %s", symbol, timeframe, mt5.last_error())
            return []
        candles: list[Candle] = []
        for r in rates:
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(r["time"], tz=UTC),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                )
            )
        return candles

    # ── order management ─────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: float,
        tp: float | None = None,
        comment: str = "",
    ) -> OrderResult:
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return OrderResult(success=False, message=f"No tick for {symbol}")

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if direction == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(round(lot_size, 2)),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "deviation": 20,
            "magic": 202603,
            "comment": comment[:63],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if tp is not None:
            request["tp"] = float(tp)

        result = mt5.order_send(request)
        if result is None:
            return OrderResult(success=False, message=f"order_send returned None: {mt5.last_error()}")

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

    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        pos = self._get_position(ticket)
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
            logger.error("modify_order failed for %d: %s", ticket,
                         result.comment if result else mt5.last_error())
            return False
        return True

    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False

        close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
        price = tick.bid if direction == "BUY" else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(round(lot_size, 2)),
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 202603,
            "comment": "partial_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("close_partial failed for %d: %s", ticket,
                         result.comment if result else mt5.last_error())
            return False
        return True

    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        pos = self._get_position(ticket)
        if pos is None:
            logger.warning("close_order: position %d not found (already closed?)", ticket)
            return True  # Position doesn't exist — treat as success

        return self.close_partial(ticket, symbol, pos.volume, direction)

    def get_open_positions(self) -> list[PositionInfo]:
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [self._mt5_pos_to_info(p) for p in positions]

    def get_fill_size(self, order_id: str) -> float:
        deal = mt5.history_deals_get(ticket=int(order_id))
        if deal:
            return float(deal[0].volume)
        return 0.0

    def reconcile(self) -> list[PositionInfo]:
        return self.get_open_positions()

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _get_position(ticket: int):
        """Return raw MT5 position or None."""
        positions = mt5.positions_get(ticket=ticket)
        if positions and len(positions) > 0:
            return positions[0]
        return None

    @staticmethod
    def _mt5_pos_to_info(pos) -> PositionInfo:
        return PositionInfo(
            ticket=pos.ticket,
            symbol=pos.symbol,
            direction="BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
            lot_size=pos.volume,
            entry_price=pos.price_open,
            stop_loss=pos.sl,
            current_price=pos.price_current,
            pnl=pos.profit,
        )
