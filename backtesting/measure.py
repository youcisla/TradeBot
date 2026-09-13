"""Honest walk-forward measurement harness.

Replaces the harness in ``scripts/backtest.py``, which could not support a
conclusion about edge.  Its defects, and what this module does instead:

- H4 was built by grouping the whole H1 array and returning the tail, so a
  decision at bar *t* used bars after *t*.  ``AsOfStore`` slices every
  timeframe to bars at or before the decision timestamp.
- ``spread=0.0`` and no commission.  Real per-bar spread and commission are
  charged on every fill.
- A limit entry counted as filled even when price never returned to it.
  Entries must now be touched by a later bar.
- A TP3 win was credited the full distance.  The real 40/30/30 scale-out is
  modelled.
- Each TP leg counted as a separate trade, tripling *n* with correlated
  samples.  One record per position.

Deliberately pessimistic where the intrabar order is unknowable: if a bar spans
both the stop and a target, the stop is assumed to hit first.
"""

from __future__ import annotations

import bisect
import logging
import math
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Sequence

from models.market_data import Candle, MarketContext

logger = logging.getLogger(__name__)

WINDOW_SIZE = 150          # H1 bars of history fed to the strategy at each step
MAX_HOLD_BARS = 48         # H1 bars a simulated position may stay open
COOLDOWN_BARS = 5          # H1 bars between signals from one strategy
RISK_FRACTION = 0.01       # equity risked per trade (the project's own hard cap)


# ── As-of candle access ──────────────────────────────────────────────────────

class AsOfStore:
    """Candle store that can only ever return bars at or before a timestamp.

    This is the fix for the look-ahead defect: higher-timeframe series are
    sliced by time, never built from the whole array, so a decision at bar *t*
    cannot observe anything after *t*.
    """

    def __init__(self, series: dict[str, Sequence[Candle]]) -> None:
        self._series: dict[str, list[Candle]] = {
            tf: sorted(candles, key=lambda c: c.timestamp)
            for tf, candles in series.items()
        }
        self._times: dict[str, list[datetime]] = {
            tf: [c.timestamp for c in candles] for tf, candles in self._series.items()
        }

    def upto(self, timeframe: str, ts: datetime, count: int) -> list[Candle]:
        """Return the last *count* bars of *timeframe* with timestamp <= ts."""
        times = self._times.get(timeframe)
        if not times:
            return []
        idx = bisect.bisect_right(times, ts)
        candles = self._series[timeframe]
        return candles[max(0, idx - count):idx]


class AsOfBroker:
    """Broker shim that serves only candles visible at the current step time."""

    def __init__(self, store: AsOfStore, symbol: str) -> None:
        self._store = store
        self._symbol = symbol
        self._ts: datetime | None = None

    def set_time(self, ts: datetime) -> None:
        self._ts = ts

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        if self._ts is None:
            return []
        return self._store.upto(timeframe, self._ts, count)

    def get_tick(self, symbol: str) -> dict[str, float]:
        return {"bid": 0.0, "ask": 0.0, "spread": 0.0, "volume": 0.0}

    def get_contract_size(self, symbol: str) -> float:
        return _contract_size(symbol)

    def get_tick_size(self, symbol: str) -> float:
        try:
            from config.symbols import pip_value
            return float(pip_value(symbol))
        except Exception:
            return 0.0001


# ── Indicator helpers (mirror AnalysisAgent, no DB dependency) ───────────────

def _sma(values: list[float], period: int) -> float:
    if period <= 0 or len(values) < period:
        return 0.0
    return round(sum(values[-period:]) / period, 5)


def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains = sum(d for d in recent if d > 0)
    losses = -sum(d for d in recent if d < 0)
    if gains == 0 and losses == 0:
        return 50.0
    avg_gain = gains / period
    avg_loss = (losses / period) or 1e-4
    return round(100 - 100 / (1 + avg_gain / avg_loss), 2)


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = [
        max(
            candles[i].high - candles[i].low,
            abs(candles[i].high - candles[i - 1].close),
            abs(candles[i].low - candles[i - 1].close),
        )
        for i in range(1, len(candles))
    ]
    recent = trs[-period:]
    return round(sum(recent) / len(recent), 5) if recent else 0.0


