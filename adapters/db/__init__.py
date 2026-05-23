"""Adapters — DB layer."""

from adapters.db.pool import ConnectionPool
from adapters.db.retry import with_retry
from adapters.db.schema import (
    _ALL_TABLES,
    _SCHEMA_MIGRATIONS,
    _INIT_BOT_STATUS,
    _CREATE_INDEXES,
    _CREATE_TRADE_THESES_INDEXES,
)
from adapters.db.db import Database
from adapters.db.trade_repo import TradeRepo
from adapters.db.event_repo import EventRepo
from adapters.db.status_repo import StatusRepo
from adapters.db.learning_repo import LearningRepo
from adapters.db.broker_repo import BrokerRepo
from adapters.db.user_repo import UserRepo
from adapters.db.signal_repo import SignalRepo
from adapters.db.social_repo import SocialRepo
from adapters.db.macro_repo import MacroRepo

__all__ = [
    "ConnectionPool",
    "with_retry",
    "_ALL_TABLES",
    "_SCHEMA_MIGRATIONS",
    "_INIT_BOT_STATUS",
    "_CREATE_INDEXES",
    "_CREATE_TRADE_THESES_INDEXES",
    "Database",
    "TradeRepo",
    "EventRepo",
    "StatusRepo",
    "LearningRepo",
    "BrokerRepo",
    "UserRepo",
    "SignalRepo",
    "SocialRepo",
    "MacroRepo",
]