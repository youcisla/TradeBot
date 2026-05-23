"""Crucix intelligence client — re-export from adapters/crucix/client.py.

Kept for backward compatibility. New code should import from
adapters.crucix.client directly.
"""

from adapters.crucix.client import (
    CrucixClient,
    MacroContext,
    CrucixScore,
    get_client,
    get_macro_context,
    score_crucix,
    TIER_CLEAR,
    TIER_ROUTINE,
    TIER_PRIORITY,
    TIER_FLASH,
)

__all__ = [
    "CrucixClient",
    "MacroContext",
    "CrucixScore",
    "get_client",
    "get_macro_context",
    "score_crucix",
    "TIER_CLEAR",
    "TIER_ROUTINE",
    "TIER_PRIORITY",
    "TIER_FLASH",
]