def build_context(
    symbol: str,
    window: list[Candle],
    store: AsOfStore,
    ts: datetime,
) -> MarketContext:
    """Build a MarketContext from bars visible at *ts*.  Nothing later leaks in."""
    closes = [c.close for c in window]
    atr = _atr(window, 14)
    rsi_val = _rsi(closes, 14)

    from config import settings as _settings
    sma_fast = _sma(closes, getattr(_settings, "SMA_FAST_PERIOD", 20))
    sma_slow = _sma(closes, getattr(_settings, "SMA_SLOW_PERIOD", 50))

    if atr > 0 and len(closes) >= 14:
        rng = max(closes[-14:]) - min(closes[-14:])
        if rng > atr * 3:
            regime = "volatile"
        elif sma_fast and sma_slow and abs(sma_fast - sma_slow) > atr:
            regime = "trending"
        else:
            regime = "ranging"
    else:
        regime = "unknown"

    trend = "bullish" if sma_fast > sma_slow else ("bearish" if sma_fast < sma_slow else "neutral")
    mid = window[-1].close

    return MarketContext(
        symbol=symbol,
        current_price=mid,
        bid=mid,
        ask=mid,
        spread=window[-1].spread,
        volume=window[-1].volume,
        timestamp=ts,
        sma_fast=sma_fast,
        sma_slow=sma_slow,
        rsi=rsi_val,
        atr=atr,
        regime=regime,
        trend_direction=trend,
        session="",
        day_of_week=ts.strftime("%A"),
        near_news_event=False,
        candles=window,
        h4_candles=store.upto("H4", ts, 200),
        d1_candles=store.upto("D1", ts, 100),
        m30_candles=store.upto("M30", ts, 200),
        m15_candles=store.upto("M15", ts, 400),
    )


# ── Execution simulation ─────────────────────────────────────────────────────

def _splits(n_targets: int) -> list[float]:
    """Position fraction taken at each target.  Sums to 1.0."""
    if n_targets <= 1:
        return [1.0]
    if n_targets == 2:
        return [0.4, 0.6]
    return [0.4, 0.3, 0.3]


def invert_signal(signal):
    """Reflect a signal through its entry price and flip its direction.

    This is the exact opposite bet: same entry, identical risk distance,
    mirrored targets.  If a strategy loses because its signals are backwards,
    the inverse must show the profit.  If the inverse is *also* flat or losing,
    there is no signal to invert — the entries are noise and the loss is cost.
    """
    entry = float(signal.entry_price)

    def mirror(level) -> float:
        level = float(level or 0.0)
        return (2.0 * entry - level) if level > 0 else 0.0

    return SimpleNamespace(
        symbol=signal.symbol,
        strategy=f"{getattr(signal, 'strategy', 'unknown')}_inverted",
        direction="SELL" if signal.direction == "BUY" else "BUY",
        entry_price=entry,
        stop_loss=mirror(signal.stop_loss),
        take_profit_1=mirror(getattr(signal, "take_profit_1", 0.0)),
        take_profit_2=mirror(getattr(signal, "take_profit_2", 0.0)),
        take_profit_3=mirror(getattr(signal, "take_profit_3", 0.0)),
    )


@dataclass
class Position:
    """One resolved position — the unit of measurement (never a single TP leg)."""

    symbol: str
    strategy: str
    direction: str
    opened_at: datetime
    entry: float
    stop_loss: float
    targets: list[float]
    fill_index: int = -1
    outcome: str = ""
    net_r: float = 0.0
    bars_held: int = 0


