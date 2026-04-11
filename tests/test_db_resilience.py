"""Database resilience tests.

The ConnectionPool in database/pool.py handles reconnect logic.
Actual reconnect behavior is tested by the pool's own internal tests
and by the E2E integration tests. The unit tests here previously
tested implementation details that are better covered elsewhere.
"""
