"""lgbm_price_model.py — Per-symbol LGBM classifiers trained on OHLCV bar features.

Each symbol gets its own model file: ``models/lgbm_price_{SYMBOL}.pkl``

Feature vector (12 features, pure-math from OHLCV + live context state):
  0   rsi_norm         RSI(14) / 100                  ∈ [0, 1]
  1   close_vs_ema20   (close - EMA20) / ATR           signed, clipped ±3
  2   close_vs_ema50   (close - EMA50) / ATR           signed, clipped ±3
  3   bb_pos           (close - BB_lower) / BB_range   clipped [0, 1]
  4   atr_ratio        ATR(14) / ATR(30)               vol vs recent avg
  5   vol_ratio        volume / mean_vol(20)            clipped [0, 5]
  6   ema9_slope       (EMA9 - EMA9_prev) / ATR        clipped ±2
  7   garch_vol        GARCH(1,1) cond. vol             0.0 if unavailable
  8   kalman_velocity  Kalman drift per tick            0.0 if unavailable
  9   session_enc      london=0, ny=1, asian=2, overlap=3, unknown=−1
 10   day_enc          Monday=0 … Sunday=6,             unknown=−1
 11   spread_norm      spread / ATR                     clipped [0, 1]

Labels (same convention as lgbm_ensemble.py):
  BUY=0  (long edge detected ahead)
  HOLD=1 (no clear directional edge)
  SELL=2 (short edge detected ahead)

Gated by ``settings.LGBM_ENSEMBLE_ENABLED``.  When disabled or when no model
file exists for the requested symbol, ``predict_from_context()`` returns a safe
HOLD / 0.50 default without raising.

Design constraints:
  - predict_from_context() never raises; fails open on any error
  - Model files are loaded lazily at first predict call per symbol
  - Thread-safe: lock wraps model dict reads/writes
  - Inference relies on MarketContext.candles (≥60 bars required)
  - garch_vol and kalman_velocity are filled from MarketContext at inference;
    they are set to 0.0 at training time because they require live filter state
"""

from __future__ import annotations

import logging
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.market_data import MarketContext

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_LABELS = ["BUY", "HOLD", "SELL"]   # class index → direction string

N_FEATURES = 12
FEATURE_NAMES = [
    "rsi_norm",
    "close_vs_ema20",
    "close_vs_ema50",
    "bb_pos",
    "atr_ratio",
    "vol_ratio",
    "ema9_slope",
    "garch_vol",
    "kalman_velocity",
    "session_enc",
    "day_enc",
    "spread_norm",
]

# Session / Day encoding — MUST match scripts/train_lgbm_price.py exactly
_SESSION_MAP: dict[str, float] = {
    "london": 0.0, "ny": 1.0, "new york": 1.0, "newyork": 1.0,
    "asian": 2.0, "asia": 2.0, "overlap": 3.0,
}
_DAY_MAP: dict[str, float] = {
    "monday": 0.0, "tuesday": 1.0, "wednesday": 2.0, "thursday": 3.0,
    "friday": 4.0, "saturday": 5.0, "sunday": 6.0,
}

# Minimum candles required so all features (including EMA50) are meaningful
_MIN_CANDLES = 60


# ── SHAP / feature-importance helper ─────────────────────────────────────────

def compute_shap_importance(
    model: object,
    X: list[list[float]],
    feature_names: list[str] | None = None,
) -> dict[str, float]:
    """Compute per-feature SHAP importance (mean |SHAP| across samples & classes).

    Uses the ``shap`` package when available; falls back to LightGBM gain-based
    importance.  Returns an empty dict on any error.
    The returned dict is ordered highest → lowest importance.

    This function is also callable from training scripts::

        from models.lgbm_price_model import compute_shap_importance
        imp = compute_shap_importance(model, X_train)
    """
    names = feature_names if feature_names is not None else FEATURE_NAMES

    try:
        import numpy as np
        import shap as _shap

        X_arr = np.array(X)
        explainer = _shap.TreeExplainer(model)
        sv = explainer.shap_values(X_arr)
        arr = np.array(sv) if isinstance(sv, list) else sv
        importance_arr = np.abs(arr).mean(axis=tuple(range(arr.ndim - 1)))
        n = len(importance_arr)
        return dict(
            sorted(zip(names[:n], importance_arr.tolist()), key=lambda t: -t[1])
        )
    except ImportError:
        logger.debug("shap not installed — falling back to LightGBM gain importance")
    except Exception as exc:
        logger.debug("SHAP computation failed: %s — falling back to gain importance", exc)

    # Fallback: LightGBM built-in gain importance
    try:
        gains = model.booster_.feature_importance(importance_type="gain")
        n = len(gains)
        return dict(
            sorted(zip(names[:n], [float(g) for g in gains]), key=lambda t: -t[1])
        )
    except Exception as exc:
        logger.debug("LightGBM gain fallback also failed: %s", exc)

    return {}


