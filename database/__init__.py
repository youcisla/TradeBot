"""Database package — facade + repositories.

Preferred import for new code:
    from database.db import Database

Repository sub-objects (new internal API — use instead of adding to Database facade):
    from database.trade_repo import TradeRepo
    from database.event_repo import EventRepo
    from database.status_repo import StatusRepo
    from database.learning_repo import LearningRepo
    from database.broker_repo import BrokerRepo
"""

from database.db import Database

__all__ = [
    "Database",
    # Repositories (new code should use db.<repo> instead)
    "TradeRepo",
    "EventRepo",
    "StatusRepo",
    "LearningRepo",
    "BrokerRepo",
]