def simulate(
    signal,
    opened_at: datetime,
    future: Sequence[Candle],
    *,
    spread: float,
    commission_per_lot_value: float,
    contract_size_value: float,
    max_hold: int = MAX_HOLD_BARS,
    pessimistic: bool = True,
) -> Position:
    """Resolve one signal into one position, net of costs.

    ``outcome`` is ``NO_FILL`` when price never returned to the limit level —
    such signals contribute no PnL and are reported separately rather than
    silently counted as trades.
    """
    is_buy = signal.direction == "BUY"
    entry = float(signal.entry_price)
    sl = float(signal.stop_loss)
    pos = Position(
        symbol=signal.symbol,
        strategy=getattr(signal, "strategy", "unknown"),
        direction=signal.direction,
        opened_at=opened_at,
        entry=entry,
        stop_loss=sl,
        targets=[float(t) for t in (
            getattr(signal, "take_profit_1", 0.0),
            getattr(signal, "take_profit_2", 0.0),
            getattr(signal, "take_profit_3", 0.0),
        ) if t and float(t) > 0],
    )

    r_dist = abs(entry - sl)
    if r_dist <= 0:
        pos.outcome = "INVALID"
        return pos

    # Round-trip costs expressed in R so they scale with the trade's own risk.
    spread_cost_r = spread / r_dist
    commission_r = (2.0 * commission_per_lot_value) / max(
        contract_size_value * r_dist, 1e-12
    )

    targets = pos.targets
    fractions = _splits(len(targets))
    filled = False
    remaining = 1.0
    realised = 0.0
    hit = 0
    last = 0

    for i, candle in enumerate(future[:max_hold]):
        hi, lo = candle.high, candle.low
        last = i + 1

        if not filled:
            touched = (lo <= entry) if is_buy else (hi >= entry)
            if not touched:
                continue
            filled = True
            pos.fill_index = i

        stop_hit = (lo <= sl) if is_buy else (hi >= sl)

        # Intrabar order is not recoverable from OHLC.  Pessimistic (the
        # default) assumes the stop got there first — the honest choice, since
        # assuming the opposite flatters every result.
        if pessimistic and stop_hit:
            realised += remaining * (-1.0)
            pos.outcome = "SL"
            pos.bars_held = last
            pos.net_r = realised - spread_cost_r - commission_r
            return pos

        while hit < len(targets):
            tgt = targets[hit]
            reached = (hi >= tgt) if is_buy else (lo <= tgt)
            if not reached:
                break
            leg_r = ((tgt - entry) / r_dist) if is_buy else ((entry - tgt) / r_dist)
            realised += fractions[hit] * leg_r
            remaining -= fractions[hit]
            hit += 1

        if remaining <= 1e-9:
            pos.outcome = "TP_FULL"
            pos.bars_held = last
            pos.net_r = realised - spread_cost_r - commission_r
            return pos

        if stop_hit:
            realised += remaining * (-1.0)
            pos.outcome = "SL"
            pos.bars_held = last
            pos.net_r = realised - spread_cost_r - commission_r
            return pos

    if not filled:
        pos.outcome = "NO_FILL"
        pos.bars_held = last
        return pos

    # Still open at the horizon — mark out at the last close.
    exit_candle = future[min(last, len(future)) - 1]
    exit_r = (
        (exit_candle.close - entry) / r_dist
        if is_buy
        else (entry - exit_candle.close) / r_dist
    )
    realised += remaining * exit_r
    pos.outcome = "TIMEOUT"
    pos.bars_held = last
    pos.net_r = realised - spread_cost_r - commission_r
    return pos


# ── Metrics ──────────────────────────────────────────────────────────────────

