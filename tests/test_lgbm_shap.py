"""Tests for SHAP feature importance in LGBM models.

Guards the compute_shap_importance helpers and the wiring into
LGBMEnsemble.train() / LGBMPriceModel.save_model().
"""

from __future__ import annotations

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_tiny_dataset(n_features: int = 3) -> tuple[list[list[float]], list[int]]:
    """Return a minimal 3-class dataset (3 samples per class, n_features features)."""
    X = [[float(i + j) for j in range(n_features)] for i in range(9)]
    y = [0, 1, 2] * 3  # balanced, 3 samples per class
    return X, y


def _try_import_lightgbm():
    try:
        import lightgbm as lgb  # noqa: F401
    except ImportError:
        pytest.skip("lightgbm not installed")


def _train_tiny_lgbm(n_features: int = 3):
    """Fit a minimal LGBMClassifier for unit tests."""
    _try_import_lightgbm()
    from lightgbm import LGBMClassifier

    X, y = _make_tiny_dataset(n_features)
    clf = LGBMClassifier(n_estimators=5, num_leaves=4, verbose=-1)
    clf.fit(X, y)
    return clf, X, y


# ── compute_shap_importance (price model) ────────────────────────────────────

class TestComputeShapImportance:
    def test_returns_dict_with_feature_names(self):
        _try_import_lightgbm()
        from models.lgbm_price_model import compute_shap_importance

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        result = compute_shap_importance(clf, X, feature_names=["alpha", "beta", "gamma"])

        assert isinstance(result, dict)
        assert set(result.keys()) == {"alpha", "beta", "gamma"}

    def test_all_values_are_non_negative_floats(self):
        _try_import_lightgbm()
        from models.lgbm_price_model import compute_shap_importance

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        result = compute_shap_importance(clf, X)

        for v in result.values():
            assert isinstance(v, float)
            assert v >= 0.0

    def test_ordered_highest_to_lowest(self):
        _try_import_lightgbm()
        from models.lgbm_price_model import compute_shap_importance

        clf, X, _ = _train_tiny_lgbm(n_features=4)
        result = compute_shap_importance(clf, X, feature_names=["a", "b", "c", "d"])

        values = list(result.values())
        assert values == sorted(values, reverse=True)

    def test_uses_fallback_feature_names_when_omitted(self):
        _try_import_lightgbm()
        from models.lgbm_price_model import compute_shap_importance

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        # No feature_names passed → should use FEATURE_NAMES for price model
        result = compute_shap_importance(clf, X)

        assert isinstance(result, dict)
        assert len(result) > 0


# ── LGBMEnsemble SHAP wiring ─────────────────────────────────────────────────

class TestLGBMEnsembleShap:
    def test_shap_importance_empty_before_training(self, monkeypatch):
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)

        from models.lgbm_ensemble import LGBMEnsemble

        model = LGBMEnsemble()
        assert model.get_shap_importance() == {}

    def test_shap_importance_populated_after_training(self, monkeypatch):
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)

        from models.lgbm_ensemble import LGBMEnsemble

        model = LGBMEnsemble()
        X, y = _make_tiny_dataset(n_features=4)
        success = model.train(X, y)

        assert success is True
        importance = model.get_shap_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0

    def test_get_shap_importance_returns_copy(self, monkeypatch):
        """Mutating the returned dict should not corrupt internal state."""
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)

        from models.lgbm_ensemble import LGBMEnsemble

        model = LGBMEnsemble()
        X, y = _make_tiny_dataset(n_features=3)
        model.train(X, y)

        result = model.get_shap_importance()
        result["injected"] = 999.0
        assert "injected" not in model.get_shap_importance()


# ── LGBMPriceModel SHAP wiring ───────────────────────────────────────────────

class TestLGBMPriceModelShap:
    def test_shap_computed_when_x_train_provided(self, tmp_path, monkeypatch):
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)
        # Redirect model saves to tmp_path so we don't pollute the real models/ dir
        monkeypatch.chdir(tmp_path)

        from models.lgbm_price_model import LGBMPriceModel

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        price_model = LGBMPriceModel()
        price_model.save_model("EURUSD", clf, X_train=X)

        importance = price_model.get_shap_importance("EURUSD")
        assert isinstance(importance, dict)
        assert len(importance) > 0

    def test_shap_empty_when_no_x_train(self, tmp_path, monkeypatch):
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)
        monkeypatch.chdir(tmp_path)

        from models.lgbm_price_model import LGBMPriceModel

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        price_model = LGBMPriceModel()
        price_model.save_model("EURUSD", clf)  # no X_train

        importance = price_model.get_shap_importance("EURUSD")
        assert importance == {}

    def test_shap_independent_per_symbol(self, tmp_path, monkeypatch):
        _try_import_lightgbm()
        from config import settings as _settings
        monkeypatch.setattr(_settings, "LGBM_ENSEMBLE_ENABLED", True)
        monkeypatch.chdir(tmp_path)

        from models.lgbm_price_model import LGBMPriceModel

        clf, X, _ = _train_tiny_lgbm(n_features=3)
        price_model = LGBMPriceModel()
        price_model.save_model("EURUSD", clf, X_train=X)
        price_model.save_model("GBPUSD", clf)  # no X_train

        assert len(price_model.get_shap_importance("EURUSD")) > 0
        assert price_model.get_shap_importance("GBPUSD") == {}
