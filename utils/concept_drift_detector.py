"""
Concept Drift Detection using Kolmogorov-Smirnov Test
======================================================
From TradingGym/AI-Trader: detects when market dist diverges from training dist.

Pattern: Compare price distribution (returns) now vs. training period.
If KS statistic p-value < 0.05, market regime has likely changed.

This triggers manual model evaluation or auto-retraining queue.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class DriftDetectionResult:
    """Analysis result from comparing two distributions."""
    symbol: str
    metric: str  # 'returns', 'volatility', 'volume', ...
    ks_statistic: float  # 0–1, how different the distributions are
    p_value: float  # probability they're same distribution
    drift_detected: bool  # p_value < threshold
    ref_mean: float  # Mean of reference (training) data
    ref_std: float
    current_mean: float  # Mean of current (recent) data
    current_std: float
    samples_ref: int
    samples_current: int
    timestamp: str


class ConceptDriftDetector:
    """
    Monitors for market regime shifts that degrade model performance.
    
    Usage:
        detector = ConceptDriftDetector(
            reference_period_days=365,  # Training period
            current_window_days=30,  # Recent period to test
            drift_threshold_p=0.05,  # KS test significance
        )
        
        result = detector.detect_drift(
            symbol='EURUSD',
            recent_candles=[...],
            metric='returns',  # or 'volatility', 'volume'
        )
        
        if result.drift_detected:
            logger.alert(f"DRIFT on {symbol}: retraining recommended")
    """
    
    def __init__(
        self,
        reference_period_days: int = 365,
        current_window_days: int = 30,
        drift_threshold_p: float = 0.05,
        min_samples: int = 100,
    ):
        self.reference_period_days = reference_period_days
        self.current_window_days = current_window_days
        self.drift_threshold_p = drift_threshold_p
        self.min_samples = min_samples
    
    def detect_drift(
        self,
        symbol: str,
        recent_candles: List[Dict],  # OHLCV dicts with close prices
        metric: str = 'returns',  # 'returns' | 'volatility' | 'volume'
        reference_data: Optional[List[Dict]] = None,  # Pre-cached reference
    ) -> DriftDetectionResult:
        """
        Compare recent price distribution to reference (training) distribution.
        
        Args:
            symbol: Trading pair
            recent_candles: Current market data (last 30 days)
            metric: Which metric to test ('returns', 'volatility', 'volume')
            reference_data: Optional pre-computed reference stats (for speed)
        
        Returns:
            DriftDetectionResult with KS test verdict
        """
        
        # Extract metric values from recent candles
        if metric == 'returns':
            current_values = self._extract_returns(recent_candles)
        elif metric == 'volatility':
            current_values = self._extract_rolling_volatility(recent_candles, window=5)
        elif metric == 'volume':
            current_values = self._extract_volume(recent_candles)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        if len(current_values) < self.min_samples:
            logger.warning(
                f"{symbol}: only {len(current_values)} samples, "
                f"need {self.min_samples} for drift test"
            )
            return DriftDetectionResult(
                symbol=symbol,
                metric=metric,
                ks_statistic=0.0,
                p_value=1.0,  # Inconclusive
                drift_detected=False,
                ref_mean=0, ref_std=0,
                current_mean=float(np.mean(current_values)) if len(current_values) else 0.0,
                current_std=float(np.std(current_values)) if len(current_values) else 0.0,
                samples_ref=0,
                samples_current=len(current_values),
                timestamp=datetime.utcnow().isoformat(),
            )
        
        # Use reference data if provided, else assume normal distribution
        if reference_data is not None:
            if metric == 'returns':
                ref_values = self._extract_returns(reference_data)
            elif metric == 'volatility':
                ref_values = self._extract_rolling_volatility(reference_data, window=5)
            else:
                ref_values = self._extract_volume(reference_data)
            
            # KS test: two-sample
            ks_stat, p_value = stats.ks_2samp(ref_values, current_values)
            ref_mean, ref_std = np.mean(ref_values), np.std(ref_values)
            samples_ref = len(ref_values)
        else:
            # KS test against standard normal (assumes returns are normalized)
            ks_stat, p_value = stats.kstest(
                (current_values - np.mean(current_values)) / np.std(current_values),
                'norm'
            )
            ref_mean, ref_std = 0.0, 1.0
            samples_ref = 0
        
        drift_detected = p_value < self.drift_threshold_p
        
        result = DriftDetectionResult(
            symbol=symbol,
            metric=metric,
            ks_statistic=ks_stat,
            p_value=p_value,
            drift_detected=drift_detected,
            ref_mean=float(ref_mean),
            ref_std=float(ref_std),
            current_mean=float(np.mean(current_values)),
            current_std=float(np.std(current_values)),
            samples_ref=samples_ref,
            samples_current=len(current_values),
            timestamp=datetime.utcnow().isoformat(),
        )
        
        if drift_detected:
            logger.warning(
                f"DRIFT DETECTED on {symbol} ({metric}): "
                f"KS={ks_stat:.3f}, p={p_value:.4f} < {self.drift_threshold_p}\n"
                f"  Ref mean {ref_mean:.4f} ± {ref_std:.4f}\n"
                f"  Now mean {result.current_mean:.4f} ± {result.current_std:.4f}"
            )
        
        return result
    
    @staticmethod
    def _extract_returns(candles: List[Dict]) -> np.ndarray:
        """Log returns from OHLCV candles."""
        closes = [c.get('close', 0) for c in candles]
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                ret = np.log(closes[i] / closes[i-1])
                returns.append(ret)
        return np.array(returns)
    
    @staticmethod
    def _extract_rolling_volatility(
        candles: List[Dict], window: int = 5
    ) -> np.ndarray:
        """Rolling standard deviation of returns."""
        returns = ConceptDriftDetector._extract_returns(candles)
        vols = []
        for i in range(window, len(returns)):
            vol = np.std(returns[i-window:i])
            vols.append(vol)
        return np.array(vols)
    
    @staticmethod
    def _extract_volume(candles: List[Dict]) -> np.ndarray:
        """Extract volume series."""
        volumes = [c.get('volume', 0) for c in candles]
        return np.array(volumes)
    
    def monitor_dashboard(
        self,
        symbols: List[str],
        candle_fetcher,  # Callable to get recent candles
        reference_cache: Dict[str, List[Dict]],  # Pre-fetched reference data
    ) -> Dict[str, DriftDetectionResult]:
        """
        Called daily by learning_agent.py to scan all symbols for drift.
        
        Returns:
            {symbol: DriftDetectionResult, ...}
        """
        results = {}
        
        for symbol in symbols:
            recent_candles = candle_fetcher(symbol, days=self.current_window_days)
            ref_data = reference_cache.get(symbol)
            
            for metric in ['returns', 'volatility']:
                result = self.detect_drift(
                    symbol=symbol,
                    recent_candles=recent_candles,
                    metric=metric,
                    reference_data=ref_data,
                )
                
                key = f"{symbol}_{metric}"
                results[key] = result
                
                # Alert if drift detected
                if result.drift_detected:
                    logger.alert(
                        f"CONCEPT DRIFT: {symbol} {metric} "
                        f"(p={result.p_value:.4f}). "
                        f"Model retraining recommended."
                    )
        
        return results


# Integration example for learning_agent.py
"""
In daily_summary():

    detector = ConceptDriftDetector(
        reference_period_days=365,
        current_window_days=30,
        drift_threshold_p=0.05,
    )
    
    # Fetch reference distribution (1 year ago)
    reference_data = {
        symbol: db.get_candles(symbol, days=365)
        for symbol in SYMBOLS
    }
    
    drift_results = detector.monitor_dashboard(
        symbols=SYMBOLS,
        candle_fetcher=lambda sym, days: db.get_candles(sym, days=days),
        reference_cache=reference_data,
    )
    
    # Log alerts to Telegram
    for key, result in drift_results.items():
        if result.drift_detected:
            telegram.send(
                f"⚠️ DRIFT on {result.symbol} ({result.metric}): "
                f"KS p={result.p_value:.3f} < {detector.drift_threshold_p}. "
                f"Trigger model retrain?"
            )
    
    # Store results in DB for dashboard
    db.store_drift_checks(drift_results)
"""
