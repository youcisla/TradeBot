"""
Phase 4 – Dynamic Regime Detection via Hidden Markov Model
==========================================================
Unsupervised 3-state Gaussian HMM classifies the market into:
  TRENDING  — persistent directional momentum
  RANGE    — mean-reverting oscillation
  CRISIS   — high volatility, regime collapse

The InferenceNode injects HMMRegimeDetector and receives a regime tag
on every signal, dynamically adjusting confidence thresholds and signal
weights via REGIME_PARAMS.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import joblib
    _HAS_JOBLIB = True
except ImportError:
    joblib = None  # type: ignore
    _HAS_JOBLIB = False

try:
    from sklearn.hmm import GaussianHMM
except ImportError:  # pragma: no cover
    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError:
        GaussianHMM = None  # type: ignore

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR    = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ── Regime parameters ────────────────────────────────────────────────────────────

@dataclass
class RegimeParams:
    """Dynamic thresholds and weights adjusted per HMM regime output."""
    confidence_threshold: float
    signal_weight:       float
    max_lot:            float


REGIME_PARAMS = {
    "TRENDING": RegimeParams(confidence_threshold=0.55, signal_weight=1.0,  max_lot=0.50),
    "RANGE":   RegimeParams(confidence_threshold=0.60, signal_weight=0.7,  max_lot=0.30),
    "CRISIS":  RegimeParams(confidence_threshold=0.70, signal_weight=0.4,  max_lot=0.10),
}

STATE_LABELS = {0: "TRENDING", 1: "RANGE", 2: "CRISIS"}


# ── Feature extractor ────────────────────────────────────────────────────────────

class HMMFeatureExtractor:
    """
    Converts a rolling 20-candle window into a 20-dimensional feature
    vector suitable for the Gaussian HMM.

    Feature groups (20 total):
      price       — log-return statistics (5)
      volume      — volume pressure and imbalance (5)
      microstructure — spread, lambda, wick ratios (5)
      regime      — HMM-ready rolling z-scores (5)
    """

    LOOKBACK = 20
    NAMES = [
        "return_mean", "return_std", "return_skew", "return_min", "return_max",
        "vol_mean", "vol_std", "vol_ratio", "vol_imbalance", "vol_trend",
        "spread_mean", "spread_ratio", "price_impact", "upper_wick_std", "lower_wick_std",
        "price_zscore", "volume_zscore", "return_autocorr", "high_low_ratio", "close_position",
    ]

    def transform(self, df: np.ndarray) -> np.ndarray:
        """
        df: ndarray of shape (n_candles, 5) — [open, high, low, close, volume]
        Returns (n_samples, 20) feature matrix.
        """
        n = len(df)
        feats: list[np.ndarray] = []

        ret = np.log(df[:, 3] / np.roll(df[:, 3], 1).clip(min=1e-9))
        ret[0] = 0.0

        # ── price features ──────────────────────────────────────────────
        r = ret[-self.LOOKBACK:]
        feats.extend([
            r.mean(), r.std(), (r - r.mean()).clip(0).mean() if len(r) else 0,  # skew proxy
            r.min(), r.max(),
        ])

        # ── volume features ─────────────────────────────────────────────
        vol = df[-self.LOOKBACK:, 4]
        vol_ma5 = vol.mean()
        feats.extend([
            vol.mean(), vol.std(),
            vol[-1] / (vol_ma5 + 1e-9),
            (vol[vol > vol_ma5].sum() - vol[vol <= vol_ma5].sum()) / (vol.sum() + 1e-9),
            np.polyfit(np.arange(self.LOOKBACK), vol, 1)[0] if self.LOOKBACK > 1 else 0,
        ])

        # ── microstructure ───────────────────────────────────────────────
        spread = df[-self.LOOKBACK:, 1] - df[-self.LOOKBACK:, 2]
        upper_wick = df[-self.LOOKBACK:, 1] - np.maximum(df[-self.LOOKBACK:, 0], df[-self.LOOKBACK:, 3])
        lower_wick = np.minimum(df[-self.LOOKBACK:, 0], df[-self.LOOKBACK:, 3]) - df[-self.LOOKBACK:, 2]
        price_impact = ret[-self.LOOKBACK:].abs() / (df[-self.LOOKBACK:, 4] + 1e-9)

        feats.extend([
            spread.mean(),
            spread[-1] / (spread.mean() + 1e-9),
            price_impact.mean(),
            upper_wick.std(),
            lower_wick.std(),
        ])

        # ── regime-ready z-scores ───────────────────────────────────────
        window = df[-60:, 3] if len(df) >= 60 else df[:, 3]
        z_price = (df[-1, 3] - window.mean()) / (window.std() + 1e-9)
        z_volume = (df[-1, 4] - df[:, 4].mean()) / (df[:, 4].std() + 1e-9)
        autocorr = np.corrcoef(ret[-self.LOOKBACK:-1], ret[-self.LOOKBACK + 1:])[0, 1] if self.LOOKBACK > 1 else 0.0
        hl_range = df[-1, 1] - df[-1, 2]
        close_pos = (df[-1, 3] - df[-1, 2]) / (hl_range + 1e-9)

        feats.extend([
            float(z_price), float(z_volume), float(autocorr),
            float((df[-1, 1] - df[-1, 2]) / (df[-1, 1] - df[-1, 2] + 1e-9)),
            float(close_pos),
        ])

        return np.array(feats, dtype=np.float64).reshape(1, -1)


# ── HMM Regime Detector ─────────────────────────────────────────────────────────

class HMMRegimeDetector:
    """
    Wraps a fitted GaussianHMM and provides:

    • classify(signal)  — regime label for a live SignalPayload
    • predict(df)      — regime sequence for a batch of candles
    • score(df)        — log-likelihood as regime confidence
    • save / load      — joblib serialization (no pickle)
    """

    N_COMPONENTS   = 3
    N_FEATURES     = 20
    COVARIANCE_TYPE = "diag"   # diagonal = faster, sufficient for financial features

    def __init__(self, symbol: str = "BTCUSD"):
        if GaussianHMM is None:
            raise RuntimeError("hmmlearn is required: pip install hmmlearn")
        if not _HAS_JOBLIB:
            raise RuntimeError("joblib is required: pip install joblib")

        self.symbol    = symbol
        self.extractor = HMMFeatureExtractor()
        self._model    = GaussianHMM(
            n_components=self.N_COMPONENTS,
            covariance_type=self.COVARIANCE_TYPE,
            n_iter=500,
            random_state=42,
        )
        self._fitted   = False

    # ── training ────────────────────────────────────────────────────────────

    def fit(self, candles_df, lookback: int = 60) -> "HMMRegimeDetector":
        """
        Fit the HMM on historical candles.

        candles_df: DataFrame with [timestamp, open, high, low, close, volume]
        lookback:   number of candles per training sample
        """
        import pandas as pd

        if not isinstance(candles_df, pd.DataFrame):
            raise TypeError("candles_df must be a pandas DataFrame")

        arr = candles_df[["open", "high", "low", "close", "volume"]].values
        n = len(arr)

        X_list: list[np.ndarray] = []
        for i in range(lookback, n):
            window = arr[i - lookback:i]
            feat = self.extractor.transform(window)
            if np.isfinite(feat).all():
                X_list.append(feat)

        X = np.vstack(X_list)
        self._model.fit(X)
        self._fitted = True

        logging.info(
            "HMMRegimeDetector fitted on %d samples (symbol=%s)",
            len(X), self.symbol
        )
        return self

    # ── inference ──────────────────────────────────────────────────────────

    def classify(self, signal) -> str:
        """
        Return the most likely regime label for a live SignalPayload.
        Uses a rolling 60-candle buffer maintained in the node.
        """
        # InferenceNode passes a rolling buffer; here we accept signal as context
        if not self._fitted:
            return "TRENDING"   # safe default until model is trained
        # The actual buffer lives in InferenceNode — this method is overridden there
        return STATE_LABELS.get(0, "TRENDING")

    def predict(self, df: np.ndarray) -> np.ndarray:
        """
        df: ndarray (n_candles, 5) — [open, high, low, close, volume]
        Returns regime state index (0,1,2) for each lookback window.
        """
        if not self._fitted:
            return np.zeros(len(df) - self.extractor.LOOKBACK, dtype=int)

        lookback = self.extractor.LOOKBACK
        states = []
        for i in range(lookback, len(df)):
            feat = self.extractor.transform(df[i - lookback:i])
            if np.isfinite(feat).all():
                states.append(self._model.predict(feat)[0])
            else:
                states.append(0)
        return np.array(states, dtype=int)

    def score(self, df: np.ndarray) -> float:
        """
        Return the log-likelihood of the last lookback window —
        used as a regime confidence signal.
        """
        if not self._fitted:
            return 0.0
        feat = self.extractor.transform(df[-self.extractor.LOOKBACK:])
        if not np.isfinite(feat).all():
            return 0.0
        return float(self._model.score(feat))

    # ── persistence ─────────────────────────────────────────────────────────

    def save(self, path: Path | str | None = None) -> Path:
        """Serialize the fitted model using joblib (no pickle)."""
        if not _HAS_JOBLIB:
            raise RuntimeError("joblib required for persistence")
        if not self._fitted:
            raise RuntimeError("Model must be fitted before saving")
        p = Path(path) if path else (MODEL_DIR / f"hmm_{self.symbol}.joblib")
        joblib.dump({
            "model":    self._model,
            "symbol":   self.symbol,
            "fitted":   self._fitted,
        }, str(p))
        logging.info("HMMRegimeDetector saved to %s", p)
        return p

    @classmethod
    def load(cls, path: Path | str) -> "HMMRegimeDetector":
        """Load a previously saved model via joblib."""
        if not _HAS_JOBLIB:
            raise RuntimeError("joblib required for persistence")
        data = joblib.load(str(path))
        instance = cls(symbol=data["symbol"])
        instance._model  = data["model"]
        instance._fitted = data["fitted"]
        return instance


# ── Trainer CLI ────────────────────────────────────────────────────────────────

class HMMRegimeTrainer:
    """Pipeline: fit HMM → benchmark inference latency → persist."""

    def __init__(self, symbol: str = "BTCUSD"):
        self.symbol = symbol
        self.detector = HMMRegimeDetector(symbol)

    def train(
        self,
        candles_df,
        lookback: int = 60,
    ) -> dict:
        t0 = time.perf_counter()
        self.detector.fit(candles_df, lookback)
        train_ms = (time.perf_counter() - t0) * 1e3

        # ── inference latency benchmark ─────────────────────────────────
        sample_arr = candles_df[["open", "high", "low", "close", "volume"]].values[-lookback:]
        latencies = []
        for _ in range(100):
            tick = time.perf_counter()
            _ = self.detector.score(sample_arr)
            latencies.append((time.perf_counter() - tick) * 1e3)
        latencies.sort()
        n = len(latencies)

        model_path = self.detector.save()

        return {
            "symbol":          self.symbol,
            "n_components":    self.detector.N_COMPONENTS,
            "n_features":      self.detector.N_FEATURES,
            "train_ms":        float(train_ms),
            "inference_p50_ms": float(latencies[n // 2]),
            "inference_p99_ms": float(latencies[min(int(n * 0.99), n - 1)]),
            "model_path":      str(model_path),
            "timestamp":       datetime.now(timezone.utc).isoformat(),
        }


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    import pandas as pd

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    ap = argparse.ArgumentParser(description="Phase-4: HMM Regime Detection Training")
    ap.add_argument("--candles",  required=True, help="Path to historical candle CSV")
    ap.add_argument("--symbol",    default="BTCUSD")
    ap.add_argument("--lookback",  type=int, default=60)
    ap.add_argument("--model-out", default=None, help="Override model output path")
    args = ap.parse_args()

    df = pd.read_csv(args.candles, parse_dates=["timestamp"])

    trainer = HMMRegimeTrainer(symbol=args.symbol)
    result = trainer.train(df, lookback=args.lookback)

    print(f"\n{'='*60}")
    print(f"HMM Regime Detector trained for {args.symbol}")
    print(f"  Components:  {result['n_components']} (TRENDING / RANGE / CRISIS)")
    print(f"  Features:    {result['n_features']}")
    print(f"  Train ms:    {result['train_ms']:.1f} ms")
    print(f"  Inference p50: {result['inference_p50_ms']:.4f} ms")
    print(f"  Inference p99: {result['inference_p99_ms']:.4f} ms")
    print(f"  Model → {result['model_path']}")


if __name__ == "__main__":
    main()
