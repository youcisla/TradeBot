"""lgbm_ensemble.py — LightGBM 3-class ensemble (BUY / SELL / HOLD).

Combines macro feature vectors (from ``features/macro_features.py``) and
microstructure feature vectors (from ``features/microstructure.py``) into a
single prediction head trained with LightGBM gradient boosting.

Gated by ``settings.LGBM_ENSEMBLE_ENABLED``. When disabled (or when the model
has not been trained yet), it safely returns HOLD with 0.50 confidence.

Design constraints:
    - Never raises outside of __init__; all methods return safe defaults
    - Model is saved/loaded from ``models/lgbm_model.pkl``
    - Training can be triggered manually or via the LearningAgent
    - Thread-safe: predict() / update() use a lock

Usage::

    from models.lgbm_ensemble import LGBMEnsemble, LGBMPrediction

    model = LGBMEnsemble()
    pred = model.predict(macro_vec=[...], micro_vec=[...])
    print(pred.direction, pred.confidence)
"""

from __future__ import annotations

import logging
import os
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_MODEL_PATH = Path("models") / "lgbm_model.pkl"
_LABELS = ["BUY", "HOLD", "SELL"]   # class indices 0, 1, 2


@dataclass
class LGBMPrediction:
    direction: str          # "BUY" | "SELL" | "HOLD"
    confidence: float       # class probability of winning class
    proba: dict[str, float] # {"BUY": p, "HOLD": p, "SELL": p}
    model_trained: bool


class LGBMEnsemble:
    """LightGBM ensemble for direction + confidence prediction."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None          # lgb.Booster or sklearn wrapper
        self._enabled: bool = self._check_enabled()
        self._trained: bool = False

        if self._enabled:
            self._try_load_model()

    # ── Public API ────────────────────────────────────────────────────────

    def predict(
        self,
        macro_vec: Sequence[float],
        micro_vec: Sequence[float],
    ) -> LGBMPrediction:
        """Predict trade direction and confidence from feature vectors.

        Returns HOLD / 0.50 when the model is disabled or not trained.
        """
        if not self._enabled or not self._trained or self._model is None:
            return self._default_prediction()

        with self._lock:
            try:
                X = self._build_input(macro_vec, micro_vec)
                proba = self._model.predict_proba([X])[0]   # shape (3,)
                idx = int(proba.argmax())
                return LGBMPrediction(
                    direction=_LABELS[idx],
                    confidence=float(proba[idx]),
                    proba={
                        "BUY": float(proba[0]),
                        "HOLD": float(proba[1]),
                        "SELL": float(proba[2]),
                    },
                    model_trained=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("LGBMEnsemble.predict failed: %s", exc)
                return self._default_prediction()

    def train(
        self,
        X: Sequence[Sequence[float]],
        y: Sequence[int],
    ) -> bool:
        """Train the ensemble on historical feature+label data.

        Parameters
        ----------
        X : 2-D array-like of shape (n_samples, n_features)
        y : 1-D label array (0=BUY, 1=HOLD, 2=SELL)

        Returns True on success, False on error.
        """
        if not self._enabled:
            logger.debug("LGBMEnsemble.train: disabled, skipping")
            return False

        try:
            lgb = self._import_lgb()
            if lgb is None:
                return False

            clf = lgb.LGBMClassifier(
                n_estimators=300,
                learning_rate=0.05,
                num_leaves=31,
                feature_fraction=0.8,
                bagging_fraction=0.8,
                bagging_freq=5,
                class_weight="balanced",
                verbose=-1,
            )
            clf.fit(list(X), list(y))

            with self._lock:
                self._model = clf
                self._trained = True

            self._save_model(clf)
            logger.info("LGBMEnsemble trained on %d samples", len(list(y)))
            return True

        except Exception as exc:  # noqa: BLE001
            logger.warning("LGBMEnsemble.train error: %s", exc)
            return False

    def update(
        self,
        macro_vec: Sequence[float],
        micro_vec: Sequence[float],
        label: int,
    ) -> None:
        """Online update stub — reserved for future warm-start logic."""
        # LightGBM supports continue_training; implement when needed
        pass  # noqa: PIE790

    @property
    def is_ready(self) -> bool:
        return self._enabled and self._trained

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _check_enabled() -> bool:
        try:
            from config import settings
            return bool(getattr(settings, "LGBM_ENSEMBLE_ENABLED", False))
        except Exception:  # noqa: BLE001
            return False

    def _try_load_model(self) -> None:
        if not _MODEL_PATH.exists():
            logger.debug("LGBMEnsemble: no saved model at %s", _MODEL_PATH)
            return
        try:
            with open(_MODEL_PATH, "rb") as fh:
                self._model = pickle.load(fh)  # noqa: S301
            self._trained = True
            logger.info("LGBMEnsemble loaded from %s", _MODEL_PATH)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LGBMEnsemble: failed to load model: %s", exc)

    def _save_model(self, clf: object) -> None:
        try:
            _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_MODEL_PATH, "wb") as fh:
                pickle.dump(clf, fh)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LGBMEnsemble: could not save model: %s", exc)

    @staticmethod
    def _import_lgb():
        try:
            import lightgbm as lgb
            return lgb
        except ImportError:
            logger.warning("lightgbm not installed; pip install lightgbm")
            return None

    @staticmethod
    def _build_input(
        macro_vec: Sequence[float],
        micro_vec: Sequence[float],
    ) -> list[float]:
        return list(macro_vec) + list(micro_vec)

    @staticmethod
    def _default_prediction() -> LGBMPrediction:
        return LGBMPrediction(
            direction="HOLD",
            confidence=0.50,
            proba={"BUY": 0.333, "HOLD": 0.334, "SELL": 0.333},
            model_trained=False,
        )
