"""External signal intake — TradingView alerts and other webhook sources.

The HTTP server runs in its own thread (see ``main.py``), so alerts cannot be
handed to the trading loop by direct call.  They land in this module's
thread-safe queue and the loop drains them at the top of each iteration.

**An alert is a suggestion, not a command.**  Nothing here places an order.
Each alert is normalised into a candidate signal that then travels the same
``scan → rank → guard → execute`` path as every internally generated signal, so
GuardPipeline, the risk caps, the daily-loss limit and the duplicate check all
apply unchanged.  Routing alerts straight to the executor would mean anyone who
learned the webhook URL could trade the account directly.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

# Bounded: a misconfigured alert firing every second must not grow without
# limit.  Dropping the oldest is correct — a stale alert is worthless anyway.
MAX_QUEUE = 200


@dataclass
class ExternalSignal:
    """A candidate signal from an outside source, awaiting pipeline admission."""

    source: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    comment: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def validate(self) -> tuple[bool, str]:
        """Reject anything that cannot become a sane trade.

        Deliberately strict: these values arrive from outside the system, so
        they are untrusted input at a trust boundary, not internal state.
        """
        if self.direction not in ("BUY", "SELL"):
            return False, f"direction must be BUY or SELL, got {self.direction!r}"
        if not self.symbol or not self.symbol.strip():
            return False, "symbol is empty"
        if self.entry_price <= 0:
            return False, "entry_price must be positive"

        if self.stop_loss > 0:
            if self.direction == "BUY" and self.stop_loss >= self.entry_price:
                return False, "BUY stop_loss must sit below entry_price"
            if self.direction == "SELL" and self.stop_loss <= self.entry_price:
                return False, "SELL stop_loss must sit above entry_price"

        for label, level in (
            ("take_profit_1", self.take_profit_1),
            ("take_profit_2", self.take_profit_2),
            ("take_profit_3", self.take_profit_3),
        ):
            if level <= 0:
                continue
            if self.direction == "BUY" and level <= self.entry_price:
                return False, f"{label} must sit above entry_price for a BUY"
            if self.direction == "SELL" and level >= self.entry_price:
                return False, f"{label} must sit below entry_price for a SELL"

        return True, ""


class SignalInbox:
    """Thread-safe bounded queue of external signals."""

    def __init__(self, maxlen: int = MAX_QUEUE) -> None:
        self._q: deque[ExternalSignal] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._dropped = 0

    def submit(self, signal: ExternalSignal) -> bool:
        ok, reason = signal.validate()
        if not ok:
            logger.warning("Intake rejected %s %s: %s", signal.source, signal.symbol, reason)
            return False
        with self._lock:
            if len(self._q) == self._q.maxlen:
                self._dropped += 1
                logger.warning(
                    "Intake queue full (%d) — dropped %d so far; is an alert misconfigured?",
                    self._q.maxlen, self._dropped,
                )
            self._q.append(signal)
        logger.info(
            "Intake accepted %s %s %s @ %.5f",
            signal.source, signal.direction, signal.symbol, signal.entry_price,
        )
        return True

    def drain(self, max_items: int = 20) -> list[ExternalSignal]:
        """Remove and return up to *max_items* signals, oldest first."""
        out: list[ExternalSignal] = []
        with self._lock:
            while self._q and len(out) < max_items:
                out.append(self._q.popleft())
        return out

    def pending(self) -> int:
        with self._lock:
            return len(self._q)

    def dropped(self) -> int:
        with self._lock:
            return self._dropped


# Process-wide inbox.  The HTTP thread writes, the trading loop reads.
INBOX = SignalInbox()


def _self_check() -> None:
    """Runnable check on the validation rules — this is a trust boundary."""
    box = SignalInbox(maxlen=3)

    good = ExternalSignal(
        source="tradingview", symbol="EURUSD", direction="BUY",
        entry_price=1.1050, stop_loss=1.1000, take_profit_1=1.1150,
    )
    assert box.submit(good) is True
    assert box.pending() == 1

    # A BUY whose stop sits above entry is nonsense and must be refused.
    assert box.submit(ExternalSignal(
        source="tradingview", symbol="EURUSD", direction="BUY",
        entry_price=1.1050, stop_loss=1.1100,
    )) is False, "invalid geometry must be rejected"

    # A BUY target below entry is likewise refused.
    assert box.submit(ExternalSignal(
        source="tradingview", symbol="EURUSD", direction="BUY",
        entry_price=1.1050, take_profit_1=1.1000,
    )) is False

    # An unknown direction is refused.
    assert box.submit(ExternalSignal(
        source="x", symbol="EURUSD", direction="LONG", entry_price=1.1,
    )) is False

    # Bounded: the oldest is dropped, the queue never grows past maxlen.
    for _ in range(5):
        box.submit(ExternalSignal(
            source="tradingview", symbol="GBPUSD", direction="SELL", entry_price=1.25,
        ))
    assert box.pending() == 3, box.pending()
    assert box.dropped() >= 2

    drained = box.drain(max_items=2)
    assert len(drained) == 2 and box.pending() == 1

    print("intake.py self-check: OK")


if __name__ == "__main__":
    _self_check()
