"""Database resilience tests.

Verifies that Database._get_conn() detects a stale connection, triggers
_reconnect(), and that subsequent operations succeed.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call
import psycopg2

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_good_conn():
    """Return a mock connection that passes the liveness check."""
    conn = MagicMock()
    conn.closed = False
    conn.status = psycopg2.extensions.STATUS_READY
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.execute = MagicMock()
    cur.fetchall = MagicMock(return_value=[])
    cur.fetchone = MagicMock(return_value=None)
    conn.cursor.return_value = cur
    return conn


def _make_stale_conn():
    """Return a mock connection whose liveness cursor.execute raises."""
    conn = MagicMock()
    conn.closed = False
    conn.status = psycopg2.extensions.STATUS_READY
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    # First execute (SELECT 1 liveness check) raises; subsequent ones succeed
    cur.execute.side_effect = [psycopg2.OperationalError("connection reset")]
    conn.cursor.return_value = cur
    return conn


def _make_pool(conn_sequence: list):
    """Return a mock pool that dishes out connections in sequence."""
    pool = MagicMock()
    pool.getconn.side_effect = conn_sequence
    pool.putconn = MagicMock()
    pool.closeall = MagicMock()
    return pool


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestConnectionResilience:
    def test_stale_connection_triggers_reconnect(self):
        """When the liveness check fails, _reconnect() must be called."""
        stale = _make_stale_conn()
        good = _make_good_conn()

        first_pool = _make_pool([stale, good])
        second_pool = _make_pool([good, good])   # after reconnect

        pool_sequence = [first_pool, second_pool]
        pool_call_idx = [0]

        def _fake_pool(*args, **kwargs):
            pool = pool_sequence[pool_call_idx[0]]
            pool_call_idx[0] = min(pool_call_idx[0] + 1, len(pool_sequence) - 1)
            return pool

        with patch("psycopg2.pool.SimpleConnectionPool", side_effect=_fake_pool):
            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = None
                db._connect()

                # Trigger a get that hits the stale path
                # _get_conn will call getconn, detect OperationalError, reconnect, call getconn again
                conn = db._get_conn()
                assert conn is good

    def test_reconnect_creates_new_pool(self):
        """_reconnect() must tear down the old pool and build a fresh one."""
        with patch("psycopg2.pool.SimpleConnectionPool") as mock_cls:
            good = _make_good_conn()
            pool = _make_pool([good])
            mock_cls.return_value = pool

            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = None
                db._connect()

                old_pool = db._pool
                db._reconnect()

                # Pool constructor called at least twice (initial + reconnect)
                assert mock_cls.call_count >= 2
                old_pool.closeall.assert_called_once()

    def test_get_conn_returns_fresh_after_reconnect(self):
        """After reconnect, _get_conn must return a working connection."""
        stale = _make_stale_conn()
        fresh = _make_good_conn()

        # Pools: first pool serves stale then fresh (for reconnect's getconn)
        first_pool = _make_pool([stale, fresh])
        second_pool = _make_pool([fresh])

        pools = [first_pool, second_pool]
        idx = [0]

        def _factory(*a, **kw):
            p = pools[min(idx[0], len(pools) - 1)]
            idx[0] += 1
            return p

        with patch("psycopg2.pool.SimpleConnectionPool", side_effect=_factory):
            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = None
                db._connect()

                conn = db._get_conn()
                assert conn is fresh

    def test_good_connection_not_reconnected(self):
        """A healthy connection must not trigger any pool rebuild."""
        good = _make_good_conn()
        pool = _make_pool([good])

        with patch("psycopg2.pool.SimpleConnectionPool", return_value=pool):
            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = None
                db._connect()

                call_count_before = psycopg2.pool.SimpleConnectionPool.call_count
                conn = db._get_conn()
                call_count_after = psycopg2.pool.SimpleConnectionPool.call_count

                assert conn is good
                # No additional pool creation
                assert call_count_after == call_count_before


class TestPutConn:
    def test_bad_connection_discarded(self):
        """A closed connection must be returned with close=True."""
        bad_conn = MagicMock()
        bad_conn.closed = True
        bad_conn.status = psycopg2.extensions.STATUS_READY

        pool = MagicMock()

        with patch("psycopg2.pool.SimpleConnectionPool", return_value=pool):
            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = pool

                db._put_conn(bad_conn)
                pool.putconn.assert_called_once_with(bad_conn, close=True)

    def test_good_connection_returned_normally(self):
        """A healthy connection must be returned without close=True."""
        good_conn = MagicMock()
        good_conn.closed = False
        good_conn.status = psycopg2.extensions.STATUS_READY

        pool = MagicMock()

        with patch("psycopg2.pool.SimpleConnectionPool", return_value=pool):
            with patch("database.db.settings") as mock_settings:
                mock_settings.DATABASE_URL = "postgresql://test"
                from database.db import Database
                db = Database.__new__(Database)
                db._dsn = "postgresql://test"
                db._pool = pool

                db._put_conn(good_conn)
                pool.putconn.assert_called_once_with(good_conn)
