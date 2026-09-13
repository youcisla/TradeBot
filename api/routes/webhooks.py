"""TradingView (and generic) webhook ingestion.

Point a TradingView alert's webhook URL at::

    POST http://<host>:8001/api/webhooks/tradingview

and set the alert message body to JSON::

    {
      "secret": "<TRADINGVIEW_WEBHOOK_SECRET>",
      "symbol": "EURUSD",
      "side": "buy",
      "entry": 1.1050,
      "sl": 1.1000,
      "tp1": 1.1150
    }

TradingView posts the alert message verbatim, so any JSON you can type in the
alert box arrives here unchanged.

**Security.**  This endpoint accepts instructions from the public internet, so:

* it is authenticated by a shared secret compared in constant time;
* if no secret is configured it refuses everything — fail closed, never open;
* it is rate limited, so one misconfigured alert cannot flood the pipeline;
* it **never executes an order**.  Accepted alerts are queued and travel the
  normal ``scan → rank → guard → execute`` path, so `GuardPipeline`, the risk
  caps and the daily-loss limit apply exactly as they do to internal signals.
"""

from __future__ import annotations

import hmac
import logging
import os
from collections import deque
from time import monotonic
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status

from autonomy.intake import INBOX, ExternalSignal

logger = logging.getLogger(__name__)
router = APIRouter()

RATE_LIMIT = 30            # accepted alerts
RATE_WINDOW_S = 60.0
_recent: deque[float] = deque()


def _secret() -> str:
    return os.environ.get("TRADINGVIEW_WEBHOOK_SECRET", "").strip()


def _rate_limited() -> bool:
    now = monotonic()
    while _recent and now - _recent[0] > RATE_WINDOW_S:
        _recent.popleft()
    return len(_recent) >= RATE_LIMIT


def _num(payload: dict[str, Any], *keys: str) -> float:
    """First present, parseable numeric value among *keys*, else 0.0."""
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def _parse(payload: dict[str, Any]) -> ExternalSignal:
    """Normalise a provider payload into an ExternalSignal.

    Accepts the common aliases so a user does not have to guess which spelling
    this endpoint wants: ``side``/``direction``, ``sl``/``stop_loss``,
    ``tp``/``tp1``/``take_profit``.
    """
    direction = str(payload.get("side") or payload.get("direction") or "").upper().strip()
    if direction in ("LONG", "BUY"):
        direction = "BUY"
    elif direction in ("SHORT", "SELL"):
        direction = "SELL"

    return ExternalSignal(
        source="tradingview",
        symbol=str(payload.get("symbol") or "").upper().strip(),
        direction=direction,
        entry_price=_num(payload, "entry", "entry_price", "price"),
        stop_loss=_num(payload, "sl", "stop_loss", "stop"),
        take_profit_1=_num(payload, "tp1", "take_profit_1", "tp", "take_profit"),
        take_profit_2=_num(payload, "tp2", "take_profit_2"),
        take_profit_3=_num(payload, "tp3", "take_profit_3"),
        comment=str(payload.get("comment") or payload.get("strategy") or "tradingview")[:29],
    )


@router.post("/tradingview", status_code=status.HTTP_202_ACCEPTED)
def tradingview_alert(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Accept a TradingView alert as a candidate signal."""
    expected = _secret()
    if not expected:
        # No secret configured means this endpoint cannot authenticate anyone.
        # Refusing is the only safe behaviour.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TRADINGVIEW_WEBHOOK_SECRET is not configured; webhook intake disabled",
        )

    supplied = str(payload.get("secret") or "")
    if not hmac.compare_digest(supplied, expected):
        logger.warning("TradingView webhook rejected: bad secret")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid secret")

    if _rate_limited():
        logger.warning("TradingView webhook rate limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"rate limit {RATE_LIMIT}/{RATE_WINDOW_S:.0f}s exceeded",
        )

    signal = _parse(payload)
    ok, reason = signal.validate()
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)

    _recent.append(monotonic())
    INBOX.submit(signal)

    # 202, not 200: the alert is accepted for evaluation, not executed.  Say so
    # plainly so the response cannot be mistaken for a fill confirmation.
    return {
        "status": "queued",
        "note": "candidate signal only — subject to guards, risk limits and ranking",
        "symbol": signal.symbol,
        "direction": signal.direction,
        "pending": INBOX.pending(),
    }


@router.get("/health")
def intake_health() -> dict[str, Any]:
    """How much external signal is waiting, and whether intake is armed."""
    return {
        "secret_configured": bool(_secret()),
        "pending": INBOX.pending(),
        "dropped": INBOX.dropped(),
        "rate_limit": f"{RATE_LIMIT}/{RATE_WINDOW_S:.0f}s",
    }
