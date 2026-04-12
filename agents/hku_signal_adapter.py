"""HKU marketplace signal adapter.

Converts raw HKU API signal payloads into our internal Signal format.

HKU signals carry a 0-100 integer confidence.  We apply a discount factor
(default 0.80) so external signals are never fully trusted until our own
LGBM filter has validated them through the pipeline.  The source field is set
to "hku" so the dashboard and rank phase can distinguish them.
"""

from __future__ import annotations

from typing import Any

from models.signal import Signal, SignalIntent


def adapt_hku_signal(
    hku_payload: dict[str, Any],
    discount_factor: float = 0.80,
) -> Signal:
    """Convert an HKU marketplace signal dict to an internal Signal.

    Args:
        hku_payload:     Raw dict from HKU API (keys: signal_id, agent_id,
                         symbol, direction, price, sl, tp, confidence, action, content)
        discount_factor: Scales HKU's 0-100 confidence down before converting to 0-1.
                         Default 0.80 means HKU signals top out at 80% confidence.

    Returns:
        A Signal instance with source="hku" and strategy="hku_external".
    """
    hku_conf = hku_payload.get("confidence", 50)
    internal_conf = min(1.0, (hku_conf / 100.0) * discount_factor)

    direction = str(hku_payload.get("direction", "")).upper()
    if direction not in ("BUY", "SELL"):
        direction = "BUY" if hku_payload.get("action", "") in ("buy", "long") else "SELL"

    return Signal(
        strategy="hku_external",
        symbol=str(hku_payload.get("symbol", "")),
        direction=direction,
        entry_price=float(hku_payload.get("price", 0.0)),
        stop_loss=float(hku_payload.get("sl", 0.0)),
        take_profit_1=float(hku_payload.get("tp", 0.0)),
        confidence=internal_conf,
        signal_intent=SignalIntent.STRATEGY,  # external signals treated as STRATEGY
        source="hku",
        metadata={
            "hku_signal_id": hku_payload.get("signal_id") or hku_payload.get("id", ""),
            "hku_agent_id": hku_payload.get("agent_id", ""),
            "hku_action": hku_payload.get("action", ""),
        },
        reason=hku_payload.get("content", ""),
    )
