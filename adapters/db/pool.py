"""Database connection pool — extracted from database/db.py."""

from __future__ import annotations

import logging

import psycopg2
import psycopg2.pool

logger = logging.getLogger(__name__)


class ConnectionPool:
    """PostgreSQL connection pool wrapper with auto-reconnect."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: psycopg2.pool.ThreadedConnectionPool | None = None
        self._connect()

    def _connect(self) -> None:
        if self._pool:
            try:
                self._pool.closeall()
            except Exception:
                pass
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=8,
            dsn=self._dsn,
            options="-c statement_timeout=15000",
        )
        logger.info("PostgreSQL connection pool created")

    def _get_conn(self) -> psycopg2.extensions.connection:
        """Get a connection from the pool, reconnecting if uninitialized."""
        if self._pool is None:
            logger.warning("DB pool was None — reconnecting")
            self._connect()
        conn = self._pool.getconn()
        return conn

    def _put_conn(self, conn: psycopg2.extensions.connection) -> None:
        """Return connection to the pool, validating with SELECT 1 on the way back."""
        if self._pool is None:
            return
        try:
            if conn.closed or conn.status != psycopg2.extensions.STATUS_READY:
                self._pool.putconn(conn, close=True)
                return
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                self._pool.putconn(conn, close=True)
                return
        except Exception:
            pass
        self._pool.putconn(conn)

    def _reconnect(self) -> None:
        """Tear down the pool and create a fresh one."""
        logger.info("Rebuilding DB connection pool…")
        try:
            if self._pool:
                self._pool.closeall()
        except Exception:
            pass
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=8,
            dsn=self._dsn,
            options="-c statement_timeout=15000",
        )
        logger.info("DB connection pool rebuilt")

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._pool = None

    def get_conn(self) -> psycopg2.extensions.connection:
        return self._get_conn()

    def put_conn(self, conn: psycopg2.extensions.connection) -> None:
        self._put_conn(conn)