"""
Cross-Symbol Correlation Gating
================================
From QuantConnect/StockSharp: reduce position size when multiple correlated pairs open.
Prevents indirect leverage when (e.g.) EURUSD and GBPUSD both long.

Pattern: If correlation > 0.80, scale down second position to 50% of normal size.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class CorrelationGate:
    """
    Tracks correlation between open positions and gates new trades.

    Usage:
        gate = CorrelationGate(correlation_threshold=0.80, lookback_bars=100)

        can_trade, multiplier = gate.check_correlation(
            symbol='GBPUSD',
            open_positions=[{'symbol': 'EURUSD', 'direction': 'long'}],
            price_history={
                'EURUSD': [...],  # Last N closes
                'GBPUSD': [...],
            }
        )

        if can_trade:
            lot_size = normal_lot * multiplier  # E.g., multiplier=0.5 if corr > threshold

    To check readiness before calling check_correlation::

        if gate.has_data('EURUSD'):
            # dynamic correlation is available
    """

    def __init__(
        self,
        threshold: float = 0.80,
        lookback_bars: int = 100,
        size_multiplier: float = 0.5,  # Reduce to 50% if correlated
        lookback_days: int = 30,
    ):
        """
        Args:
            threshold: If |corr| > this, considered correlated (0–1).
            lookback_bars: Number of H1 bars to fetch for correlation calc.
            size_multiplier: Position multiplier when correlated (0–1).
            lookback_days: Historical window for correlation calc.
        """
        self.correlation_threshold = threshold
        self.lookback_bars = lookback_bars
        self.size_multiplier = size_multiplier
        self.lookback_days = lookback_days
        # Price history cache populated by _check_correlation before calling check_correlation.
        self._price_cache: dict[str, list[float]] = {}

    def has_data(self, symbol: str) -> bool:
        """Return True if we have cached price history for *symbol* with enough bars."""
        bars = self._price_cache.get(symbol, [])
        return len(bars) >= self.lookback_bars
    
    def check_correlation(
        self,
        symbol: str,
        open_positions: List[Dict],  # [{symbol, direction, lot_size, entry_price}, ...]
        price_history: Dict[str, List[float]] | None = None,
    ) -> Tuple[bool, float]:
        """
        Check if new trade is correlated with existing open positions.

        Returns:
            (can_trade, size_multiplier)
            can_trade = True (always, but multiplier reflects correlation penalty)
            size_multiplier = 1.0 (normal) or self.size_multiplier (0.5 if corr > threshold)

        If *price_history* is not provided, reads from the internal _price_cache.
        """
        if not open_positions:
            return True, 1.0  # No open positions, no correlation issue

        # Use supplied price_history or fall back to cached data
        if price_history is None:
            price_history = self._price_cache

        if symbol not in price_history:
            return True, 1.0  # No price history for symbol, can't check

        new_prices = price_history[symbol]
        
        max_abs_corr = 0.0
        correlated_with = []
        
        for pos in open_positions:
            pos_symbol = pos.get('symbol')
            if pos_symbol not in price_history:
                continue
            
            pos_prices = price_history[pos_symbol]
            
            # Calculate correlation
            corr = self._calculate_correlation(new_prices, pos_prices)
            
            # Consider direction: two longs/shorts with positive corr are risky
            pos_direction = pos.get('direction')  # 'long' or 'short'
            
            # For now, use absolute correlation (both directions penalized equally)
            abs_corr = abs(corr)
            
            if abs_corr > max_abs_corr:
                max_abs_corr = abs_corr
                correlated_with = [pos_symbol]
            elif abs(abs_corr - max_abs_corr) < 0.01:  # Tie
                correlated_with.append(pos_symbol)
        
        is_correlated = max_abs_corr > self.correlation_threshold
        multiplier = self.size_multiplier if is_correlated else 1.0
        
        if is_correlated:
            logger.info(
                f"{symbol}: correlated with {correlated_with} "
                f"(r={max_abs_corr:.3f} > {self.correlation_threshold}). "
                f"Scaling position to {multiplier*100:.0f}%"
            )
        
        return True, multiplier
    
    @staticmethod
    def _calculate_correlation(prices1: List[float], prices2: List[float]) -> float:
        """Pearson correlation of price series."""
        if len(prices1) < 2 or len(prices2) < 2:
            return 0.0
        
        # Align lengths (take min)
        min_len = min(len(prices1), len(prices2))
        p1 = np.array(prices1[-min_len:], dtype=float)
        p2 = np.array(prices2[-min_len:], dtype=float)
        
        # Handle edge cases
        if np.std(p1) == 0 or np.std(p2) == 0:
            return 0.0
        
        # Log returns for more stable correlation
        ret1 = np.diff(np.log(p1))
        ret2 = np.diff(np.log(p2))
        
        corr = np.corrcoef(ret1, ret2)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0
    
    def get_correlation_matrix(
        self,
        symbols: List[str],
        price_history: Dict[str, List[float]],
    ) -> Dict[Tuple[str, str], float]:
        """
        Build full correlation matrix across all symbols.
        Useful for portfolio-level risk reporting.
        
        Returns:
            {(symbol_a, symbol_b): correlation_coeff, ...}
        """
        corr_matrix = {}
        
        for i, sym_a in enumerate(symbols):
            if sym_a not in price_history:
                continue
            
            for sym_b in symbols[i+1:]:
                if sym_b not in price_history:
                    continue
                
                corr = self._calculate_correlation(
                    price_history[sym_a],
                    price_history[sym_b],
                )
                
                corr_matrix[(sym_a, sym_b)] = corr
                corr_matrix[(sym_b, sym_a)] = corr  # Symmetric
        
        return corr_matrix
    
    def portfolio_delta_exposure(
        self,
        open_positions: List[Dict],  # {symbol, direction, lot_size, delta, ...}
        correlation_matrix: Dict,
    ) -> Dict:
        """
        Compute equivalent single-symbol exposure accounting for correlation.
        E.g., two EURUSD-correlated positions = higher effective delta.
        
        Returns:
            {symbol: effective_delta, ...}
        """
        effective_exposure = {}
        
        for pos in open_positions:
            symbol = pos.get('symbol')
            delta = pos.get('delta', 1.0)  # Position magnitude
            direction = 1 if pos.get('direction') == 'long' else -1
            
            exposure = delta * direction
            effective_exposure[symbol] = exposure
        
        # Adjust for correlations
        adjusted_exposure = {}
        for sym_a, exp_a in effective_exposure.items():
            adj = exp_a
            for sym_b, exp_b in effective_exposure.items():
                if sym_a != sym_b:
                    corr = correlation_matrix.get((sym_a, sym_b), 0.0)
                    # If highly correlated in same direction, amplify risk
                    if corr > 0.80 and exp_a * exp_b > 0:
                        adj += abs(corr) * exp_b * 0.5  # Add correlation penalty
            adjusted_exposure[sym_a] = adj
        
        return adjusted_exposure


# Integration example for risk_agent.py
"""
In assess_and_size_trade():

    gate = CorrelationGate(
        correlation_threshold=0.80,
        lookback_days=30,
        size_multiplier=0.5,  # Half size if correlated
    )
    
    # Fetch price histories for all open positions + new symbol
    all_symbols = [pos['symbol'] for pos in context.open_positions] + [context.symbol]
    price_history = {
        sym: db.get_closes(sym, days=30)
        for sym in all_symbols
    }
    
    can_trade, size_mult = gate.check_correlation(
        symbol=context.symbol,
        open_positions=context.open_positions,
        price_history=price_history,
    )
    
    # Apply multiplier to lot size
    lot_size = calculate_position_size(...) * size_mult
    
    # Get portfolio-level correlation stats for reporting
    corr_matrix = gate.get_correlation_matrix(all_symbols, price_history)
    delta_exposure = gate.portfolio_delta_exposure(
        context.open_positions,
        corr_matrix,
    )
    
    logger.info(f"Portfolio delta by symbol: {delta_exposure}")
    logger.info(f"Correlation matrix: {corr_matrix}")
"""
