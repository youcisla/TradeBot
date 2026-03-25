"""Tests for CrucixClient and MacroContext."""

import json
from unittest.mock import MagicMock, patch

import pytest

from filters.crucix_client import (
    CrucixClient,
    MacroContext,
    TIER_CLEAR,
    TIER_ROUTINE,
    TIER_PRIORITY,
    TIER_FLASH,
)


@pytest.fixture
def client() -> CrucixClient:
    return CrucixClient(base_url="http://localhost:9999", cache_ttl_seconds=0)


# ── MacroContext helpers ──────────────────────────────────────────────────────

def test_macro_context_defaults() -> None:
    ctx = MacroContext()
    assert ctx.risk_tier == TIER_CLEAR
    assert ctx.crucix_available is False
    assert ctx.lot_scale_factor == 1.0
    assert ctx.is_blackout is False


def test_lot_scale_factor_by_tier() -> None:
    assert MacroContext(risk_tier=TIER_FLASH).lot_scale_factor == 0.0
    assert MacroContext(risk_tier=TIER_PRIORITY).lot_scale_factor == 0.5
    assert MacroContext(risk_tier=TIER_ROUTINE).lot_scale_factor == 0.75
    assert MacroContext(risk_tier=TIER_CLEAR).lot_scale_factor == 1.0


def test_is_blackout_flash_only() -> None:
    assert MacroContext(risk_tier=TIER_FLASH).is_blackout is True
    assert MacroContext(risk_tier=TIER_PRIORITY).is_blackout is False


def test_is_stale() -> None:
    assert MacroContext(last_sweep_age_minutes=25).is_stale is True
    assert MacroContext(last_sweep_age_minutes=10).is_stale is False


def test_confidence_modifier_vix_high_sell() -> None:
    ctx = MacroContext(vix=35)
    assert ctx.confidence_modifier("SELL") > 1.0


def test_confidence_modifier_vix_high_buy() -> None:
    ctx = MacroContext(vix=35)
    assert ctx.confidence_modifier("BUY") < 1.0


def test_confidence_modifier_flash_zeroes() -> None:
    ctx = MacroContext(risk_tier=TIER_FLASH, vix=10)
    assert ctx.confidence_modifier("BUY") == 0.0
    assert ctx.confidence_modifier("SELL") == 0.0


def test_confidence_modifier_inverted_curve() -> None:
    ctx = MacroContext(yield_curve_inverted=True)
    assert ctx.confidence_modifier("SELL") > ctx.confidence_modifier("BUY")


# ── CrucixClient._parse ───────────────────────────────────────────────────────

def test_parse_empty_dict(client: CrucixClient) -> None:
    ctx = client._parse({})
    assert ctx.crucix_available is True
    assert ctx.risk_tier == TIER_CLEAR


def test_parse_flash_alert(client: CrucixClient) -> None:
    raw = {"alerts": [{"tier": "FLASH", "title": "Major escalation"}]}
    ctx = client._parse(raw)
    assert ctx.risk_tier == TIER_FLASH
    assert "Major escalation" in ctx.active_flash_alerts


def test_parse_priority_alert(client: CrucixClient) -> None:
    raw = {"alerts": [{"tier": "PRIORITY", "title": "Fed hike surprise"}]}
    ctx = client._parse(raw)
    assert ctx.risk_tier == TIER_PRIORITY


def test_parse_clear_when_no_alerts(client: CrucixClient) -> None:
    raw = {"alerts": []}
    ctx = client._parse(raw)
    assert ctx.risk_tier == TIER_CLEAR


def test_parse_inverted_yield_curve(client: CrucixClient) -> None:
    raw = {"economic": {"yieldCurveSpread": -0.5}}
    ctx = client._parse(raw)
    assert ctx.yield_curve_inverted is True


def test_parse_normal_yield_curve(client: CrucixClient) -> None:
    raw = {"economic": {"yieldCurveSpread": 0.8}}
    ctx = client._parse(raw)
    assert ctx.yield_curve_inverted is False


def test_parse_vix_from_market(client: CrucixClient) -> None:
    raw = {"market": {"vix": 28.5}}
    ctx = client._parse(raw)
    assert abs(ctx.vix - 28.5) < 1e-5


# ── CrucixClient.get_context — unavailable server ────────────────────────────

def test_get_context_returns_safe_default_on_error(client: CrucixClient) -> None:
    with patch.object(client, "_fetch_data", side_effect=ConnectionRefusedError("refused")):
        ctx = client.get_context()
    assert isinstance(ctx, MacroContext)
    assert ctx.crucix_available is False
    assert ctx.risk_tier == TIER_CLEAR


def test_get_context_caches_result(client: CrucixClient) -> None:
    raw = {"alerts": [{"tier": "ROUTINE", "title": "minor"}]}
    client._cache_ttl = 9999  # freeze cache
    with patch.object(client, "_fetch_data", return_value=raw):
        ctx1 = client.get_context()
        ctx2 = client.get_context()
    assert ctx1 is ctx2  # same object returned from cache
