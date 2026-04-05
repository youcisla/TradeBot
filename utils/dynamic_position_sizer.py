"""
Dynamic Position Sizing via Kelly Criterion
=============================================
From StockSharp/QuantConnect: scale position based on win rate + average win/loss.
More aggressive when edge is clear, conservative when uncertain.

Kelly formula: f* = (bp - q) / b
  f* = fractional position size
  b = average_win / average_loss
  p = win_probability
  q = 1 - p

Safety: Use 0.25 × f* (quarter-Kelly) to reduce volatility.
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DynamicPositionSizer:
    """
    Calculates position size based on recent strategy performance.
    
    Usage:
        sizer = DynamicPositionSizer(lookback_days=30)
        lot_size = sizer.calculate_position_size(
            account_equity=10000,
            symbol='EURUSD',
            recent_trades=[...],  # Win/loss magnitudes
            atr=0.0050,
            sl_distance=0.0100,
            strategy_name='neural',
        )
    """
    
    def __init__(
        self,
        lookback_days: int = 30,
        min_kelly_fraction: float = 0.10,  # Use 10% Kelly minimum (very conservative)
        max_kelly_fraction: float = 0.25,  # Cap at 25% Kelly (quarter-Kelly safe)
        min_sample_trades: int = 10,  # Need at least 10 recent trades
        fallback_risk_pct: float = 0.02,  # Default if insufficient history
    ):
        self.lookback_days = lookback_days
        self.min_kelly_fraction = min_kelly_fraction
        self.max_kelly_fraction = max_kelly_fraction
        self.min_sample_trades = min_sample_trades
        self.fallback_risk_pct = fallback_risk_pct
    
    def calculate_position_size(
        self,
        account_equity: float,
        symbol: str,
        recent_trades: list,  # List of dicts: {result: 'W'|'L', pnl_pct: 0.015, ...}
        atr: float,
        sl_distance: float,
        strategy_name: str = 'neural',
        volatility_regime: str = 'normal',  # 'calm'|'normal'|'elevated'
    ) -> Tuple[float, Dict]:
        """
        Calculate lot size and return diagnostic info.
        
        Returns:
            (lot_size, details_dict)
        """
        details = {
            'symbol': symbol,
            'strategy': strategy_name,
            'volatility_regime': volatility_regime,
            'account_equity': account_equity,
            'atr': atr,
        }
        
        # Filter trades from last N days for this strategy
        cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)
        relevant_trades = [
            t for t in recent_trades
            if (t.get('strategy') == strategy_name and
                datetime.fromisoformat(t.get('closed_at', '')) > cutoff_date)
        ]
        
        details['sample_trades'] = len(relevant_trades)
        
        # Fallback if insufficient history
        if len(relevant_trades) < self.min_sample_trades:
            logger.warning(
                f"{symbol} {strategy_name}: only {len(relevant_trades)} trades, "
                f"using fallback {self.fallback_risk_pct*100}%"
            )
            risk_pct = self.fallback_risk_pct
            details['reason'] = 'insufficient_history'
            details['kelly_fraction'] = None
            details['kelly_position_size'] = None
            lot_size = self._calculate_lot_from_risk_pct(
                account_equity, risk_pct, atr, sl_distance
            )
            details['final_lot_size'] = lot_size
            return lot_size, details
        
        # Calculate Kelly components
        win_trades = [t for t in relevant_trades if t.get('result') == 'W']
        loss_trades = [t for t in relevant_trades if t.get('result') == 'L']
        
        p = len(win_trades) / len(relevant_trades)  # Win rate
        details['win_rate'] = p
        details['win_count'] = len(win_trades)
        details['loss_count'] = len(loss_trades)
        
        # Avoid division by zero
        if len(win_trades) == 0 or len(loss_trades) == 0:
            logger.warning(
                f"{symbol}: no wins or losses found, using fallback"
            )
            risk_pct = self.fallback_risk_pct
            details['reason'] = 'no_win_loss_history'
            lot_size = self._calculate_lot_from_risk_pct(
                account_equity, risk_pct, atr, sl_distance
            )
            details['final_lot_size'] = lot_size
            return lot_size, details
        
        avg_win = sum(t.get('pnl_pct', 0) for t in win_trades) / len(win_trades)
        avg_loss = abs(sum(t.get('pnl_pct', 0) for t in loss_trades) / len(loss_trades))
        
        details['avg_win_pct'] = avg_win
        details['avg_loss_pct'] = avg_loss
        
        # Avoid division by zero in Kelly
        if avg_loss == 0:
            avg_loss = 0.001  # Minimum threshold
        
        # Kelly: f* = (bp - q) / b, where b = avg_win / avg_loss
        b = avg_win / avg_loss if avg_loss > 0 else 1.0
        q = 1 - p
        
        if b > 0:
            f_star = (b * p - q) / b
        else:
            f_star = 0  # No edge
        
        details['kelly_fraction_raw'] = f_star
        
        # Clamp to safe range
        kelly_fraction = max(
            self.min_kelly_fraction,
            min(f_star, self.max_kelly_fraction)
        )
        details['kelly_fraction'] = kelly_fraction
        
        # Volatility adjustment
        if volatility_regime == 'elevated':
            kelly_fraction *= 0.75  # 25% reduction in high vol
        elif volatility_regime == 'calm':
            kelly_fraction *= 1.1  # 10% increase in low vol
        
        details['kelly_fraction_adjusted'] = kelly_fraction
        
        # Convert Kelly to risk %
        risk_pct = kelly_fraction
        details['risk_pct'] = risk_pct
        
        # Calculate final lot size
        lot_size = self._calculate_lot_from_risk_pct(
            account_equity, risk_pct, atr, sl_distance
        )
        details['final_lot_size'] = lot_size
        details['reason'] = 'kelly_calculation'
        
        logger.info(
            f"{symbol} {strategy_name}: Kelly f*={f_star:.3f}, "
            f"adjusted={kelly_fraction:.3f}, lot_size={lot_size:.2f}"
        )
        
        return lot_size, details
    
    @staticmethod
    def _calculate_lot_from_risk_pct(
        account_equity: float,
        risk_pct: float,
        atr: float,
        sl_distance: float,
    ) -> float:
        """
        lot_size = (account * risk_pct) / (sl_distance * pip_value)
        
        For simplicity, assume pip_value = 0.0001 (standard FX).
        In production, query broker for exact pip value per symbol.
        """
        if sl_distance <= 0 or atr <= 0:
            return 0.1  # Minimum safe lot
        
        risk_amount = account_equity * risk_pct
        pip_value = 0.0001  # Standard FX
        sl_pips = sl_distance / pip_value
        
        lot_size = risk_amount / (sl_pips * pip_value * 100000)  # 100k per lot
        
        # Bounds
        lot_size = max(0.01, min(lot_size, 10.0))  # 0.01–10.0 lots
        
        return lot_size


# Example: integrate into risk_agent.py
"""
In risk_agent.py assess_and_size_trade():

    sizer = DynamicPositionSizer(lookback_days=30)
    
    # Fetch recent trades for this strategy
    recent_trades = db.get_trades(
        symbol=context.symbol,
        strategy=context.strategy_name,
        limit=100,
    )
    
    lot_size, details = sizer.calculate_position_size(
        account_equity=context.account.equity,
        symbol=context.symbol,
        recent_trades=recent_trades,
        atr=context.atr,
        sl_distance=signal.stop_loss,
        strategy_name=context.strategy_name,
        volatility_regime=context.volatility_regime,
    )
    
    logger.info(f"Position sizing details: {json.dumps(details, indent=2)}")
    
    # Respect risk caps
    lot_size = min(lot_size, MAX_LOT_PER_TRADE)
    return RiskAssessment(
        approved=True,
        lot_size=lot_size,
        reason=f"Kelly-based: {details['kelly_fraction']:.1%}",
    )
"""
