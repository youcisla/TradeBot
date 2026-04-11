"""Retry decorator for transient psycopg2 operational errors."""

from __future__ import annotations

import functools
import logging
import time as _time

import psycopg2
import psycopg2.pool

logger = logging.getLogger(__name__)


def with_retry(max_retries: int = 3, base_delay: float = 0.5):
    """Retry decorator for transient psycopg2 operational errors.

    Retries up to *max_retries* times with exponential backoff (base_delay × 2^attempt).
    Logs each retry attempt at WARNING level.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "DB retry %d/%d for %s after %.1fs: %s",
                            attempt + 1, max_retries, fn.__name__, delay, e,
                        )
                        _time.sleep(delay)
                    else:
                        logger.error(
                            "DB retry exhausted for %s: %s", fn.__name__, e,
                        )
            raise last_exc
        return wrapper
    return decorator
