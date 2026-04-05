"""Dynamic strategy plugin loading.

Loads strategy classes from dotted paths declared in STRATEGY_PLUGINS.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from typing import TYPE_CHECKING

from config import settings
from strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from broker.connector import BrokerConnector
    from database.db import Database

logger = logging.getLogger(__name__)


def _resolve_strategy_class(dotted_path: str) -> type[BaseStrategy]:
    """Resolve a strategy class from a dotted path."""
    module_name, sep, class_name = dotted_path.rpartition(".")
    if not sep:
        raise ValueError(f"Invalid strategy plugin path: {dotted_path}")

    module = importlib.import_module(module_name)
    candidate = getattr(module, class_name, None)
    if candidate is None:
        raise ValueError(f"Strategy class not found: {dotted_path}")
    if not inspect.isclass(candidate):
        raise ValueError(f"Strategy plugin target is not a class: {dotted_path}")
    if not issubclass(candidate, BaseStrategy):
        raise TypeError(f"Strategy plugin must inherit BaseStrategy: {dotted_path}")
    return candidate


def _instantiate_strategy(
    strategy_cls: type[BaseStrategy],
    db: Database | None,
    broker: BrokerConnector | None,
) -> BaseStrategy:
    """Instantiate strategy with best-effort dependency injection."""
    sig = inspect.signature(strategy_cls)
    kwargs: dict[str, object] = {}

    if "db" in sig.parameters:
        kwargs["db"] = db
    if "broker" in sig.parameters:
        kwargs["broker"] = broker

    return strategy_cls(**kwargs)


def load_strategy_plugins(
    db: Database | None = None,
    broker: BrokerConnector | None = None,
) -> list[BaseStrategy]:
    """Load and instantiate strategies declared in settings.STRATEGY_PLUGINS."""
    instances: list[BaseStrategy] = []

    for dotted_path in settings.STRATEGY_PLUGINS:
        try:
            strategy_cls = _resolve_strategy_class(dotted_path)
            strategy = _instantiate_strategy(strategy_cls, db=db, broker=broker)
            instances.append(strategy)
            logger.info("Loaded strategy plugin: %s", dotted_path)
        except Exception as exc:
            logger.error("Failed loading strategy plugin %s: %s", dotted_path, exc)
            if settings.STRATEGY_PLUGIN_FAIL_FAST:
                raise

    return instances
