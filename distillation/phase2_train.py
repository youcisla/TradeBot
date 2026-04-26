"""
Phase 2 – Local Student Model Training
======================================
Trains a sub-millisecond XGBoost classifier on the DeepSeek-R1
enriched dataset produced by phase1_enrich.py.

Teacher gives us:
  • setup_label  — multi-class target
  • confidence   — used as sample weight
  • regime_hint  — TRENDING | RANGE | CRISIS

Pipeline
  1. Load enriched JSONL
  2. Feature engineering (rolling ICT + microstructure)
  3. Train XGBoost with k-fold CV
  4. Persist model + latency benchmark
"""

from __future__ import annotations

import json
import logging
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, f1_score, log_loss, roc_auc_score,
    classification_report, confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore", category=FutureWarning)

PROJECT_ROOT   = Path(__file__).parent.parent.parent
MODEL_OUTPUT   = PROJECT_ROOT / "models"
REPORT_DIR     = PROJECT_ROOT / "distillation" / "reports"
DISTILLATION_DIR = PROJECT_ROOT / "distillation" / "output"

for _d in (MODEL_OUTPUT, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Feature engineering ────────────────────────────────────────────────────────

class ICTFeatureEngine:
    """
    Converts raw candles into an 18-feature vector suitable for the
    XGBoost student model.

    Feature groups:
      price          – log returns, body/wick ratios
      volume         – % changes, moving-average ratio
      microstructure – spread, volume imbalance, Kyle's lambda
      ict            – FVG size proxy, trend strength
    """

    LOOKBACK = 20
    NAMES = [
        "return_1", "return_5", "return_15",
        "body_size", "high_low_ratio",
        "upper_wick", "lower_wick", "wick_ratio",
        "vol_change_1", "vol_change_5", "vol_MA5_ratio",
        "spread", "volume_imbalance", "price_impact_lambda",
        "fvg_size", "fvg_age", "ob_strength", "trend_strength",
    ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ── price features ────────────────────────────────────────────────
        df["return_1"]   = np.log(df["close"] / df["close"].shift(1).clip(lower=1e-9))
        df["return_5"]   = np.log(df["close"] / df["close"].shift(5).clip(lower=1e-9))
        df["return_15"]  = np.log(df["close"] / df["close"].shift(15).clip(lower=1e-9))
        df["body_size"]  = abs(df["close"] - df["open"])
        df["high_low_ratio"] = df["high"] - df["low"]
        df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
        df["wick_ratio"] = df["upper_wick"] / (df["lower_wick"] + 1e-9)

        # ── volume features ──────────────────────────────────────────────
        df["vol_change_1"]  = df["volume"].pct_change(1)
        df["vol_change_5"]  = df["volume"].pct_change(5)
        df["vol_MA5"]       = df["volume"].rolling(5).mean()
        df["vol_MA5_ratio"] = df["volume"] / (df["vol_MA5"] + 1e-9)

        # ── microstructure ────────────────────────────────────────────────
        df["spread"] = (df["high"] - df["low"]).clip(lower=1e-9)
        df["bid_vol"]  = df["volume"] * np.where(df["return_1"] >= 0, 1.0, 0.5)
        df["ask_vol"]  = df["volume"] * np.where(df["return_1"] < 0,  1.0, 0.5)
        df["volume_imbalance"] = (
            (df["bid_vol"].rolling(5).sum() - df["ask_vol"].rolling(5).sum())
            / (df["bid_vol"].rolling(5).sum() + df["ask_vol"].rolling(5).sum() + 1e-9)
        )
        df["price_impact_lambda"] = df["return_1"].abs() / (df["volume"] + 1e-9)

        # ── ICT proxies ──────────────────────────────────────────────────
        df["fvg_size"]       = df["high"].shift(1) - df["low"]   # upward FVG proxy
        df["fvg_age"]        = 0  # placeholder; wired to ICT engine in production
        df["ob_strength"]    = 0  # placeholder
        df["trend_strength"] = (
            df["close"] - df["low"].rolling(self.LOOKBACK).min()
        ) / (
            df["high"].rolling(self.LOOKBACK).max() -
            df["low"].rolling(self.LOOKBACK).min() + 1e-9
        )

        drop_cols = [
            "timestamp", "symbol", "open", "high", "low", "close", "volume",
            "bid_vol", "ask_vol", "vol_MA5",
        ]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
        df = df.fillna(0).replace([np.inf, -np.inf], 0)
        return df[self.NAMES]


# ── Trainer ────────────────────────────────────────────────────────────────────

CLASSES = [
    "FVG_BUY", "FVG_SELL",
    "OB_BUY",  "OB_SELL",
    "LTB_BUY", "LTB_SELL",
    "HLTB_BUY","HLTB_SELL",
    "BOS_BUY", "BOS_SELL",
    "NONE",
]


class StudentTrainer:
    def __init__(self, symbol: str = "BTCUSD"):
        self.symbol      = symbol
        self.featurizer  = ICTFeatureEngine()
        self.le          = LabelEncoder().fit(CLASSES)
        self._model: xgb.Booster | None = None

    def load(self, jsonl_path: str | Path) -> pd.DataFrame:
        records = []
        with open(jsonl_path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df

    def train(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
    ) -> dict:
        # ── filter valid labelled rows ────────────────────────────────────
        df = df[df["setup_label"].notna() & (df["setup_label"] != "null")].copy()
        logging.info("Training on %d labelled candles (symbol=%s)", len(df), self.symbol)

        if len(df) < 50:
            raise ValueError(f"Need ≥50 labelled candles, got {len(df)}")

        y      = self.le.transform(df["setup_label"])
        weight = df["confidence"].fillna(0.5).astype(float).values

        X      = self.featurizer.transform(df)
        logging.info("Feature matrix: %s", X.shape)

        # ── k-fold CV ─────────────────────────────────────────────────────
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        metrics = {k: [] for k in ["accuracy", "f1_macro", "roc_auc", "log_loss", "train_ms"]}

        for fold, (tr_idx, va_idx) in enumerate(cv.split(X, y)):
            t0   = time.perf_counter()
            dtrain = xgb.DMatrix(X.iloc[tr_idx], label=y[tr_idx], weight=weight[tr_idx])
            dval   = xgb.DMatrix(X.iloc[va_idx], label=y[va_idx])

            params = {
                "objective":       "multi:softprob",
                "num_class":      len(CLASSES),
                "max_depth":       6,
                "learning_rate":   0.05,
                "subsample":       0.8,
                "colsample_bytree": 0.8,
                "min_child_weight": 3,
                "eval_metric":     "mlogloss",
                "tree_method":      "hist",
                "device":          "cuda",   # GPU if available; falls back to cpu
                "seed":            42,
            }

            model = xgb.train(
                params, dtrain,
                num_boost_round=500,
                evals=[(dval, "val")],
                early_stopping_rounds=30,
                verbose_eval=False,
            )
            train_ms = (time.perf_counter() - t0) * 1e3

            yprob = model.predict(dval)
            ypred = yprob.argmax(axis=1)

            acc = accuracy_score(y[va_idx], ypred)
            f1  = f1_score(y[va_idx], ypred, average="macro", zero_division=0)
            try:
                auc = roc_auc_score(y[va_idx], yprob, multi_class="ovr")
            except ValueError:
                auc = 0.0
            ll  = log_loss(y[va_idx], yprob)

            for k, v in zip(["accuracy","f1_macro","roc_auc","log_loss","train_ms"],
                            [acc, f1, auc, ll, train_ms]):
                metrics[k].append(v)

            logging.info(
                "Fold %d — acc=%.3f f1=%.3f auc=%.3f ll=%.4f t_ms=%.0f",
                fold, acc, f1, auc, ll, train_ms
            )

        # ── final model on ALL data ────────────────────────────────────────
        dfull = xgb.DMatrix(X, label=y, weight=weight)
        self._model = xgb.train(
            {**params, "max_depth": 7},
            dfull,
            num_boost_round=500,
            verbose_eval=False,
        )

        # ── feature importance ──────────────────────────────────────────
        imp   = self._model.get_score(importance_type="gain")
        fi_df = (
            pd.DataFrame([{"feature": k, "importance": v} for k, v in imp.items()])
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        fi_path = REPORT_DIR / f"{self.symbol}_feature_importance.csv"
        fi_df.to_csv(fi_path, index=False)

        # ── inference latency benchmark ────────────────────────────────
        inf_bench = self._benchmark(X.sample(500, random_state=7))

        # ── assemble results ───────────────────────────────────────────
        results = {
            "symbol":               self.symbol,
            "n_candles":            int(len(df)),
            "accuracy_p50":        float(np.median(metrics["accuracy"])),
            "f1_macro_p50":        float(np.median(metrics["f1_macro"])),
            "roc_auc_p50":         float(np.median(metrics["roc_auc"])),
            "log_loss_p50":        float(np.median(metrics["log_loss"])),
            "train_ms_p50":        float(np.median(metrics["train_ms"])),
            "inference_p50_ms":    inf_bench["p50"],
            "inference_p99_ms":    inf_bench["p99"],
            "feature_importance_csv": str(fi_path),
            "model_path":          str(MODEL_OUTPUT / f"student_{self.symbol}.json"),
            "label_classes":      list(self.le.classes_),
            "fold_metrics":       {k: [float(v) for v in vals] for k, vals in metrics.items()},
            "timestamp":           datetime.now(timezone.utc).isoformat(),
        }

        self._model.save_model(results["model_path"])
        with open(REPORT_DIR / f"{self.symbol}_training_report.json", "w") as fh:
            json.dump(results, fh, indent=2)

        return results

    def predict(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Returns (predicted_class_indices, probability_matrix). Sub-ms on GPU."""
        dtest = xgb.DMatrix(X)
        probs = self._model.predict(dtest)
        return probs.argmax(axis=1), probs

    # ── internals ────────────────────────────────────────────────────────────

    def _benchmark(self, X: pd.DataFrame) -> dict:
        dtest = xgb.DMatrix(X)
        for _ in range(3):
            self._model.predict(dtest)
        latencies = []
        for _ in range(100):
            t0 = time.perf_counter()
            self._model.predict(dtest)
            latencies.append((time.perf_counter() - t0) * 1e3)
        latencies.sort()
        n = len(latencies)
        return {"p50": float(latencies[n // 2]), "p99": float(latencies[min(int(n * 0.99), n - 1)])}


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    ap = argparse.ArgumentParser(description="Phase-2: Student Model Training")
    ap.add_argument("--enriched-jsonl", required=True)
    ap.add_argument("--symbol",         default="BTCUSD")
    ap.add_argument("--n-splits",       type=int, default=5)
    args = ap.parse_args()

    trainer = StudentTrainer(symbol=args.symbol)
    df      = trainer.load(args.enriched_jsonl)
    results = trainer.train(df, n_splits=args.n_splits)

    print(f"\n{'='*60}")
    print(f"Student model trained for {args.symbol}")
    print(f"  Accuracy (CV p50):   {results['accuracy_p50']:.4f}")
    print(f"  F1 macro  (CV p50):   {results['f1_macro_p50']:.4f}")
    print(f"  ROC AUC   (CV p50):   {results['roc_auc_p50']:.4f}")
    print(f"  Inference p50:         {results['inference_p50_ms']:.3f} ms")
    print(f"  Inference p99:         {results['inference_p99_ms']:.3f} ms")
    print(f"  Model → {results['model_path']}")


if __name__ == "__main__":
    main()