"""Backtesting engine core execution loop.

Runs the historical data through the MockBroker and executes
the core ICT strategy at each candle step.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backtesting.mock_broker import MockBroker
from backtesting.report import generate_report, inject_report_to_db
from database.db import Database
from strategies.ict.engine import ICTEngine

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Historical testing engine."""

    def __init__(self, data_path: Path | str, initial_balance: float = 10000.0, db: Database | None = None) -> None:
        self.data_path = Path(data_path)
        self.broker = MockBroker(initial_balance=initial_balance)
        self.ict_engine = ICTEngine(min_confidence=0.5) # Standard threshold
        self.db = db

    def run(self, symbol: str) -> dict:
        """Run the backtest loop over the loaded history."""
        
        logger.info("Initializing BacktestEngine for %s", symbol)
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
            
        self.broker.load_data(str(self.data_path))
        self.broker.connect()
        
        step_count = 0
        trade_count = 0
        
        logger.info("Starting historical simulation loop...")
        
        while self.broker.step():
            c = self.broker.current_candle
            step_count += 1
            
            # Print progress every 500 candles
            if step_count % 500 == 0:
                logger.info("Processed %d candles... Current time: %s", step_count, c.timestamp)
            
            # 1. Fetch historical context (up to current simulated time)
            # Need minimum candles for ICT Engine (usually >200 for HTF bias + LTF setups)
            candles = self.broker.get_candles(symbol, "H1", 250)
            if len(candles) < 200:
                continue
                
            # 2. Run ICT Engine
            current_tick = self.broker.get_tick(symbol)
            
            ctx, setup, _ = self.ict_engine.analyze(
                symbol=symbol,
                candles=candles,
                htf_candles=candles, # Using H1 for both since we're in backtest
                current_price=current_tick["bid"],
                atr=0.0010, # mock ATR for simplicity
            )
            
            # 3. Execution logic
            if setup:
                # Check if we already have an open position
                # Simple logic: 1 position at a time
                if not self.broker.positions:
                    logger.info("New Setup %s: %s at %.5f (Score: %.1f)", 
                                setup.direction, setup.model.name, setup.entry_price, setup.confidence)
                                
                    res = self.broker.place_order(
                        symbol=symbol,
                        direction=setup.direction,
                        lot_size=0.1, # Fixed 0.1 lots for backtesting test
                        sl=setup.stop_loss,
                        tp=setup.take_profit_2,  # Target TP2
                        comment=setup.model.name  # Pass model name to tracker!
                    )
                    if res.success:
                        trade_count += 1
        
        self.broker.disconnect()
        logger.info("Backtest complete. Processed %d candles. Executed %d trades.", step_count, trade_count)
        
        # Output Report
        report = generate_report(self.broker.closed_positions, initial_balance=10000.0)
        
        if self.db:
            inject_report_to_db(report, self.db)
            
        return report
