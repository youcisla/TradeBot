"""Tests for dynamic strategy plugin loading."""

from __future__ import annotations

from unittest.mock import patch

from strategies.base_strategy import BaseStrategy
from strategies.plugin_loader import load_strategy_plugins


class DummyPluginStrategy(BaseStrategy):
    name = "dummy_plugin"

    def detect(self, context):
        return None

    def calculate_sl(self, context, direction: str) -> float:
        return 0.0

    def calculate_tps(self, context, entry: float, sl: float, direction: str):
        return (0.0, 0.0, 0.0)


def test_load_strategy_plugins_empty() -> None:
    with patch("strategies.plugin_loader.settings") as mock_settings:
        mock_settings.STRATEGY_PLUGINS = ()
        mock_settings.STRATEGY_PLUGIN_FAIL_FAST = False
        loaded = load_strategy_plugins(db=None, broker=None)
    assert loaded == []


def test_load_strategy_plugins_success() -> None:
    dotted = "tests.test_strategy_plugin_loader.DummyPluginStrategy"
    with patch("strategies.plugin_loader.settings") as mock_settings:
        mock_settings.STRATEGY_PLUGINS = (dotted,)
        mock_settings.STRATEGY_PLUGIN_FAIL_FAST = False
        loaded = load_strategy_plugins(db=None, broker=None)

    assert len(loaded) == 1
    assert isinstance(loaded[0], DummyPluginStrategy)


def test_load_strategy_plugins_non_fail_fast_skips_bad() -> None:
    with patch("strategies.plugin_loader.settings") as mock_settings:
        mock_settings.STRATEGY_PLUGINS = ("bad.path.DoesNotExist",)
        mock_settings.STRATEGY_PLUGIN_FAIL_FAST = False
        loaded = load_strategy_plugins(db=None, broker=None)

    assert loaded == []