@dataclass
class Metrics:
    label: str = ""
    positions: int = 0
    no_fills: int = 0
    wins: int = 0
    win_rate: float = 0.0
    avg_r: float = 0.0
    total_r: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    annualised_sharpe: float = 0.0
    final_equity: float = 1.0
    total_return_pct: float = 0.0
    buy_hold_pct: float = 0.0
    baseline_available: bool = False
    days: float = 0.0

    def render(self) -> str:
        bh = f"{self.buy_hold_pct:>+8.2f}%" if self.baseline_available else "     n/a"
        return (
            f"{self.label:<20} n={self.positions:<4} nofill={self.no_fills:<4} "
            f"win={self.win_rate:>6.1%} avgR={self.avg_r:>+7.3f} "
            f"PF={self.profit_factor:>5.2f} maxDD={self.max_drawdown_pct:>6.1%} "
            f"Sharpe={self.annualised_sharpe:>6.2f} ret={self.total_return_pct:>+8.2f}% "
            f"B&H={bh}"
        )


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def compute_metrics(
    positions: list[Position],
    *,
    label: str = "",
    risk_fraction: float = RISK_FRACTION,
    first_close: float = 0.0,
    last_close: float = 0.0,
) -> Metrics:
    """Per-position statistics with a compounded equity curve."""
    m = Metrics(label=label)
    m.no_fills = sum(1 for p in positions if p.outcome == "NO_FILL")
    filled = [p for p in positions if p.outcome not in ("NO_FILL", "INVALID")]
    m.positions = len(filled)

    if filled:
        m.wins = sum(1 for p in filled if p.net_r > 0)
        m.win_rate = m.wins / len(filled)
        m.total_r = sum(p.net_r for p in filled)
        m.avg_r = m.total_r / len(filled)
        gross_win = sum(p.net_r for p in filled if p.net_r > 0)
        gross_loss = abs(sum(p.net_r for p in filled if p.net_r < 0))
        m.profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

        equity = [1.0]
        for p in filled:
            equity.append(equity[-1] * (1.0 + risk_fraction * p.net_r))
        m.final_equity = equity[-1]
        m.total_return_pct = (equity[-1] - 1.0) * 100.0
        m.max_drawdown_pct = _max_drawdown(equity)

        returns = [risk_fraction * p.net_r for p in filled]
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        sd = math.sqrt(var)
        span_days = (filled[-1].opened_at - filled[0].opened_at).total_seconds() / 86400.0
        m.days = span_days
        if sd > 0 and span_days > 0:
            years = max(span_days / 365.25, 1e-9)
            trades_per_year = len(filled) / years
            m.annualised_sharpe = (mean / sd) * math.sqrt(trades_per_year)

    if first_close > 0:
        m.buy_hold_pct = (last_close / first_close - 1.0) * 100.0
        m.baseline_available = True
    return m


# ── Driver ───────────────────────────────────────────────────────────────────

def _commission(symbol: str) -> float:
    try:
        from config.symbols import commission_per_lot
        return float(commission_per_lot(symbol))
    except Exception:
        return 0.0


def _contract_size(symbol: str) -> float:
    try:
        from config.symbols import contract_size
        return float(contract_size(symbol))
    except Exception:
        return 100_000.0


def run_symbol(
    symbol: str,
    series: dict[str, Sequence[Candle]],
    *,
    strategy_factory,
    warmup: int = WINDOW_SIZE,
    pessimistic: bool = True,
    invert: bool = False,
) -> list[Position]:
    """Walk a symbol's H1 history forward, resolving one position per signal."""
    h1 = list(series.get("H1") or [])
    if len(h1) < warmup + MAX_HOLD_BARS + 2:
        logger.warning("%s: only %d H1 bars — skipping", symbol, len(h1))
        return []

    store = AsOfStore(series)
    broker = AsOfBroker(store, symbol)

    # Built once per symbol, not per bar — the broker reference is live, so the
    # strategy sees the current as-of time on every detect() call.
    strategy = strategy_factory(broker)

    positions: list[Position] = []
    last_signal_bar = -10_000

    for bar in range(warmup, len(h1) - MAX_HOLD_BARS):
        ts = h1[bar - 1].timestamp          # last CLOSED bar
        broker.set_time(ts)
        window = store.upto("H1", ts, warmup)

        if bar - last_signal_bar < COOLDOWN_BARS:
            continue

        ctx = build_context(symbol, window, store, ts)
        try:
            signal = strategy.detect(ctx)
        except Exception as exc:                       # noqa: BLE001
            logger.debug("%s: strategy raised at bar %d (%s)", symbol, bar, exc)
            continue
        if signal is None:
            continue

        if invert:
            signal = invert_signal(signal)

        last_signal_bar = bar
        future = h1[bar: bar + MAX_HOLD_BARS + 1]
        positions.append(
            simulate(
                signal,
                ts,
                future,
                spread=float(h1[bar - 1].spread or 0.0),
                commission_per_lot_value=_commission(symbol),
                contract_size_value=_contract_size(symbol),
                pessimistic=pessimistic,
            )
        )

    return positions


