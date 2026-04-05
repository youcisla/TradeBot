"""
Walk-Forward Optimizer
======================
Rolling window optimization pattern from backtrader/QuantConnect.
Prevents overfitting by training on one period, testing on next.

Pattern: 1-year train window, 1-month test window, 2-week roll frequency.
This matches typical market regime cycles.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """One window in the walk-forward sequence."""
    train_start: str  # ISO format
    train_end: str
    test_start: str
    test_end: str
    window_idx: int


@dataclass
class WalkForwardResult:
    """Results from one train+test cycle."""
    window_idx: int
    train_start: str
    test_start: str
    train_metrics: Dict  # {'win_rate': 0.55, 'sharpe': 1.2, 'max_dd': -0.08, ...}
    test_metrics: Dict   # Same structure, but on out-of-sample data
    overfitting_bias: Dict  # {metric: (train_value - test_value)}
    optimal_params: Dict  # Best hyperparams found during train window
    
    def overfitting_score(self) -> float:
        """Degrees of overfitting: avg(|train - test| / test for each metric)."""
        if not self.overfitting_bias:
            return 0.0
        scores = []
        for metric, bias in self.overfitting_bias.items():
            test_val = self.test_metrics.get(metric, 1.0)
            if test_val != 0:
                scores.append(abs(bias) / abs(test_val))
        return sum(scores) / len(scores) if scores else 0.0


class WalkForwardOptimizer:
    """
    Orchestrates rolling window train/test cycles.
    
    Usage:
        optimizer = WalkForwardOptimizer(
            data_length_days=1000,
            train_window_days=365,
            test_window_days=30,
            roll_frequency_days=14
        )
        windows = optimizer.generate_windows()
        
        for window in windows:
            # Train neural model on data[train_start:train_end]
            # Test on data[test_start:test_end]
            # Record both metrics
    """
    
    def __init__(
        self,
        data_length_days: int,
        train_window_days: int = 365,
        test_window_days: int = 30,
        roll_frequency_days: int = 14,
    ):
        """
        Args:
            data_length_days: Total available data span
            train_window_days: Training period length (typically 1 year)
            test_window_days: Out-of-sample test length (typically 1 month)
            roll_frequency_days: Slide forward by this much after each cycle (2 weeks)
        """
        self.data_length_days = data_length_days
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.roll_frequency_days = roll_frequency_days
    
    def generate_windows(
        self, start_date: datetime = None
    ) -> List[WalkForwardWindow]:
        """Generate all train/test window pairs."""
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=self.data_length_days)
        
        windows = []
        window_idx = 0
        current_train_start = start_date
        
        while True:
            train_start = current_train_start
            train_end = train_start + timedelta(days=self.train_window_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_window_days)
            
            # Stop if test window runs past present
            if test_end > datetime.utcnow():
                break
            
            windows.append(WalkForwardWindow(
                train_start=train_start.isoformat(),
                train_end=train_end.isoformat(),
                test_start=test_start.isoformat(),
                test_end=test_end.isoformat(),
                window_idx=window_idx,
            ))
            
            current_train_start += timedelta(days=self.roll_frequency_days)
            window_idx += 1
        
        return windows
    
    def evaluate_results(self, results: List[WalkForwardResult]) -> Dict:
        """Aggregate across all windows to detect concept drift."""
        if not results:
            return {}
        
        # Average test performance across all windows
        avg_test_metrics = {}
        for metric_key in results[0].test_metrics.keys():
            values = [r.test_metrics[metric_key] for r in results]
            avg_test_metrics[metric_key] = sum(values) / len(values)
        
        # Track degradation over time (most recent vs. oldest)
        oldest_test = results[0].test_metrics
        newest_test = results[-1].test_metrics
        degradation = {}
        for key in oldest_test.keys():
            degradation[key] = oldest_test[key] - newest_test[key]
        
        # Detect acceleration in degradation (sign of drift)
        drift_detected = False
        if len(results) >= 3:
            recent_degradation = sum([
                r.overfitting_score() for r in results[-3:]
            ]) / 3
            older_degradation = sum([
                r.overfitting_score() for r in results[:3]
            ]) / 3
            drift_detected = recent_degradation > older_degradation * 1.5
        
        return {
            'window_count': len(results),
            'avg_test_metrics': avg_test_metrics,
            'total_degradation': degradation,
            'concept_drift_detected': drift_detected,
            'avg_overfitting_score': sum([r.overfitting_score() for r in results]) / len(results),
        }


def example_usage():
    """Demo: how to integrate WFO into neural_strategy.py training."""
    from datetime import datetime, timedelta
    
    optimizer = WalkForwardOptimizer(
        data_length_days=1000,
        train_window_days=365,
        test_window_days=30,
        roll_frequency_days=14,
    )
    
    windows = optimizer.generate_windows()
    all_results = []
    
    for window in windows:
        logger.info(f"WF Window {window.window_idx}: "
                   f"train [{window.train_start}:{window.train_end}], "
                   f"test [{window.test_start}:{window.test_end}]")
        
        # PSEUDOCODE:
        # train_data = db.fetch_candles(symbol, window.train_start, window.train_end)
        # test_data = db.fetch_candles(symbol, window.test_start, window.test_end)
        # 
        # # Hyperparameter grid search on train data
        # best_params = grid_search_lstm(train_data, param_grid={...})
        # 
        # # Evaluate best model on out-of-sample test data
        # train_metrics = evaluate_lstm(train_data, best_params)
        # test_metrics = evaluate_lstm(test_data, best_params)
        # 
        # result = WalkForwardResult(
        #     window_idx=window.window_idx,
        #     train_start=window.train_start,
        #     test_start=window.test_start,
        #     train_metrics=train_metrics,
        #     test_metrics=test_metrics,
        #     overfitting_bias={k: train_metrics[k] - test_metrics[k] 
        #                       for k in train_metrics},
        #     optimal_params=best_params,
        # )
        # all_results.append(result)
    
    # Summary across all windows
    summary = optimizer.evaluate_results(all_results)
    logger.info(f"WF Summary: {json.dumps(summary, indent=2)}")
    
    return all_results, summary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    example_usage()
