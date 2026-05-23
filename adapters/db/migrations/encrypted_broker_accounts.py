"""Schema migration: add encrypted credential columns to broker_accounts.

Adds: profile_label, encrypted_password, salt, kdf_ops_limit, kdf_mem_limit_kib, kdf_parallelism

Existing rows (from old plaintext password column) are preserved as-is.
A Phase 2.7 one-time migration script will handle re-encrypting those credentials
with a new derived key — requiring the user to re-enter their MT5 password once.

Run via: python -m adapters.db.migrations.encrypted_broker_accounts
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

UP = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='encrypted_password') THEN
        ALTER TABLE broker_accounts ADD COLUMN encrypted_password TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='salt') THEN
        ALTER TABLE broker_accounts ADD COLUMN salt TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='profile_label') THEN
        ALTER TABLE broker_accounts ADD COLUMN profile_label TEXT DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='kdf_ops_limit') THEN
        ALTER TABLE broker_accounts ADD COLUMN kdf_ops_limit INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='kdf_mem_limit_kib') THEN
        ALTER TABLE broker_accounts ADD COLUMN kdf_mem_limit_kib INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='kdf_parallelism') THEN
        ALTER TABLE broker_accounts ADD COLUMN kdf_parallelism INTEGER;
    END IF;
END $$;
"""

DOWN = """
ALTER TABLE broker_accounts
    DROP COLUMN IF EXISTS encrypted_password,
    DROP COLUMN IF EXISTS salt,
    DROP COLUMN IF EXISTS profile_label,
    DROP COLUMN IF EXISTS kdf_ops_limit,
    DROP COLUMN IF EXISTS kdf_mem_limit_kib,
    DROP COLUMN IF EXISTS kdf_parallelism;
"""


def run_up(pool) -> None:
    from adapters.db.pool import ConnectionPool
    conn = pool.get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(UP)
        logger.info("Migration up: encrypted_broker_accounts applied")
    finally:
        pool.put_conn(conn)


def run_down(pool) -> None:
    from adapters.db.pool import ConnectionPool
    conn = pool.get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DOWN)
        logger.info("Migration down: encrypted_broker_accounts rolled back")
    finally:
        pool.put_conn(conn)


if __name__ == "__main__":
    import sys
    from config import settings
    from adapters.db.pool import ConnectionPool

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    pool = ConnectionPool(settings.DATABASE_URL)
    if len(sys.argv) > 1 and sys.argv[1] == "--down":
        run_down(pool)
    else:
        run_up(pool)
    pool.close()