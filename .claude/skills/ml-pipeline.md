# Skill: ml-pipeline

Covers the new ML/signal-enrichment stack added in the P0/P1 implementation sprint.

---

## Files

| File | Purpose |
|---|---|
| `features/macro_features.py` | Builds a fixed 15-float z-scored macro feature vector from a `MacroSnapshot` |
| `features/microstructure.py` | Computes spread, imbalance, Kyle's lambda, wick asymmetry per bar |
| `models/lgbm_ensemble.py` | LightGBM 3-class classifier (BUY / SELL / HOLD) gated by `LGBM_ENSEMBLE_ENABLED` |
| `models/garch_regime.py` | GARCH(1,1) + EWMA regime detector ("low"/"normal"/"high"/"extreme") |
| `utils/kalman_filter.py` | 2D constant-velocity Kalman price smoother |

---

## Feature Pipeline

```
MacroSnapshot (IntelligenceSweep)
    └─► MacroFeatureBuilder.build()  →  MacroFeatureVector (15 floats, z-scored)
                                              │
Bar OHLCV                                     │
    └─► MicrostructureFeatures.compute() →  MicroBarFeatures (6 floats)
                                              │
                                        LGBMEnsemble.predict(macro_vec, micro_vec)
                                              │
                                        LGBMPrediction(direction, confidence, proba)
```

---

## Usage Pattern

```python
from features.macro_features import MacroFeatureBuilder
from features.microstructure import MicrostructureFeatures
from models.lgbm_ensemble import LGBMEnsemble

macro_builder = MacroFeatureBuilder()
micro_feats   = MicrostructureFeatures()
ensemble      = LGBMEnsemble()

# On every completed bar:
snap = intelligence_sweep.get_latest()
mv   = macro_builder.build(snap)
mf   = micro_feats.compute(open=o, high=h, low=l, close=c, volume=v)

pred = ensemble.predict(mv.values, mf.to_list())
# pred.direction in {"BUY", "SELL", "HOLD"}
# pred.confidence in [0.0, 1.0]
```

---

## Adding a New Feature

1. Add a field to `MacroSnapshot` (in `filters/intelligence_sweep.py`)
2. Add the field to `FEATURE_NAMES` in `features/macro_features.py`
3. Update `_MEANS` and `_STDS` with a representative baseline value
4. Extend `MacroFeatureBuilder.build()` to extract and z-score the new field

---

## Training the Ensemble

```python
from models.lgbm_ensemble import LGBMEnsemble
model = LGBMEnsemble()
model.train(X=feature_matrix, y=label_array)   # 0=BUY, 1=HOLD, 2=SELL
```

Model is saved to `models/lgbm_model.pkl` automatically.

---

## Regime Gating

```python
from models.garch_regime import GarchRegimeDetector
garch = GarchRegimeDetector()
garch.update_price(new_price, prev_price)
if garch.is_high_vol:
    # reduce lot size or skip signal
```

Regime thresholds are controlled by `GARCH_HIGH_VOL_THRESHOLD` in `config/settings.py`.
