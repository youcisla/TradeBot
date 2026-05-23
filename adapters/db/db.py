"""Database facade — migrated from database/db.py."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config import settings

from adapters.db.pool import ConnectionPool
from adapters.db.retry import with_retry
from adapters.db.schema import (
    _ALL_TABLES,
    _SCHEMA_MIGRATIONS,
    _INIT_BOT_STATUS,
    _CREATE_INDEXES,
    _CREATE_TRADE_THESES_INDEXES,
)

from adapters.db.trade_repo import TradeRepo
from adapters.db.event_repo import EventRepo
from adapters.db.status_repo import StatusRepo
from adapters.db.learning_repo import LearningRepo
from adapters.db.broker_repo import BrokerRepo
from adapters.db.user_repo import UserRepo
from adapters.db.signal_repo import SignalRepo
from adapters.db.social_repo import SocialRepo
from adapters.db.macro_repo import MacroRepo

if TYPE_CHECKING:
    import psycopg2

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL facade exposing all repository sub-objects."""

    def __init__(self) -> None:
        dsn = settings.database_url
        self._pool = ConnectionPool(dsn)
        self.trades = TradeRepo(self._pool)
        self.events = EventRepo(self._pool)
        self.status = StatusRepo(self._pool)
        self.learning = LearningRepo(self._pool)
        self.broker = BrokerRepo(self._pool)
        self.users = UserRepo(self._pool)
        self.signals = SignalRepo(self._pool)
        self.social = SocialRepo(self._pool)
        self.macro = MacroRepo(self._pool)

    def init_schema(self) -> None:
        """Run all CREATE TABLE statements and migrations."""
        conn = self._pool.get_conn()
        try:
            with conn.cursor() as cur:
                for table_ddl in _ALL_TABLES:
                    cur.execute(table_ddl)
                cur.execute(_INIT_BOT_STATUS)
                cur.execute(_CREATE_TRADE_THESES_INDEXES)
                for migration in _SCHEMA_MIGRATIONS:
                    cur.execute(migration)
                for index_ddl in _CREATE_INDEXES.split(";"):
                    index_ddl = index_ddl.strip()
                    if index_ddl:
                        cur.execute(index_ddl)
            conn.commit()
            logger.info("Database schema initialised")
        finally:
            self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def claim_pending_command(self) -> dict | None:
        return self.events.claim_pending_command()

    @with_retry(max_retries=3, base_delay=0.5)
    def claim_pending_confirmation(self) -> dict | None:
        return self.events.claim_pending_confirmation()

    @with_retry(max_retries=3, base_delay=0.5)
    def update_command_result(self, command_id: int, result: str, status: str = "done") -> None:
        self.events.update_command_result(command_id, result, status)

    @with_retry(max_retries=3, base_delay=0.5)
    def log_agent_event(
        self, agent: str, level: str, message: str, data: dict | None = None
    ) -> None:
        self.events.log_agent_event(agent, level, message, data)

    @with_retry(max_retries=3, base_delay=0.5)
    def log_signal(self, signal: dict) -> None:
        self.events.log_signal(signal)

    def close(self) -> None:
        self._pool.close()
