"""Backtesting engine — scan-rank-execute pipeline over historical candles.

Uses the same agent pipeline as live trading (MarketAgent → AnalysisAgent →
StrategyAgent → lot-sizing) with MockBroker instead of MT5, so backtest
behaviour closely mirrors live execution.

Each trade uses three sub-positions matching the live TP1/TP2/TP3 split.
When TP1 is hit the SL on the remaining legs moves to breakeven.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from backtesting.mock_broker import MockBroker
from backtesting.report import generate_report, generate_run_artifact, inject_report_to_db
from database.db import Database
from utils.mesh_bus import record_call

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────

def _atr(candles: list, period: int = 14) -> float:
    """Average True Range over the last *period* candles."""
    if len(candles) < 2:
        return 0.001
    trs = []
    for i in range(1, min(period + 1, len(candles))):
        c = candles[-i]
        p = candles[-i - 1]
        trs.append(max(c.high - c.low,
                       abs(c.high - p.close),
                       abs(c.low  - p.close)))
    return sum(trs) / len(trs) if trs else 0.001


@dataclass
class _TradeGroup:
    """The three TP legs that make up one logical backtest trade."""
    symbol:    str
    direction: str
    entry:     float
    sl:        float
    tp1:       float
    tp2:       float
    tp3:       float
    ticket1:   int          # 40 % lot — TP1 leg
    ticket2:   int          # 30 % lot — TP2 leg
    ticket3:   int          # 30 % lot — TP3 leg
    tp1_hit:   bool = False
    closed:    bool = False


# ── Engine ───────────────────────────────────────────────────────────────

class BacktestEngine:
    """Historical simulation engine.

    Wires up real agents against MockBroker so that signal detection,
    ATR calculation, and lot sizing match live behaviour exactly.
    """

    def __init__(self, data_path: Path | str,
                 initial_balance: float = 10_000.0,
                 db: Database | None = None) -> None:
        self.data_path       = Path(data_path)
        self.broker          = MockBroker(initial_balance=initial_balance)
        self._initial_balance = initial_balance
        self.db              = db

    # ── public API ───────────────────────────────────────────────────────

    def run(
        self,
        symbol: str,
        *,
        profile: str = "custom",
        mode: str = "backtest",
        export_artifact: bool = False,
        artifact_path: Path | str | None = None,
    ) -> dict:
        """Run the backtest and return the performance report dict."""
        _t0 = time.monotonic()
        # Import agents lazily so the module can be imported without all
        # agent dependencies installed (useful for tests).
        from agents.market_agent   import MarketAgent
        from agents.analysis_agent import AnalysisAgent
        from agents.strategy_agent import StrategyAgent
        from config                import settings
        from filters.data_validator import DataValidationError
        from strategies.ict_strategy    import ICTStrategy
        from strategies.sma_crossover   import SmaCrossoverStrategy

        logger.info("BacktestEngine: starting %s (balance=%.0f)", symbol, self._initial_balance)
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        self.broker.load_data(str(self.data_path))
        self.broker.connect()

        # ── Agent wiring (no DB, no Crucix in backtest) ──────────────────
        market_agent   = MarketAgent(self.broker, db=None)
        analysis_agent = AnalysisAgent(crucix_agent=None, db=None)

        ict = ICTStrategy(broker=self.broker, db=None, min_confidence=55.0)
        sma = SmaCrossoverStrategy()
        # Confidence getter always returns 1.0 — no learning system in backtest
        strategy_agent = StrategyAgent([ict, sma], lambda _s: 1.0, db=None)

        # Lot sizing: use the same risk formula as live, but skip the
        # duplicate / correlation / drawdown checks that require Trade objects.
        from config.symbols import contract_size as _cs
        def _lot(signal) -> float:
            balance      = self.broker.get_balance()
            risk_amt     = balance * settings.MAX_RISK_PER_TRADE
            sl_dist      = abs(signal.entry_price - signal.stop_loss)
            if sl_dist == 0:
                return settings.MIN_LOT_SIZE
            risk_per_lot = sl_dist * _cs(signal.symbol)
            raw          = round(risk_amt / risk_per_lot, 2)
            return max(settings.MIN_LOT_SIZE, min(settings.MAX_LOT_SIZE, raw))

        open_groups: list[_TradeGroup] = []
        trade_count  = 0
        step_count   = 0

        while self.broker.step():
            step_count += 1
            if step_count % 500 == 0:
                logger.info("Processed %d candles — %s  equity=%.2f",
                            step_count,
                            self.broker.current_candle.timestamp,
                            self.broker.get_equity())

            open_tickets = set(self.broker.positions)

            # ── Manage existing trade groups ─────────────────────────────
            for grp in open_groups:
                if grp.closed:
                    continue

                # TP1 hit → move SL to breakeven on remaining legs
                if not grp.tp1_hit and grp.ticket1 not in open_tickets:
                    tp1_rec = next(
                        (p for p in self.broker.closed_positions
                         if p.ticket == grp.ticket1 and p.pnl > 0),
                        None,
                    )
                    if tp1_rec:
                        grp.tp1_hit = True
                        self.broker.modify_order(grp.ticket2, sl=grp.entry)
                        self.broker.modify_order(grp.ticket3, sl=grp.entry)

                # SL hit on any leg → emergency-close all remaining siblings
                for t in (grp.ticket1, grp.ticket2, grp.ticket3):
                    if t in open_tickets:
                        continue
                    sl_rec = next(
                        (p for p in self.broker.closed_positions
                         if p.ticket == t and p.pnl < 0),
                        None,
                    )
                    if sl_rec:
                        for sib in (grp.ticket1, grp.ticket2, grp.ticket3):
                            if sib in open_tickets:
                                self.broker.close_order(sib, grp.symbol, grp.direction)
                        grp.closed = True
                        break

                # All three legs gone → group is done
                if (grp.ticket1 not in open_tickets
                        and grp.ticket2 not in open_tickets
                        and grp.ticket3 not in open_tickets):
                    grp.closed = True

            open_groups = [g for g in open_groups if not g.closed]

            # ── Skip new signals if already in a position on this symbol ─
            open_symbols = {self.broker.positions[t].symbol for t in self.broker.positions}
            if symbol in open_symbols:
                continue

            # ── Require enough history for analysis ──────────────────────
            candles = self.broker.get_candles(symbol, "H1", 250)
            if len(candles) < 200:
                continue

            # ── Signal pipeline ──────────────────────────────────────────
            try:
                data = market_agent.get_data(symbol)
            except (DataValidationError, Exception):
                continue

            context = analysis_agent.analyze(data)
            signals = strategy_agent.detect_all(context)
            if not signals:
                continue

            # Take the highest-confidence signal
            signals.sort(key=lambda s: s.confidence, reverse=True)
            signal = signals[0]

            # Patch SL/TP from ATR if strategy left them at 0
            atr = _atr(candles)
            if signal.stop_loss == 0.0:
                if signal.direction == "BUY":
                    signal.stop_loss    = signal.entry_price - 2 * atr
                    signal.take_profit_1 = signal.entry_price + 1 * atr
                    signal.take_profit_2 = signal.entry_price + 2 * atr
                    signal.take_profit_3 = signal.entry_price + 3 * atr
                else:
                    signal.stop_loss    = signal.entry_price + 2 * atr
                    signal.take_profit_1 = signal.entry_price - 1 * atr
                    signal.take_profit_2 = signal.entry_price - 2 * atr
                    signal.take_profit_3 = signal.entry_price - 3 * atr

            lot_size = _lot(signal)
            if lot_size <= 0:
                continue

            # Split into TP1/TP2/TP3 legs (match live ratios)
            lot1 = round(lot_size * settings.TP1_CLOSE_PERCENT, 2)
            lot2 = round(lot_size * settings.TP2_CLOSE_PERCENT, 2)
            lot3 = round(lot_size - lot1 - lot2, 2)
            if lot3 < settings.MIN_LOT_SIZE:
                lot3 = settings.MIN_LOT_SIZE

            sl   = signal.stop_loss
            tp1  = signal.take_profit_1
            tp2  = signal.take_profit_2
            tp3  = signal.take_profit_3

            r1 = self.broker.place_order(symbol, signal.direction, lot1, sl, tp1,
                                         comment=f"{signal.strategy}_TP1")
            r2 = self.broker.place_order(symbol, signal.direction, lot2, sl, tp2,
                                         comment=f"{signal.strategy}_TP2")
            r3 = self.broker.place_order(symbol, signal.direction, lot3, sl, tp3,
                                         comment=f"{signal.strategy}_TP3")

            if r1.success and r2.success and r3.success:
                trade_count += 1
                open_groups.append(_TradeGroup(
                    symbol=symbol, direction=signal.direction,
                    entry=signal.entry_price, sl=sl,
                    tp1=tp1, tp2=tp2, tp3=tp3,
                    ticket1=r1.broker_ticket,
                    ticket2=r2.broker_ticket,
                    ticket3=r3.broker_ticket,
                ))
                logger.info(
                    "Trade #%d: %s %s conf=%.0f%% SL=%.5f TP1=%.5f TP3=%.5f lot=%.2f",
                    trade_count, signal.direction, symbol,
                    signal.confidence * 100, sl, tp1, tp3, lot_size,
                )

        self.broker.disconnect()
        logger.info("Backtest done: %d candles processed, %d trades opened",
                    step_count, trade_count)

        report = generate_report(self.broker.closed_positions,
                                 initial_balance=self._initial_balance)

        if export_artifact:
            artifact = generate_run_artifact(
                self.broker.closed_positions,
                initial_balance=self._initial_balance,
                symbol=symbol,
                profile=profile,
                mode=mode,
                source_data=str(self.data_path),
                report=report,
            )
            output_path = Path(artifact_path) if artifact_path else (
                Path("backtesting") / "runs" / f"{symbol.lower()}_{mode}_artifact.json"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as fh:
                json.dump(artifact, fh, indent=2)
            report["Artifact Path"] = str(output_path)

        if self.db:
            inject_report_to_db(report, self.db)
        record_call("backtesting", (time.monotonic() - _t0) * 1000.0, True)
        return report
