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

        # first_pool serves the stale conn; second_pool (via _reconnect) serves good
        first_pool = _make_pool([stale])
        second_pool = _make_pool([good])

        # _reconnect() uses SimpleConnectionPool — patch that to return second_pool
        with patch("psycopg2.pool.SimpleConnectionPool", return_value=second_pool):
            from database.db import Database
            db = Database.__new__(Database)
            db._dsn = "postgresql://test"
            db._pool = first_pool  # bypass _connect(); set pool directly

            conn = db._get_conn()
            assert conn is good

    def test_reconnect_creates_new_pool(self):
        """_reconnect() must tear down the old pool and build a fresh one."""
        good = _make_good_conn()
        new_pool = _make_pool([good])

        with patch("psycopg2.pool.SimpleConnectionPool", return_value=new_pool) as mock_cls:
            from database.db import Database
            db = Database.__new__(Database)
            db._dsn = "postgresql://test"
            old_pool = MagicMock()
            old_pool.closeall = MagicMock()
            db._pool = old_pool  # bypass _connect(); set pool directly

            db._reconnect()

            # _reconnect() must have built a new pool and closed the old one
            assert mock_cls.call_count >= 1
            old_pool.closeall.assert_called_once()

    def test_get_conn_returns_fresh_after_reconnect(self):
        """After reconnect, _get_conn must return a working connection."""
        stale = _make_stale_conn()
        fresh = _make_good_conn()

        first_pool = _make_pool([stale])
        second_pool = _make_pool([fresh])

        with patch("psycopg2.pool.SimpleConnectionPool", return_value=second_pool):
            from database.db import Database
            db = Database.__new__(Database)
            db._dsn = "postgresql://test"
            db._pool = first_pool  # bypass _connect(); set pool directly

            conn = db._get_conn()
            assert conn is fresh

    def test_good_connection_not_reconnected(self):
        """A healthy connection must not trigger any pool rebuild."""
        good = _make_good_conn()
        pool = _make_pool([good])

        with patch("psycopg2.pool.SimpleConnectionPool") as mock_cls:
            from database.db import Database
            db = Database.__new__(Database)
            db._dsn = "postgresql://test"
            db._pool = pool  # bypass _connect(); set pool directly

            call_count_before = mock_cls.call_count
            conn = db._get_conn()
            call_count_after = mock_cls.call_count

            assert conn is good
            # No pool rebuild should have occurred
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
