"""PostgreSQL database handler — facade over repository pattern.

Uses psycopg2 with a connection pool.  Connects to Vercel Postgres via
the DATABASE_URL environment variable.

Tables
------
- trades              – open & closed trade state (crash recovery)
- trade_scores        – learning system scoring per closed trade
- strategy_confidence – per-strategy confidence values
- agent_events        – persona-style event log per agent
- bot_commands        – command queue written by UI, read by bot
- bot_status          – single-row heartbeat

Architecture
-----------
All new code should use the repository sub-objects directly:

    db.trades.save(trade)
    db.events.log_agent_event("agent", "info", "message")
    db.status.update_bot_status("running", equity=1000, ...)
    db.users.get_user_by_username("alice")
    db.signals.save_signal(...)
    db.social.get_leaderboard()
    db.macro.save_macro_snapshot(...)

All existing callers (agents, strategies, web API) continue using the
facade methods with zero changes required:

    db.save_trade(trade)         # → db.trades.upsert_trade(trade)
    db.log_agent_event(...)      # → db.events.log_agent_event(...)
    db.update_bot_status(...)    # → db.status.update_bot_status(...)

"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from config import settings

from .pool import ConnectionPool
from .schema import (
    _ALL_TABLES,
    _SCHEMA_MIGRATIONS,
    _INIT_BOT_STATUS,
)
from .trade_repo import TradeRepo
from .event_repo import EventRepo
from .status_repo import StatusRepo
from .learning_repo import LearningRepo
from .broker_repo import BrokerRepo
from .user_repo import UserRepo
from .signal_repo import SignalRepo
from .social_repo import SocialRepo
from .macro_repo import MacroRepo

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL facade — all existing method signatures preserved.

    New code should use the repository sub-objects for better cohesion.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or settings.DATABASE_URL
        self._pool = ConnectionPool(self._dsn)

        # Repository sub-objects (new internal API)
        self.trades = TradeRepo(self._pool)
        self.events = EventRepo(self._pool)
        self.status = StatusRepo(self._pool)
        self.learning = LearningRepo(self._pool)
        self.broker = BrokerRepo(self._pool)
        self.users = UserRepo(self._pool)
        self.signals = SignalRepo(self._pool)
        self.social = SocialRepo(self._pool)
        self.macro = MacroRepo(self._pool)

        self._create_tables()

    # ── pool (shared with repos) ─────────────────────────────────────────

    def _get_conn(self):
        return self._pool.get_conn()

    def _put_conn(self, conn):
        self._pool.put_conn(conn)

    def _reconnect(self) -> None:
        self._pool._reconnect()

    def close(self) -> None:
        self._pool.close()

    # ── schema ───────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    for ddl in _ALL_TABLES:
                        cur.execute(ddl)
                    for migration in _SCHEMA_MIGRATIONS:
                        cur.execute(migration)
                    cur.execute(_INIT_BOT_STATUS)
            logger.info("Database tables verified")
        finally:
            self._put_conn(conn)
        self.purge_old_data()

    def purge_old_data(self) -> None:
        """Delete stale rows and expire pending approvals."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agent_events WHERE created_at < NOW() - INTERVAL '14 days'"
                    )
                    n_events = cur.rowcount
                    cur.execute(
                        "DELETE FROM bot_commands WHERE status='done' AND created_at < NOW() - INTERVAL '7 days'"
                    )
                    n_cmds = cur.rowcount
                    cur.execute(
                        "DELETE FROM ict_setups WHERE created_at < NOW() - INTERVAL '30 days'"
                    )
                    n_ict = cur.rowcount
                    cur.execute(
                        "DELETE FROM macro_snapshots WHERE fetched_at < NOW() - INTERVAL '7 days'"
                    )
                    n_macro = cur.rowcount
                    cur.execute(
                        """
                        UPDATE bot_commands
                        SET status = 'failed',
                            result = 'Expired: approval not received within 1 hour',
                            executed_at = NOW()
                        WHERE status = 'pending_confirmation'
                          AND created_at < NOW() - INTERVAL '1 hour'
                        """
                    )
                    n_expired = cur.rowcount
            if n_events or n_cmds or n_ict or n_macro or n_expired:
                logger.info(
                    "DB purge: removed %d agent_events, %d bot_commands, %d ict_setups, "
                    "%d macro_snapshots; expired %d stale approval requests",
                    n_events, n_cmds, n_ict, n_macro, n_expired,
                )
        except Exception:
            logger.exception("DB purge failed (non-fatal)")
        finally:
            self._put_conn(conn)

    # ── trade persistence (facade → trades repo) ─────────────────────────

    def upsert_trade(self, t) -> None:
        return self.trades.upsert_trade(t)

    def update_live_state(self, trade_id: str, pnl: float, current_price: float) -> None:
        return self.trades.update_live_state(trade_id, pnl, current_price)

    def get_open_trades(self):
        return self.trades.get_open_trades()

    def get_all_trades(self):
        return self.trades.get_all_trades()

    def get_trade(self, trade_id: str):
        return self.trades.get_trade(trade_id)

    def get_trade_by_broker_ticket(self, broker_ticket: int):
        return self.trades.get_trade_by_broker_ticket(broker_ticket)

    def get_trades_closed_today(self):
        return self.trades.get_trades_closed_today()

    def count_closed_trades(self) -> int:
        return self.trades.count_closed_trades()

    def get_closed_trades_since(self, since: datetime, limit: int = 500):
        return self.trades.get_closed_trades_since(since, limit)

    # ── trade scores (facade → learning repo) ───────────────────────────

    def insert_score(self, *args, **kwargs) -> None:
        return self.learning.insert_score(*args, **kwargs)

    # ── strategy confidence (facade → learning repo) ───────────────────

    def get_confidence(self, strategy: str) -> float:
        return self.learning.get_confidence(strategy)

    def upsert_confidence(self, strategy: str, confidence: float,
                          total_trades: int, total_score: int) -> None:
        return self.learning.upsert_confidence(strategy, confidence, total_trades, total_score)

    def get_rolling_avg_score(self, strategy: str, n: int = 10) -> float | None:
        return self.learning.get_rolling_avg_score(strategy, n)

    def get_strategy_streak(self, strategy: str) -> int:
        return self.learning.get_strategy_streak(strategy)

    def update_strategy_streak(self, strategy: str,
                                win_streak: int, last_score: float) -> None:
        return self.learning.update_strategy_streak(strategy, win_streak, last_score)

    def save_performance_snapshot(self, *args, **kwargs) -> None:
        return self.learning.save_performance_snapshot(*args, **kwargs)

    def get_previous_snapshot(self, period_type: str, before_key: str) -> dict | None:
        return self.learning.get_previous_snapshot(period_type, before_key)

    def get_period_stats(self, since: datetime, until: datetime) -> dict:
        return self.learning.get_period_stats(since, until)

    def get_recent_strategy_regime_stats(self, *args, **kwargs) -> list[dict]:
        return self.learning.get_recent_strategy_regime_stats(*args, **kwargs)

    def get_recent_context_outcomes(self, *args, **kwargs) -> dict[str, float | int]:
        return self.learning.get_recent_context_outcomes(*args, **kwargs)

    def boost_all_strategy_confidence(self, boost: float) -> None:
        return self.learning.boost_all_strategy_confidence(boost)

    def reset_learning_state(self) -> dict[str, int]:
        result = self.learning.reset_learning_state()
        self.log_agent_event(
            "learning_agent",
            "warning",
            "Learning state reset requested; historical scoring cleared",
            result,
        )
        return result

    # ── agent events (facade → events repo) ────────────────────────────

    def log_agent_event(self, agent: str, level: str, message: str,
                        data: dict | None = None) -> None:
        return self.events.log_agent_event(agent, level, message, data)

    def log_event(self, level: str, source: str, message: str,
                  data: str | None = None) -> None:
        return self.events.log_event(level, source, message, data)

    # ── bot commands (facade → events repo) ─────────────────────────────

    def get_pending_commands(self) -> list[dict]:
        return self.events.get_pending_commands()

    def claim_pending_commands(self, limit: int = 25) -> list[dict]:
        return self.events.claim_pending_commands(limit)

    def update_command(self, cmd_id: int, status: str,
                       result: str | None = None, *,
                       set_executed: bool = True) -> None:
        return self.events.update_command(cmd_id, status, result, set_executed=set_executed)

    def review_command(self, cmd_id: int, *, approved: bool,
                       reviewer: str, reason: str) -> bool:
        return self.events.review_command(cmd_id, approved=approved,
                                          reviewer=reviewer, reason=reason)

    def start_session(self, version: str = "") -> int:
        return self.events.start_session(version)

    def end_session(self, session_id: int, exit_reason: str = "normal") -> None:
        return self.events.end_session(session_id, exit_reason)

    # ── bot status (facade → status repo) ───────────────────────────────

    def update_bot_status(self, state: str, equity: float,
                          open_trades: int, daily_pnl: float,
                          broker_account: str = "", broker_server: str = "",
                          broker_name: str = "", balance: float = 0.0,
                          leverage: int = 0,
                          spread_condition: str = "unknown",
                          current_session: str = "unknown",
                          market_regime: str = "unknown",
                          spread_pips: float = 0.0,
                          vix: float = 0.0,
                          daily_loss_pct: float = 0.0,
                          equity_drawdown_pct: float = 0.0) -> None:
        return self.status.update_bot_status(
            state, equity, open_trades, daily_pnl,
            broker_account=broker_account, broker_server=broker_server,
            broker_name=broker_name, balance=balance, leverage=leverage,
            spread_condition=spread_condition, current_session=current_session,
            market_regime=market_regime, spread_pips=spread_pips,
            vix=vix, daily_loss_pct=daily_loss_pct,
            equity_drawdown_pct=equity_drawdown_pct,
        )

    def set_bot_uptime_start(self) -> None:
        return self.status.set_bot_uptime_start()

    def set_bot_stopped(self) -> None:
        return self.status.set_bot_stopped()

    # ── symbol faults (facade → broker repo) ────────────────────────────

    def load_symbol_faults(self) -> dict[str, dict]:
        return self.broker.load_symbol_faults()

    def save_symbol_fault(self, symbol: str, fail_count: int,
                          disabled_until: datetime | None) -> None:
        return self.broker.save_symbol_fault(symbol, fail_count, disabled_until)

    # ── broker accounts (facade → broker repo) ─────────────────────────

    def get_broker_accounts(self, user_id: int | None = None) -> list[dict]:
        return self.broker.get_broker_accounts(user_id)

    def get_active_broker_account(self) -> dict | None:
        return self.broker.get_active_broker_account()

    def add_broker_account(self, name: str, account_number: str,
                           password: str, server: str,
                           is_demo: bool = True,
                           user_id: int | None = None) -> int:
        return self.broker.add_broker_account(name, account_number, password,
                                               server, is_demo, user_id)

    def update_broker_account(self, account_id: int, name: str,
                              account_number: str, password: str | None,
                              server: str, is_demo: bool) -> None:
        return self.broker.update_broker_account(
            account_id, name, account_number, password, server, is_demo)

    def delete_broker_account(self, account_id: int) -> None:
        return self.broker.delete_broker_account(account_id)

    def activate_broker_account(self, account_id: int) -> None:
        return self.broker.activate_broker_account(account_id)

    def mark_broker_connected(self, account_id: int) -> None:
        return self.broker.mark_broker_connected(account_id)

    # ── ICT setups (facade → signals repo) ───────────────────────────────

    def save_ict_setup(self, setup: dict) -> None:
        return self.signals.save_ict_setup(setup)

    # ── trade theses (facade → signals repo) ─────────────────────────────

    def save_trade_thesis(self, *, symbol: str, direction: str = "",
                          stage: str = "IDEA", trade_id: str | None = None,
                          entry_price: float | None = None,
                          sl_price: float | None = None,
                          tp_price: float | None = None,
                          rr_ratio: float | None = None,
                          bull_case: str = "", bear_case: str = "",
                          entry_reason: str = "", notes: str = "") -> int:
        return self.signals.save_trade_thesis(
            symbol=symbol, direction=direction, stage=stage,
            trade_id=trade_id, entry_price=entry_price,
            sl_price=sl_price, tp_price=tp_price, rr_ratio=rr_ratio,
            bull_case=bull_case, bear_case=bear_case,
            entry_reason=entry_reason, notes=notes)

    def get_trade_thesis(self, trade_id: str) -> dict | None:
        return self.signals.get_trade_thesis(trade_id)

    def update_trade_outcome(self, trade_id: str, *,
                             actual_outcome: str,
                             mae_pips: float | None = None,
                             mfe_pips: float | None = None,
                             notes: str = "") -> None:
        return self.signals.update_trade_outcome(
            trade_id, actual_outcome=actual_outcome,
            mae_pips=mae_pips, mfe_pips=mfe_pips, notes=notes)

    # ── dashboard users (facade → users repo) ──────────────────────────

    def get_user_by_username(self, username: str) -> dict | None:
        return self.users.get_user_by_username(username)

    def get_user_by_id(self, user_id: int) -> dict | None:
        return self.users.get_user_by_id(user_id)

    def create_user(self, username: str, password_hash: str) -> int:
        return self.users.create_user(username, password_hash)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        return self.users.update_user_password(user_id, password_hash)

    def get_all_users(self) -> list[dict]:
        return self.users.get_all_users()

    def user_count(self) -> int:
        return self.users.user_count()

    # ── signals (facade → signals repo) ─────────────────────────────────

    def save_signal(self, *, signal_intent: str, signal_type: str,
                    strategy: str, symbol: str = "", direction: str = "",
                    entry_price: float = 0.0, stop_loss: float = 0.0,
                    take_profit_1: float = 0.0, confidence: float = 0.5,
                    reason: str = "", bull_case: str = "", bear_case: str = "",
                    author: str = "bot", tags: list[str] | None = None) -> int:
        return self.signals.save_signal(
            signal_intent=signal_intent, signal_type=signal_type,
            strategy=strategy, symbol=symbol, direction=direction,
            entry_price=entry_price, stop_loss=stop_loss,
            take_profit_1=take_profit_1, confidence=confidence,
            reason=reason, bull_case=bull_case, bear_case=bear_case,
            author=author, tags=tags)

    def get_signals(self, signal_intent: str | None = None,
                    signal_type: str | None = None,
                    strategy: str | None = None,
                    author: str | None = None,
                    limit: int = 50) -> list[dict]:
        return self.signals.get_signals(
            signal_intent=signal_intent, signal_type=signal_type,
            strategy=strategy, author=author, limit=limit)

    def mark_signal_points_awarded(self, signal_id: int) -> None:
        return self.signals.mark_signal_points_awarded(signal_id)

    # ── agent reputation (facade → social repo) ─────────────────────────

    def get_agent_reputation(self, agent: str) -> dict:
        return self.social.get_agent_reputation(agent)

    def bump_agent_reputation(self, agent: str, *, adopted: bool = False,
                              points_delta: int = 0,
                              score_delta: int = 0) -> None:
        return self.social.bump_agent_reputation(
            agent, adopted=adopted, points_delta=points_delta, score_delta=score_delta)

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        return self.social.get_leaderboard(limit)

    # ── subscriptions (facade → social repo) ────────────────────────────

    def save_subscription(self, follower_id: str, leader_id: str,
                          leader_strategy: str = "all") -> int:
        return self.social.save_subscription(follower_id, leader_id, leader_strategy)

    def get_subscriptions(self, follower_id: str | None = None,
                          leader_id: str | None = None) -> list[dict]:
        return self.social.get_subscriptions(follower_id, leader_id)

    def delete_subscription(self, follower_id: str, leader_id: str) -> bool:
        return self.social.delete_subscription(follower_id, leader_id)

    def get_followers(self, leader_id: str) -> list[dict]:
        return self.social.get_followers(leader_id)

    # ── macro snapshots (facade → macro repo) ─────────────────────────

    def save_macro_snapshot(self, snapshot_data: dict) -> None:
        return self.macro.save_macro_snapshot(snapshot_data)

    def get_macro_snapshots(self, lookback_hours: int = 24,
                            risk_tier: str | None = None,
                            limit: int = 100) -> list[dict]:
        return self.macro.get_macro_snapshots(lookback_hours, risk_tier, limit)

    def prune_macro_snapshots(self, keep_hours: int = 168) -> int:
        return self.macro.prune_macro_snapshots(keep_hours)

    # ── persistent agent memory (facade → macro repo) ─────────────────

    def write_memory_block(self, block_name: str, content: str) -> None:
        return self.macro.write_memory_block(block_name, content)

    def read_memory_block(self, block_name: str) -> str | None:
        return self.macro.read_memory_block(block_name)
