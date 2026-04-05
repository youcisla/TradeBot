"""
Walk-Forward Optimizer (from TensorTrade, BackTrader patterns)
- Rolling window optimization with continuous retraining
- Out-of-sample testing against holdout data
- Parameter stability analysis across rolling windows
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Callable
from datetime import datetime, timedelta
import pandas as pd


@dataclass
class WFOConfig:
    """Walk-forward optimization configuration"""
    train_window: int  # bars for training (e.g., 500)
    test_window: int   # bars for OOS testing (e.g., 50)
    reoptimize_freq: int  # reoptimize every N bars
    param_ranges: Dict[str, Tuple[float, float]]  # param: (min, max, step)


class WalkForwardOptimizer:
    """
    Rolling window optimizer that retrains every N bars.
    From: BackTrader, TensorTrade patterns
    """
    
    def __init__(self, config: WFOConfig):
        self.config = config
        self.window_results = []
        self.best_params = {}
        self.stability_score = 0.0
        
    def optimize_window(
        self,
        bars: pd.DataFrame,
        fitness_fn: Callable,
        start_idx: int
    ) -> Dict:
        """
        Optimize parameters on training window, test on holdout.
        
        Returns: {
            'train_pnl': float,
            'test_pnl': float,
            'parameters': dict,
            'stability': float,  # param consistency across windows
            'window_idx': int
        }
        """
        train_end = start_idx + self.config.train_window
        test_end = train_end + self.config.test_window
        
        if test_end > len(bars):
            return None
        
        train_data = bars.iloc[start_idx:train_end]
        test_data = bars.iloc[train_end:test_end]
        
        # Grid search or optimization on training window
        best_fit = None
        best_params = None
        
        for param_combo in self._generate_param_combinations():
            fit = fitness_fn(train_data, param_combo)
            if best_fit is None or fit > best_fit:
                best_fit = fit
                best_params = param_combo
        
        # Evaluate on holdout
        test_fit = fitness_fn(test_data, best_params)
        
        result = {
            'train_pnl': best_fit,
            'test_pnl': test_fit,
            'parameters': best_params,
            'overfitting_ratio': best_fit / abs(test_fit) if test_fit != 0 else 0,
            'window_idx': start_idx
        }
        
        self.window_results.append(result)
        return result
    
    def run_walk_forward(
        self,
        bars: pd.DataFrame,
        fitness_fn: Callable
    ) -> Dict:
        """
        Run WFO across entire dataset.
        
        Returns rolling metrics and parameter stability.
        """
        position = 0
        
        while position + self.config.train_window + self.config.test_window <= len(bars):
            self.optimize_window(bars, fitness_fn, position)
            position += self.config.reoptimize_freq
        
        # Analyze stability
        params_list = [r['parameters'] for r in self.window_results]
        self.stability_score = self._measure_param_stability(params_list)
        
        return {
            'avg_train_pnl': np.mean([r['train_pnl'] for r in self.window_results]),
            'avg_test_pnl': np.mean([r['test_pnl'] for r in self.window_results]),
            'avg_overfitting': np.mean([r['overfitting_ratio'] for r in self.window_results]),
            'parameter_stability': self.stability_score,
            'num_windows': len(self.window_results),
            'window_details': self.window_results
        }
    
    def _generate_param_combinations(self):
        """Generate parameter combinations for grid search"""
        param_names = list(self.config.param_ranges.keys())
        param_ranges = list(self.config.param_ranges.values())
        
        # Simple grid search
        ranges = []
        for pmin, pmax in param_ranges:
            ranges.append(np.linspace(pmin, pmax, 5))  # 5 levels per param
        
        import itertools
        for combo in itertools.product(*ranges):
            yield dict(zip(param_names, combo))
    
    def _measure_param_stability(self, params_list: List[Dict]) -> float:
        """
        Measure consistency of parameters across windows.
        High stability = robust parameters.
        """
        if len(params_list) < 2:
            return 0.0
        
        param_names = list(params_list[0].keys())
        stabilities = []
        
        for param_name in param_names:
            values = [p[param_name] for p in params_list]
            cv = np.std(values) / np.mean(np.abs(values)) if np.mean(np.abs(values)) > 0 else 0
            stabilities.append(1.0 / (1.0 + cv))  # normalize to [0, 1]
        
        return np.mean(stabilities)