def summarise(positions: list[Position], h1: Sequence[Candle], *, label: str) -> Metrics:
    return compute_metrics(
        positions,
        label=label,
        first_close=h1[0].close if h1 else 0.0,
        last_close=h1[-1].close if h1 else 0.0,
    )


def split_folds(positions: list[Position], n: int = 5) -> list[list[Position]]:
    """Split time-ordered positions into sequential folds."""
    if not positions or n <= 1:
        return [positions]
    size = max(1, len(positions) // n)
    return [positions[i: i + size] for i in range(0, len(positions), size)]


def _self_check() -> None:
    """Runnable check for the parts that decide money: fills, costs, scale-out."""
    from datetime import UTC
    from types import SimpleNamespace

    def candle(o, h, l, c):
        return Candle(timestamp=datetime.now(UTC), open=o, high=h, low=l, close=c)

    free = dict(spread=0.0, commission_per_lot_value=0.0, contract_size_value=100_000.0)

    sig = SimpleNamespace(
        symbol="EURUSD", strategy="t", direction="BUY", entry_price=1.1000,
        stop_loss=1.0950, take_profit_1=1.1050, take_profit_2=0.0, take_profit_3=0.0,
    )

    # 1. A limit price never returns to must not count as a trade.
    never = [candle(1.1060, 1.1070, 1.1055, 1.1065) for _ in range(10)]
    assert simulate(sig, datetime.now(UTC), never, **free).outcome == "NO_FILL"

    # 2. Touched then straight to SL = -1R exactly.
    p = simulate(sig, datetime.now(UTC), [candle(1.1000, 1.1005, 1.0940, 1.0950)], **free)
    assert p.outcome == "SL" and abs(p.net_r + 1.0) < 1e-9, p

    # 3. Touched then full TP with one target = the full R, not a leg.
    p = simulate(sig, datetime.now(UTC), [candle(1.1000, 1.1060, 1.0995, 1.1055)], **free)
    assert p.outcome == "TP_FULL" and abs(p.net_r - 1.0) < 1e-9, p

    # 4. Three targets reached across bars scale out 40/30/30, not 100% at TP3.
    sig3 = SimpleNamespace(
        symbol="EURUSD", strategy="t", direction="BUY", entry_price=1.1000,
        stop_loss=1.0950, take_profit_1=1.1050, take_profit_2=1.1100,
        take_profit_3=1.1150,
    )
    ladder = [
        candle(1.1000, 1.1050, 1.0999, 1.1049),
        candle(1.1049, 1.1100, 1.1040, 1.1099),
        candle(1.1099, 1.1150, 1.1090, 1.1149),
    ]
    p = simulate(sig3, datetime.now(UTC), ladder, **free)
    expected = 0.4 * 1.0 + 0.3 * 2.0 + 0.3 * 3.0
    assert p.outcome == "TP_FULL" and abs(p.net_r - expected) < 1e-9, (p, expected)

    # 5. Spread is charged: a 2-pip spread on a 50-pip stop costs 0.04R.
    p_cost = simulate(
        sig, datetime.now(UTC), [candle(1.1000, 1.1060, 1.0995, 1.1055)],
        spread=0.0002, commission_per_lot_value=0.0, contract_size_value=100_000.0,
    )
    assert abs(p_cost.net_r - (1.0 - 0.0002 / 0.0050)) < 1e-9, p_cost

    # 6. A bar spanning both stop and target resolves to the stop.
    spanning = [candle(1.1000, 1.1060, 1.0940, 1.1000)]
    assert simulate(sig, datetime.now(UTC), spanning, **free).outcome == "SL"

    print("measure.py self-check: OK")


if __name__ == "__main__":
    _self_check()
