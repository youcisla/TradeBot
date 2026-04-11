"""Broker, symbol-faults, and ICT repository — extracted from database/db.py."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class BrokerRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── broker accounts ──────────────────────────────────────────────────

    def get_broker_accounts(self, user_id: int | None = None) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if user_id:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user_id,),
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts ORDER BY created_at DESC"""
                    )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def get_active_broker_account(self) -> dict | None:
        from utils.crypto import decrypt

        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM broker_accounts WHERE is_active = TRUE LIMIT 1"
                )
                row = cur.fetchone()
                if not row:
                    return None
                result = dict(row)
                result["password"] = decrypt(result["password"])
                return result
        finally:
            self._put(conn)

    def add_broker_account(
        self,
        name: str,
        account_number: str,
        password: str,
        server: str,
        is_demo: bool = True,
        user_id: int | None = None,
    ) -> int:
        from utils.crypto import encrypt

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO broker_accounts
                           (user_id, name, account_number, password, server, is_demo)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           RETURNING id""",
                        (user_id, name, account_number,
                         encrypt(password), server, is_demo),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def update_broker_account(
        self,
        account_id: int,
        name: str,
        account_number: str,
        password: str | None,
        server: str,
        is_demo: bool,
    ) -> None:
        from utils.crypto import encrypt

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if password:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s, password=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, encrypt(password),
                             server, is_demo, account_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, server, is_demo, account_id),
                        )
        finally:
            self._put(conn)

    def delete_broker_account(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM broker_accounts WHERE id = %s",
                                (account_id,))
        finally:
            self._put(conn)

    def activate_broker_account(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE broker_accounts SET is_active = FALSE")
                    cur.execute(
                        "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put(conn)

    def mark_broker_connected(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE broker_accounts SET last_connected = NOW() WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put(conn)

    # ── symbol faults ─────────────────────────────────────────────────────

    def load_symbol_faults(self) -> dict[str, dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT symbol, fail_count, disabled_until FROM symbol_fault")
                return {r["symbol"]: {"fail_count": r["fail_count"],
                                      "disabled_until": r["disabled_until"]}
                        for r in cur.fetchall()}
        finally:
            self._put(conn)

    def save_symbol_fault(
        self,
        symbol: str,
        fail_count: int,
        disabled_until: datetime | None,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if fail_count == 0 and disabled_until is None:
                        cur.execute(
                            "DELETE FROM symbol_fault WHERE symbol = %s", (symbol,))
                    else:
                        cur.execute(
                            """INSERT INTO symbol_fault (symbol, fail_count, disabled_until)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (symbol) DO UPDATE SET
                                   fail_count = EXCLUDED.fail_count,
                                   disabled_until = EXCLUDED.disabled_until""",
                            (symbol, fail_count, disabled_until),
                        )
        finally:
            self._put(conn)

    # ── ICT setups ───────────────────────────────────────────────────────

    def save_ict_setup(self, setup: dict) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO ict_setups
                           (symbol, direction, model, entry_price, stop_loss,
                            take_profit_1, take_profit_2, take_profit_3,
                            confidence, htf_bias, htf_regime, premium_discount,
                            entry_zone, reason, confluences, missing, session,
                            executed, trade_id)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            setup.get("symbol"),
                            setup.get("direction"),
                            setup.get("model"),
                            setup.get("entry_price"),
                            setup.get("stop_loss"),
                            setup.get("take_profit_1"),
                            setup.get("take_profit_2"),
                            setup.get("take_profit_3"),
                            setup.get("confidence"),
                            setup.get("htf_bias", ""),
                            setup.get("htf_regime", ""),
                            setup.get("premium_discount", ""),
                            setup.get("entry_zone", ""),
                            setup.get("reason", ""),
                            json.dumps(setup.get("confluences", {})),
                            setup.get("missing", []),
                            setup.get("session", ""),
                            setup.get("executed", False),
                            setup.get("trade_id"),
                        ),
                    )
        finally:
            self._put(conn)

    # ── trade theses ─────────────────────────────────────────────────────

    def save_trade_thesis(
        self,
        *,
        symbol: str,
        direction: str = "",
        stage: str = "IDEA",
        trade_id: str | None = None,
        entry_price: float | None = None,
        sl_price: float | None = None,
        tp_price: float | None = None,
        rr_ratio: float | None = None,
        bull_case: str = "",
        bear_case: str = "",
        entry_reason: str = "",
        notes: str = "",
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO trade_theses
                           (trade_id, symbol, direction, stage,
                            entry_price, sl_price, tp_price, rr_ratio,
                            bull_case, bear_case, entry_reason, notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (trade_id, symbol, direction, stage,
                         entry_price, sl_price, tp_price, rr_ratio,
                         bull_case, bear_case, entry_reason, notes),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def get_trade_thesis(self, trade_id: str) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM trade_theses
                       WHERE trade_id = %s
                       ORDER BY created_at DESC
                       LIMIT 1""",
                    (trade_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def update_trade_outcome(
        self,
        trade_id: str,
        *,
        actual_outcome: str,
        mae_pips: float | None = None,
        mfe_pips: float | None = None,
        notes: str = "",
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE trade_theses
                           SET stage          = 'CLOSED',
                               actual_outcome = %s,
                               mae_pips       = %s,
                               mfe_pips       = %s,
                               notes          = CASE WHEN %s = '' THEN notes ELSE %s END,
                               closed_at      = NOW()
                           WHERE trade_id = %s""",
                        (actual_outcome, mae_pips, mfe_pips,
                         notes, notes, trade_id),
                    )
        finally:
            self._put(conn)

    # ── dashboard users ──────────────────────────────────────────────────

    def get_user_by_username(self, username: str) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM dashboard_users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def get_user_by_id(self, user_id: int) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def create_user(self, username: str, password_hash: str) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO dashboard_users (username, password_hash)
                           VALUES (%s, %s) RETURNING id""",
                        (username, password_hash),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE dashboard_users SET password_hash = %s WHERE id = %s",
                        (password_hash, user_id),
                    )
        finally:
            self._put(conn)

    def get_all_users(self) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users ORDER BY created_at"
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def user_count(self) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dashboard_users")
                return cur.fetchone()[0]
        finally:
            self._put(conn)

    # ── signals ────────────────────────────────────────────────────────────

    def save_signal(
        self,
        *,
        signal_intent: str,
        signal_type: str,
        strategy: str,
        symbol: str = "",
        direction: str = "",
        entry_price: float = 0.0,
        stop_loss: float = 0.0,
        take_profit_1: float = 0.0,
        confidence: float = 0.5,
        reason: str = "",
        bull_case: str = "",
        bear_case: str = "",
        author: str = "bot",
        tags: list[str] | None = None,
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO signals
                           (signal_intent, signal_type, strategy, symbol, direction,
                            entry_price, stop_loss, take_profit_1, confidence,
                            reason, bull_case, bear_case, author, tags)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (
                            signal_intent, signal_type, strategy, symbol, direction,
                            entry_price, stop_loss, take_profit_1, confidence,
                            reason, bull_case, bear_case, author,
                            tags or [],
                        ),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def get_signals(
        self,
        signal_intent: str | None = None,
        signal_type: str | None = None,
        strategy: str | None = None,
        author: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = []
                params: list = []
                if signal_intent:
                    conditions.append("signal_intent = %s")
                    params.append(signal_intent)
                if signal_type:
                    conditions.append("signal_type = %s")
                    params.append(signal_type)
                if strategy:
                    conditions.append("strategy = %s")
                    params.append(strategy)
                if author:
                    conditions.append("author = %s")
                    params.append(author)
                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
                params.append(max(1, limit))
                cur.execute(
                    f"""SELECT * FROM signals
                        {where}
                        ORDER BY created_at DESC
                        LIMIT %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def mark_signal_points_awarded(self, signal_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE signals SET points_awarded = TRUE WHERE id = %s",
                        (signal_id,),
                    )
        finally:
            self._put(conn)

    # ── agent reputation ─────────────────────────────────────────────────

    def get_agent_reputation(self, agent: str) -> dict:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM agent_reputation WHERE agent = %s",
                    (agent,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                # Create default record on first access
                cur.execute(
                    "INSERT INTO agent_reputation (agent) VALUES (%s) ON CONFLICT (agent) DO NOTHING",
                    (agent,),
                )
                cur.execute(
                    "SELECT * FROM agent_reputation WHERE agent = %s",
                    (agent,),
                )
                row = cur.fetchone()
                return dict(row) if row else {
                    "agent": agent, "total_signals": 0, "adopted_signals": 0,
                    "total_points": 0, "win_streak": 0, "last_score": 0,
                    "reputation_score": 0.5,
                }
        finally:
            self._put(conn)

    def bump_agent_reputation(
        self,
        agent: str,
        *,
        adopted: bool = False,
        points_delta: int = 0,
        score_delta: int = 0,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if adopted:
                        cur.execute(
                            """INSERT INTO agent_reputation
                               (agent, total_signals, adopted_signals, total_points,
                                last_score, updated_at)
                               VALUES (%s, 1, 1, %s, %s, NOW())
                               ON CONFLICT (agent) DO UPDATE SET
                                   total_signals  = agent_reputation.total_signals + 1,
                                   adopted_signals = agent_reputation.adopted_signals + 1,
                                   total_points    = agent_reputation.total_points + %s,
                                   last_score      = %s,
                                   win_streak      = agent_reputation.win_streak + 1,
                                   updated_at      = NOW()""",
                            (agent, points_delta, score_delta, points_delta, score_delta),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO agent_reputation
                               (agent, total_signals, total_points, last_score, updated_at)
                               VALUES (%s, 1, %s, %s, NOW())
                               ON CONFLICT (agent) DO UPDATE SET
                                   total_signals  = agent_reputation.total_signals + 1,
                                   total_points   = agent_reputation.total_points + %s,
                                   last_score     = %s,
                                   updated_at     = NOW()""",
                            (agent, points_delta, score_delta, points_delta, score_delta),
                        )
        finally:
            self._put(conn)

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT agent, total_signals, adopted_signals,
                              total_points, win_streak, reputation_score, updated_at
                       FROM agent_reputation
                       ORDER BY total_points DESC
                       LIMIT %s""",
                    (max(1, limit),),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    # ── subscriptions (copy-trading) ──────────────────────────────────────

    def save_subscription(
        self,
        follower_id: str,
        leader_id: str,
        leader_strategy: str = "all",
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO subscriptions (follower_id, leader_id, leader_strategy)
                           VALUES (%s, %s, %s)
                           ON CONFLICT DO NOTHING
                           RETURNING id""",
                        (follower_id, leader_id, leader_strategy),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        finally:
            self._put(conn)

    def get_subscriptions(
        self,
        follower_id: str | None = None,
        leader_id: str | None = None,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = []
                params: list = []
                if follower_id:
                    conditions.append("follower_id = %s")
                    params.append(follower_id)
                if leader_id:
                    conditions.append("leader_id = %s")
                    params.append(leader_id)
                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
                cur.execute(
                    f"""SELECT * FROM subscriptions {where}
                        ORDER BY created_at DESC""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def delete_subscription(self, follower_id: str, leader_id: str) -> bool:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """DELETE FROM subscriptions
                           WHERE follower_id = %s AND leader_id = %s""",
                        (follower_id, leader_id),
                    )
                    return cur.rowcount > 0
        finally:
            self._put(conn)

    def get_followers(self, leader_id: str) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM subscriptions
                       WHERE leader_id = %s AND status = 'ACTIVE'
                       ORDER BY created_at DESC""",
                    (leader_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    # ── macro snapshots ───────────────────────────────────────────────────

    def save_macro_snapshot(self, snapshot_data: dict) -> None:
        from datetime import UTC

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO macro_snapshots
                           (snapshot_json, risk_tier, yield_inverted, usd_strength, gdelt_tone, fetched_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            json.dumps(snapshot_data),
                            snapshot_data.get("risk_tier", "normal"),
                            snapshot_data.get("yield_curve_inverted", False),
                            snapshot_data.get("usd_strength", "neutral"),
                            snapshot_data.get("gdelt_risk_tone"),
                            datetime.now(UTC),
                        ),
                    )
        finally:
            self._put(conn)

    def get_macro_snapshots(
        self,
        lookback_hours: int = 24,
        risk_tier: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = [
                    "fetched_at >= NOW() - (%s || ' hours')::interval"
                ]
                params: list = [str(max(1, lookback_hours))]
                if risk_tier:
                    conditions.append("risk_tier = %s")
                    params.append(risk_tier)
                params.append(max(1, limit))
                cur.execute(
                    f"""SELECT id, snapshot_json, risk_tier, yield_inverted,
                              usd_strength, gdelt_tone, fetched_at
                       FROM macro_snapshots
                       WHERE {' AND '.join(conditions)}
                       ORDER BY fetched_at DESC
                       LIMIT %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def prune_macro_snapshots(self, keep_hours: int = 168) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """DELETE FROM macro_snapshots
                           WHERE fetched_at < NOW() - (%s || ' hours')::interval""",
                        (str(max(1, keep_hours)),),
                    )
                    return cur.rowcount
        finally:
            self._put(conn)

    # ── persistent agent memory ──────────────────────────────────────────

    def write_memory_block(self, block_name: str, content: str) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO bot_memory (block_name, content, updated_at)
                           VALUES (%s, %s, NOW())
                           ON CONFLICT (block_name)
                           DO UPDATE SET content = EXCLUDED.content,
                                         updated_at = NOW()""",
                        (block_name, content),
                    )
        finally:
            self._put(conn)

    def read_memory_block(self, block_name: str) -> str | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM bot_memory WHERE block_name = %s",
                    (block_name,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self._put(conn)