# ── Prediction dataclass (mirrors lgbm_ensemble.LGBMPrediction shape) ────────

@dataclass
class LGBMPrediction:
    """Price-model prediction — same shape as lgbm_ensemble.LGBMPrediction."""

    direction: str            # "BUY" | "SELL" | "HOLD"
    confidence: float         # winning class probability
    proba: dict[str, float]   # {"BUY": p, "HOLD": p, "SELL": p}
    model_trained: bool


# ── Pure-function feature helpers ─────────────────────────────────────────────


def _ema_series(values: list[float], period: int) -> list[float]:
    """Exponential moving average for all values.

    Initialised at the first element (same as pandas ewm(adjust=False)).
    Returns a list of the same length as *values*.
    """
    if not values:
        return []
    k = 2.0 / (period + 1)
    ema_val = values[0]
    result = [ema_val]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1.0 - k)
        result.append(ema_val)
    return result


def _rsi_last(closes: list[float], period: int = 14) -> float:
    """Simple RSI of the last *period* deltas."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    avg_gain = sum(x for x in recent if x > 0) / period
    avg_loss = sum(-x for x in recent if x < 0) / period or 1e-10
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _atr_last(candles: list, period: int = 14) -> float:
    """Simple rolling ATR (SMA of true range) at the last bar."""
    n = len(candles)
    if n < period + 1:
        return 0.0
    trs: list[float] = []
    for i in range(1, n):
        h, lo, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    recent = trs[-period:]
    return sum(recent) / len(recent) if recent else 0.0


def compute_features_from_context(ctx: "MarketContext") -> list[float] | None:
    """Build the 12-feature vector from a live MarketContext.

    Returns *None* when ``ctx.candles`` has fewer than ``_MIN_CANDLES`` bars —
    the caller should treat this as "insufficient data" and use the default
    HOLD prediction.

    This is the **inference path**.  garch_vol and kalman_velocity are taken
    directly from the context (populated by AnalysisAgent's stateful filters).
    """
    candles = ctx.candles
    if not candles or len(candles) < _MIN_CANDLES:
        return None

    closes = [c.close for c in candles]
    highs  = [c.high  for c in candles]
    lows   = [c.low   for c in candles]
    vols   = [c.volume for c in candles]

    # ── ATR ──────────────────────────────────────────────────────────────────
    atr14 = _atr_last(candles, 14)
    atr_safe = max(atr14, 1e-10)

    # ATR ratio: current 14-bar ATR vs 30-bar ATR (volatility regime signal)
    n_atrslow = min(30, len(candles) - 1)
    atr30 = _atr_last(candles, n_atrslow) if n_atrslow >= 14 else atr14
    atr_ratio = atr14 / max(atr30, 1e-10)

    # ── RSI ──────────────────────────────────────────────────────────────────
    # Use the pre-computed ctx.rsi when available (AnalysisAgent already did this).
    rsi_val = float(ctx.rsi) if ctx.rsi is not None and 0.0 < ctx.rsi < 100.0 else _rsi_last(closes, 14)
    rsi_norm = rsi_val / 100.0

    # ── EMA series ───────────────────────────────────────────────────────────
    ema9_s  = _ema_series(closes, 9)
    ema20_s = _ema_series(closes, 20)
    ema50_s = _ema_series(closes, 50)

    close_last = closes[-1]
    ema9_last   = ema9_s[-1]
    ema9_prev   = ema9_s[-2] if len(ema9_s) >= 2 else ema9_last
    close_vs_ema20 = max(-3.0, min(3.0, (close_last - ema20_s[-1]) / atr_safe))
    close_vs_ema50 = max(-3.0, min(3.0, (close_last - ema50_s[-1]) / atr_safe))

    # ── Bollinger Bands (20-period, 2σ population std) ───────────────────────
    bb_window = closes[-20:]
    bb_mean   = sum(bb_window) / len(bb_window)
    bb_var    = sum((x - bb_mean) ** 2 for x in bb_window) / len(bb_window)
    bb_std2   = bb_var ** 0.5 * 2.0
    bb_upper  = bb_mean + bb_std2
    bb_lower  = bb_mean - bb_std2
    bb_range  = max(bb_upper - bb_lower, 1e-10)
    bb_pos    = max(0.0, min(1.0, (close_last - bb_lower) / bb_range))

    # ── Volume ratio ─────────────────────────────────────────────────────────
    vol_last   = vols[-1] if vols else 0.0
    vol_mean20 = sum(vols[-20:]) / min(len(vols), 20) or 1e-10
    vol_ratio  = min(vol_last / vol_mean20, 5.0)

    # ── EMA9 slope (normalised by ATR) ───────────────────────────────────────
    ema9_slope = max(-2.0, min(2.0, (ema9_last - ema9_prev) / atr_safe))

    # ── Runtime ML fields (zero at training; live at inference) ──────────────
    garch_vol       = float(ctx.garch_vol       or 0.0)
    kalman_velocity = float(ctx.kalman_velocity or 0.0)

    # ── Session / Day ─────────────────────────────────────────────────────────
    session_enc = _SESSION_MAP.get((ctx.session     or "").lower().strip(), -1.0)
    day_enc     = _DAY_MAP.get(   (ctx.day_of_week or "").lower().strip(), -1.0)

    # ── Spread ───────────────────────────────────────────────────────────────
    spread_norm = min(float(ctx.spread or 0.0) / atr_safe, 1.0)

    return [
        rsi_norm,           # 0
        close_vs_ema20,     # 1
        close_vs_ema50,     # 2
        bb_pos,             # 3
        atr_ratio,          # 4
        vol_ratio,          # 5
        ema9_slope,         # 6
        garch_vol,          # 7
        kalman_velocity,    # 8
        session_enc,        # 9
        day_enc,            # 10
        spread_norm,        # 11
    ]


# ── Model class ───────────────────────────────────────────────────────────────


class LGBMPriceModel:
    """Container for per-symbol LGBM classifiers trained on bar-level features.

    Each symbol is stored under a normalised key derived from the symbol string
    (e.g. ``EURUSD`` → key ``EURUSD``, file ``models/lgbm_price_EURUSD.pkl``).

    Usage::

        from models.lgbm_price_model import LGBMPriceModel
        price_model = LGBMPriceModel()
        pred = price_model.predict_from_context(ctx)
        print(pred.direction, pred.confidence, pred.model_trained)
    """

    def __init__(self) -> None:
        self._lock   = threading.Lock()
        self._models: dict[str, object] = {}   # safe_key → fitted LGBMClassifier
        self._shap_importance: dict[str, dict[str, float]] = {}  # safe_key → importance
        self._enabled: bool = self._check_enabled()
        # Lazy-load: models are loaded on first use, not at startup.
        # This avoids a 2+ second delay from loading 20+ models sequentially.

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _check_enabled() -> bool:
        try:
            from config import settings
            return bool(getattr(settings, "LGBM_ENSEMBLE_ENABLED", False))
        except Exception:
            return False

    @staticmethod
    def _sym_key(symbol: str) -> str:
        """Normalise a symbol string to a safe file-key (upper-case, no slashes)."""
        return (symbol or "").replace("/", "_").replace("\\", "_").replace(".", "_").upper()

    @classmethod
    def _model_path(cls, symbol: str) -> Path:
        safe = cls._sym_key(symbol)
        return Path("models") / f"lgbm_price_{safe}.pkl"

    def _load_available_models(self) -> None:
        """Scan ``models/`` and load every ``lgbm_price_*.pkl`` found."""
        model_dir = Path("models")
        if not model_dir.exists():
            return
        for pkl in sorted(model_dir.glob("lgbm_price_*.pkl")):
            key = pkl.stem.replace("lgbm_price_", "").upper()
            try:
                with open(pkl, "rb") as fh:
                    self._models[key] = pickle.load(fh)
                logger.info("Price-LGBM loaded: %s (%s)", key, pkl.name)
            except Exception as exc:
                logger.warning("Could not load price-LGBM %s: %s", pkl, exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def _lazy_load(self, symbol: str) -> bool:
        """Load a single symbol's model on demand. Returns True if loaded."""
        key = self._sym_key(symbol)
        if key in self._models:
            return True  # already loaded
        path = self._model_path(symbol)
        if not path.exists():
            return False
        try:
            with open(path, "rb") as fh:
                self._models[key] = pickle.load(fh)  # noqa: S301
            logger.debug("Price-LGBM lazy-loaded: %s", key)
            return True
        except Exception as exc:
            logger.debug("Could not lazy-load price-LGBM %s: %s", path, exc)
            return False

    def is_trained(self, symbol: str) -> bool:
        """Return True if a model has been loaded for *symbol*."""
        key = self._sym_key(symbol)
        if key in self._models:
            return True
        # Try to lazy-load on first check
        return self._lazy_load(symbol)

    def symbols_trained(self) -> list[str]:
        """List all symbol keys with a loaded model."""
        with self._lock:
            return list(self._models)

    def save_model(
        self,
        symbol: str,
        model: object,
        X_train: list[list[float]] | None = None,
    ) -> None:
        """Persist *model* to disk and register it in the in-memory store.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g. ``"EURUSD"``).
        model : fitted LGBMClassifier
            The trained model to persist.
        X_train : list of feature vectors, optional
            When provided, SHAP feature importance is computed immediately
            after saving and stored via ``get_shap_importance(symbol)``.
        """
        path = self._model_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
        key = self._sym_key(symbol)
        with self._lock:
            self._models[key] = model
        logger.info("Saved price-LGBM for %s → %s", symbol, path)

        # ── SHAP feature importance ────────────────────────────────────────
        if X_train is not None:
            importance = compute_shap_importance(model, X_train)
            with self._lock:
                self._shap_importance[key] = importance
            if importance:
                top5 = list(importance.items())[:5]
                logger.info(
                    "Price-LGBM SHAP top-5 features for %s: %s", symbol, top5
                )

    def get_shap_importance(self, symbol: str | None = None) -> dict[str, float]:
        """Return the SHAP importance dict for *symbol*.

        Parameters
        ----------
        symbol : str or None
            Symbol to look up.  When *None* and only one symbol has been
            trained, returns that symbol's importance.

        Returns
        -------
        dict
            ``{feature_name: mean_abs_shap}``, ordered highest → lowest.
            Empty dict when SHAP has not been computed for this symbol.
        """
        with self._lock:
            if symbol is None:
                if len(self._shap_importance) == 1:
                    return dict(next(iter(self._shap_importance.values())))
                return {}
            return dict(self._shap_importance.get(self._sym_key(symbol), {}))

    @staticmethod
    def _default_prediction() -> LGBMPrediction:
        return LGBMPrediction(
            direction="HOLD",
            confidence=0.50,
            proba={"BUY": 0.33, "HOLD": 0.34, "SELL": 0.33},
            model_trained=False,
        )

    def predict_from_context(self, ctx: "MarketContext") -> LGBMPrediction:
        """Classify current bar as BUY / HOLD / SELL from a MarketContext.

        Returns the safe default (HOLD / 0.50 / model_trained=False) when:
          - LGBM_ENSEMBLE_ENABLED is False
          - No model has been trained for ctx.symbol
          - ctx.candles has fewer than _MIN_CANDLES bars
          - Any exception occurs during feature computation or inference

        Never raises.
        """
        if not self._enabled:
            return self._default_prediction()

        key = self._sym_key(ctx.symbol)
        # Lazy-load the first time this symbol is requested
        self._lazy_load(ctx.symbol)

        with self._lock:
            model = self._models.get(key)

        if model is None:
            return self._default_prediction()

        try:
            features = compute_features_from_context(ctx)
            if features is None:
                return self._default_prediction()

            # Wrap in a DataFrame so sklearn sees feature names — suppresses warning.
            import pandas as _pd
            proba = model.predict_proba(_pd.DataFrame([features], columns=FEATURE_NAMES))[0]
            idx   = int(proba.argmax())
            return LGBMPrediction(
                direction=_LABELS[idx],
                confidence=float(proba[idx]),
                proba={
                    "BUY":  float(proba[0]),
                    "HOLD": float(proba[1]),
                    "SELL": float(proba[2]),
                },
                model_trained=True,
            )
        except Exception as exc:
            logger.debug("LGBMPriceModel.predict_from_context failed: %s", exc)
            return self._default_prediction()
