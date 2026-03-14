
import threading
import time
from collections import defaultdict
from typing import Optional

class SymbolEventTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = defaultdict(lambda: defaultdict(float))  # {symbol: {event_type: timestamp}}

    def update(self, symbol: str, event_type: str, timestamp: Optional[float] = None):
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            self.data[symbol][event_type] = float(timestamp)  # Ensure always float

    def get(self, symbol: str, event_type: str) -> float:
        with self.lock:
            return float(self.data[symbol].get(event_type, 0.0))

    def get_all(self, symbol: str) -> dict:
        with self.lock:
            return dict(self.data[symbol])

    def get_last_event(self, symbol: str) -> tuple[str, float]:
        with self.lock:
            if not self.data[symbol]:
                return "", 0.0  # Always return a float
            event, ts = max(self.data[symbol].items(), key=lambda x: x[1])
            return event, float(ts)

    def as_dict(self):
        with self.lock:
            return {s: dict(e) for s, e in self.data.items()}
