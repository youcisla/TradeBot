"""HeartbeatManager — extracted from main.py's _update_heartbeat()."""

from datetime import UTC, datetime
import json
import logging
import time
from pathlib import Path

from broker.connector import BrokerConnector
from database.db import Database
from agents.crucix_agent import CrucixAgent
from agents.trade_manager import TradeManagerAgent
from utils.helpers import current_session
from utils import telegram_bot
from utils import terminal_ui as tui

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Writes current bot metrics to the bot_status row every loop.

    Keeps in-memory caches of equity and balance so a failed MT5 call
    falls back to the last known value rather than zero.
    """

    def __init__(
        self,
        db: Database,
        broker: BrokerConnector,
        spread_monitor,  # SpreadMonitor | None
        guard_pipeline=None,  # GuardPipeline | None
    ) -> None:
        self._db = db
        self._broker = broker
        self._spread_monitor = spread_monitor
        self._guard_pipeline = guard_pipeline
        self._hb_equity = 0.0
        self._hb_balance = 0.0

    def update(
        self,
        trade_manager: TradeManagerAgent,
        crucix_agent: CrucixAgent | None,
    ) -> None:
        """Write one heartbeat row to bot_status."""
        # MT5 API is NOT thread-safe — always call from the main thread.
        try:
            equity = self._broker.get_equity()
            self._hb_equity = equity
        except Exception:
            equity = self._hb_equity

        try:
            balance = self._broker.get_balance()
            self._hb_balance = balance
        except Exception:
            balance = self._hb_balance

        # Authoritative open-position count from MT5.
        try:
            mt5_positions = self._broker.get_open_positions()
            open_count = len(mt5_positions)
        except Exception:
            open_count = len(trade_manager.get_open_trades())

        # Daily realised P&L — source of truth from MT5 deal history.
        try:
            daily_pnl = self._broker.get_daily_pnl()
        except Exception:
            daily_pnl = 0.0

        state = "paused" if telegram_bot.is_paused() else "running"

        # ── Equity/balance sanity check ─────────────────────────────────
        if open_count == 0 and abs(equity - balance) > 0.01:
            try:
                mt5_positions = self._broker.get_open_positions()
                if mt5_positions:
                    for pos in mt5_positions:
                        logger.warning(
                            "UNTRACKED MT5 POSITION: ticket=%s symbol=%s volume=%s profit=%s",
                            pos.ticket, pos.symbol, pos.lot_size, pos.profit,
                        )
                else:
                    logger.warning(
                        "EQUITY/BALANCE MISMATCH: equity=%.2f balance=%.2f gap=%.2f",
                        equity, balance, equity - balance,
                    )
            except Exception as exc:
                logger.warning("Equity check failed: %s", exc)

        # ── Broker metadata ─────────────────────────────────────────────
        broker_account = ""
        broker_server = ""
        broker_name = ""
        leverage = 0
        info = getattr(self._broker, "account_info_cache", None)
        if info:
            broker_account = str(info.get("login", ""))
            broker_server = info.get("server", "")
            broker_name = info.get("name", "")
            leverage = info.get("leverage", 0)

        # ── Spread monitoring ─────────────────────────────────────────────
        spread_pips = 0.0
        spread_cond = "unknown"
        if self._spread_monitor is not None:
            try:
                spread_pts = self._broker.get_spread("EURUSD")
                spread_pips = spread_pts / 10.0  # 5-digit broker: points → pips
                self._spread_monitor.record(spread_pips)
                spread_cond = self._spread_monitor.condition.name.lower()
            except Exception:
                pass

        # ── Session + market regime ────────────────────────────────────
        current_sess = current_session(datetime.now(UTC))
        if spread_cond in ("high", "extreme"):
            regime = "volatile"
        elif current_sess == "overlap":
            regime = "high_volume"
        elif current_sess == "asian":
            regime = "quiet"
        else:
            regime = "normal"

        # ── VIX from Crucix ─────────────────────────────────────────────
        vix = 0.0
        try:
            if crucix_agent:
                ctx = crucix_agent.get_context()
                vix = getattr(ctx, "vix", 0.0) or 0.0
        except Exception:
            pass

        # ── Risk metrics ────────────────────────────────────────────────
        daily_loss_pct = abs(daily_pnl) / balance if balance > 0 else 0.0
        eq_dd_pct = 0.0
        try:
            peak_file = Path(__file__).resolve().parent.parent / "data" / "equity_peak.json"
            if peak_file.exists():
                with open(peak_file) as f:
                    peak = json.load(f).get("peak", 0.0)
                if peak > 0:
                    eq_dd_pct = max(0.0, (peak - equity) / peak)
        except Exception:
            pass

        self._db.update_bot_status(
            state, equity, open_count, daily_pnl,
            broker_account=broker_account,
            broker_server=broker_server,
            broker_name=broker_name,
            balance=balance,
            leverage=leverage,
            spread_condition=spread_cond,
            current_session=current_sess,
            market_regime=regime,
            spread_pips=spread_pips,
            vix=vix,
            daily_loss_pct=daily_loss_pct,
            equity_drawdown_pct=eq_dd_pct,
        )

        # ── Guard pipeline status ─────────────────────────────────────────────
        if self._guard_pipeline is not None:
            try:
                guard_status = self._guard_pipeline.get_status(
                    self._broker,
                    trade_manager.get_open_trades(),
                )
                self._db.status.update_guard_status(guard_status)
            except Exception as exc:
                logger.warning("Guard status snapshot failed: %s", exc)

        # ── Terminal UI update ────────────────────────────────────────────
        ui = tui.get_ui()
        if ui is not None:
            ui.set_bot_status(
                state.upper(), equity=equity, balance=balance,
                daily_pnl=daily_pnl, open_trades=open_count,
            )
            for t in trade_manager.get_open_trades():
                ui.set_trade(t)
