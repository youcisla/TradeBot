"""MetaTrader 5 broker connector.

Implements the BrokerConnector ABC using the MetaTrader5 Python package.
Works with any MT5 broker (PUPrime, ICMarkets, Pepperstone, etc.).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timezone
from typing import Any, cast

import MetaTrader5 as _mt5

# MetaTrader5 runtime package exposes many attributes dynamically and lacks
# complete static type hints, so we cast it to Any for this connector module.
mt5 = cast(Any, _mt5)

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

    def __init__(
        self,
        account: str | None = None,
        password: str | None = None,
        server: str | None = None,
    ) -> None:
        self._connected = False
        self._account = account or settings.BROKER_ACCOUNT
        self._password = password or settings.BROKER_PASSWORD
        self._server = server or settings.BROKER_SERVER
        # Populated after connect()
        self.account_info_cache: dict | None = None

    # ── account ──────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not mt5.initialize():
            logger.error("MT5 initialize failed: %s", mt5.last_error())
            return False

        try:
            account = int(self._account)
        except (TypeError, ValueError):
            logger.error(
                "Invalid BROKER_ACCOUNT value %r — must be a numeric account number",
                self._account,
            )
            mt5.shutdown()
            return False

        authorized = mt5.login(
            account,
            password=self._password,
            server=self._server,
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
        self.account_info_cache = {
            "login": info.login,
            "server": info.server,
            "balance": info.balance,
            "equity": info.equity,
            "leverage": info.leverage,
            "name": info.name,
            "company": info.company,
        }
        self._connected = True
        return True

    def get_available_symbols(self, candidates: list[str]) -> list[str]:
        """Return the subset of *candidates* that are visible in the MT5 terminal.

        If a symbol isn't found under its canonical name, common broker
        suffixes/variants are tried automatically.  A mapping is stored in
        ``self.symbol_map`` so the rest of the code can translate.
        """
        available = []
        self.symbol_map: dict[str, str] = {}   # canonical → broker name
        self._reverse_map: dict[str, str] = {}  # broker name → canonical

        # Common suffixes / variants brokers use
        _SUFFIXES = ["", ".r", ".ecn", "m", "+", ".a", ".b", ".i",
                     ".pro", ".raw", ".std", ".", "#", "-ECN"]
        # Some brokers use completely different names for commodities
        _ALIASES: dict[str, list[str]] = {
            "XAUUSD": ["Gold", "GOLD", "GoldUSD", "XAUUSD.r", "XAUUSD+"],
            "XAGUSD": ["Silver", "SILVER", "SilverUSD", "XAGUSD.r"],
            "USOUSD": ["USOIL", "WTI", "CrudeOIL", "USOil", "USOUSD.r", "WTI.r", "USOIL.r"],
            "UKOUSD": ["UKOIL", "Brent", "BrentOil", "UKOUSD.r", "UKOIL.r"],
        }

        for sym in candidates:
            broker_sym = self._find_broker_symbol(sym, _SUFFIXES, _ALIASES)
            if broker_sym:
                available.append(sym)
                self.symbol_map[sym] = broker_sym
                self._reverse_map[broker_sym] = sym
            # else: symbol not found at all — silently skipped

        return available

    def _find_broker_symbol(self, sym: str, suffixes: list[str],
                            aliases: dict[str, list[str]]) -> str | None:
        """Try to find *sym* on the broker under any known variant."""
        # 1. Exact match
        info = mt5.symbol_info(sym)
        if info is not None:
            mt5.symbol_select(sym, True)
            return sym

        # 2. Enable then retry
        mt5.symbol_select(sym, True)
        info = mt5.symbol_info(sym)
        if info is not None:
            return sym

        # 3. Try suffixes
        for sfx in suffixes:
            if not sfx:
                continue
            candidate = sym + sfx
            mt5.symbol_select(candidate, True)
            info = mt5.symbol_info(candidate)
            if info is not None:
                logger.info("Symbol mapped: %s → %s", sym, candidate)
                return candidate

        # 4. Try aliases
        for alias in aliases.get(sym, []):
            mt5.symbol_select(alias, True)
            info = mt5.symbol_info(alias)
            if info is not None:
                logger.info("Symbol mapped: %s → %s (alias)", sym, alias)
                return alias

        return None

    def get_contract_size(self, symbol: str) -> float:
        """Fetch the actual contract size from MT5 symbol info."""
        broker_sym = self.resolve(symbol)
        info = mt5.symbol_info(broker_sym)
        if info is not None:
            cs = float(info.trade_contract_size)
            from config.symbols import contract_size as _cfg_cs
            cfg_cs = _cfg_cs(symbol)
            if abs(cs - cfg_cs) > 0.01:
                logger.warning(
                    "CONTRACT SIZE MISMATCH for %s: broker=%.2f config=%.2f — using broker value",
                    symbol, cs, cfg_cs,
                )
            return cs
        from config.symbols import contract_size as _cfg_cs
        return _cfg_cs(symbol)

    def get_tick_size(self, symbol: str) -> float:
        """Return the broker's actual minimum price movement (trade_tick_size)."""
        broker_sym = self.resolve(symbol)
        info = mt5.symbol_info(broker_sym)
        if info is not None:
            return float(info.trade_tick_size)
        from config.symbols import pip_value as _pv
        return _pv(symbol)

    def get_tick_value(self, symbol: str) -> float:
        """Return trade_tick_value from MT5 — P&L in account currency per tick per lot.

        MT5 converts cross-currency instruments automatically so this value is
        always in the account's own currency (e.g. EUR on a EUR-denominated demo).
        """
        broker_sym = self.resolve(symbol)
        info = mt5.symbol_info(broker_sym)
        if info is not None:
            return float(info.trade_tick_value)
        from config.symbols import pip_value as _pv, contract_size as _cs
        return _pv(symbol) * _cs(symbol)

    def disconnect(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 disconnected")

    def get_balance(self) -> float:
        info = mt5.account_info()
        if info is not None:
            val = float(info.balance)
            # Only trust and cache non-zero live values.
            # A zero value when the terminal had a recent -18004 IPC error means
            # the account data is stale — prefer the cached value in that case.
            if val > 0.0:
                if self.account_info_cache is not None:
                    self.account_info_cache["balance"] = val
                return val
            # info returned but balance is 0 — possibly stale; use cache if available
            if self.account_info_cache is not None:
                cached = float(self.account_info_cache.get("balance", 0.0))
                if cached > 0.0:
                    return cached
            return val  # genuinely 0 or cache also 0
        # info is None — MT5 called from wrong thread OR IPC broken; use cache
        if self.account_info_cache is not None:
            return float(self.account_info_cache.get("balance", 0.0))
        return 0.0

    def get_equity(self) -> float:
        info = mt5.account_info()
        if info is not None:
            val = float(info.equity)
            if val > 0.0:
                if self.account_info_cache is not None:
                    self.account_info_cache["equity"] = val
                return val
            if self.account_info_cache is not None:
                cached = float(self.account_info_cache.get("equity", 0.0))
                if cached > 0.0:
                    return cached
            return val
        if self.account_info_cache is not None:
            return float(self.account_info_cache.get("equity", 0.0))
        return 0.0

    # ── market data ──────────────────────────────────────────────────────

    def resolve(self, symbol: str) -> str:
        """Translate canonical symbol to broker symbol name."""
        return getattr(self, 'symbol_map', {}).get(symbol, symbol)

    def get_tick(self, symbol: str) -> dict[str, float]:
        broker_sym = self.resolve(symbol)

        tick = mt5.symbol_info_tick(broker_sym)
        if tick is None:
            mt5.symbol_select(broker_sym, True)
            tick = mt5.symbol_info_tick(broker_sym)
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
        broker_sym = self.resolve(symbol)
        tf = _TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)

        # Ensure symbol is selected so MT5 loads its history.
        mt5.symbol_select(broker_sym, True)
        rates = mt5.copy_rates_from_pos(broker_sym, tf, 0, count)
        if rates is None:
            logger.warning("No candle data for %s (%s) %s: %s", symbol, broker_sym, timeframe, mt5.last_error())
            return []
        if len(rates) < count:
            logger.warning(
                "MT5 returned %d/%d candles for %s %s — open the symbol chart in MT5 to load more history",
                len(rates), count, symbol, timeframe,
            )
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
        broker_sym = self.resolve(symbol)
        mt5.symbol_select(broker_sym, True)
        tick = mt5.symbol_info_tick(broker_sym)
        if tick is None:
            return OrderResult(success=False, message=f"No tick for {symbol}")

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        # Use the live fill price — market may have moved since signal detection.
        fill_price = tick.ask if direction == "BUY" else tick.bid

        # ── Pre-validate SL/TP to prevent MT5 error 10016 ────────────────
        # 10016 fires when SL/TP is on the wrong side of the current price or
        # within the broker's stops_level distance.  We detect this before
        # sending so the error message is actionable instead of cryptic.
        si = mt5.symbol_info(broker_sym)
        point = float(si.point) if si is not None else 0.00001
        # stops_level=0 on PU Prime; enforce at least 1 point minimum distance
        # so floating-point equality doesn't trigger a rejection.
        raw_stops = float(si.trade_stops_level) if si is not None else 0.0
        min_dist = max(raw_stops, 1.0) * point

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

        # TP is the broker crash-safety net; trade_manager handles real partials.
        # If TP is already past fill_price (market moved), omit it rather than
        # let it invalidate the whole order.
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

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_sym,
            "volume": float(round(lot_size, 2)),
            "type": order_type,
            "price": fill_price,
            "sl": float(sl) if sl > 0 else 0.0,
            "deviation": 20,
            "magic": 202603,
            "comment": self._sanitize_comment(comment),
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if tp is not None and tp > 0:
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
        broker_sym = self.resolve(symbol)
        mt5.symbol_select(broker_sym, True)
        tick = mt5.symbol_info_tick(broker_sym)
        if tick is None:
            return False

        close_type = mt5.ORDER_TYPE_SELL if direction == "BUY" else mt5.ORDER_TYPE_BUY
        price = tick.bid if direction == "BUY" else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_sym,
            "volume": float(round(lot_size, 2)),
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 202603,
            "comment": self._sanitize_comment("partial_close"),
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

    def get_closed_pnl(self, ticket: int) -> float | None:
        """Sum profit of all deals belonging to this position ticket."""
        try:
            deals = mt5.history_deals_get(position=ticket)
            if deals:
                return float(sum(d.profit for d in deals))
        except Exception:
            logger.debug("history_deals_get failed for ticket %d", ticket)
        return None

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
            take_profit=getattr(pos, 'tp', None),
            current_price=pos.price_current,
            pnl=pos.profit,
            magic=getattr(pos, 'magic', 0),
            comment=getattr(pos, 'comment', ''),
        )

    @staticmethod
    def _sanitize_comment(comment: str | None) -> str:
        """Return an MT5-safe order comment.

        MT5 comments must be short ASCII and can fail on control chars or empty values.
        """
        raw = str(comment or "")
        ascii_only = raw.encode("ascii", "ignore").decode("ascii")
        cleaned = "".join(ch for ch in ascii_only if 32 <= ord(ch) <= 126)
        compact = " ".join(cleaned.split())
        if not compact:
            compact = "bot"
        return compact[:29]
