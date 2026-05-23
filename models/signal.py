"""Backward-compatibility shim — redirects to core/domain/signal.py."""
from core.domain.signal import EntrySnapshot, Signal, SignalIntent

__all__ = ["EntrySnapshot", "Signal", "SignalIntent"]