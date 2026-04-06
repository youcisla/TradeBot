"""train_lgbm_price.py — Train per-symbol price-based LGBM classifiers.

Labels are derived from **forward price movement** relative to ATR:
  BUY  (0) — max(high[t+1 … t+N]) − close[t] > atr_mult × ATR(14)
              AND bull_edge > bear_edge
  SELL (2) — close[t] − min(low[t+1 … t+N]) > atr_mult × ATR(14)
              AND bear_edge > bull_edge
  HOLD (1) — otherwise

Feature vector (12 features) is identical to ``models/lgbm_price_model.py``
so training and inference are guaranteed to use exactly the same representation.

Usage::

    # All ACTIVE_SYMBOLS, 2 years H1 (downloads from MT5 if needed)
    python -m scripts.train_lgbm_price

    # Specific symbols, 3 years
    python -m scripts.train_lgbm_price --symbols EURUSD GBPUSD USDJPY --years 3

    # Offline mode — only use existing data/history/*.csv files
    python -m scripts.train_lgbm_price --no-download

    # Custom labelling window
    python -m scripts.train_lgbm_price --forward-bars 3 --atr-mult 1.2

Output: ``models/lgbm_price_{SYMBOL}.pkl`` for each successfully trained symbol.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── project root on sys.path ─────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from config.symbols import ACTIVE_SYMBOLS  # noqa: E402

logger = logging.getLogger(__name__)

# ── Directories ──────────────────────────────────────────────────────────────
DATA_DIR  = _ROOT / "data" / "history"
MODEL_DIR = _ROOT / "models"

# ── Feature / label constants ────────────────────────────────────────────────
# Number of leading bars to discard so all rolling indicators are stable.
_N_WARMUP = 60

_BUY, _HOLD, _SELL = 0, 1, 2


def _compute_recency_weights(n: int, weight_factor: float) -> np.ndarray:
    """Exponential decay weights so recent bars are weighted more heavily.

    Formula (Freqtrade FreqAI pattern)::
        weights[i] = exp(-i / (weight_factor * n))

    where i=0 is the OLDEST sample and i=n-1 is the MOST RECENT.
    The array is reversed before returning so index 0 → oldest weight.
    weight_factor=0 disables weighting (all weights = 1.0).
    """
    if weight_factor <= 0:
        return np.ones(n, dtype=np.float32)
    indices = np.arange(n, dtype=np.float32)
    weights = np.exp(-indices / (weight_factor * n))
    # Most recent sample (last index) should have the highest weight;
    # reverse so index 0 = oldest but weight is still correct for .fit().
    # LGBM sees samples in array order; we want recent = higher weight.
    return weights.astype(np.float32)

# Session / Day encoding — MUST match models/lgbm_price_model.py exactly.
_SESSION_MAP: dict[str, int] = {
    "london":   0, "ny":       1, "new york": 1, "newyork": 1,
    "asian":    2, "asia":     2, "overlap":  3,
}


def _session_from_utc_hour(hour: int) -> float:
    """Approximate trading session from UTC hour (same heuristic as utils/helpers.py)."""
    if 7 <= hour < 16:
        return 3.0 if 12 <= hour < 16 else 0.0   # overlap / london
    if 12 <= hour < 21:
        return 1.0                                  # ny
    return 2.0                                      # asian


# ── Data layer ───────────────────────────────────────────────────────────────

def _find_existing_csv(symbol: str, timeframe: str = "H1") -> Path | None:
    """Return the most recently dated history CSV for symbol/timeframe, or None."""
    if not DATA_DIR.exists():
        return None
    matches = sorted(DATA_DIR.glob(f"{symbol}_{timeframe}_*.csv"), reverse=True)
    return matches[0] if matches else None


def _download_history(symbol: str, years: int, timeframe: str) -> Path | None:
    """Download from MT5 via backtesting.data_downloader.download_history()."""
    try:
        from backtesting.data_downloader import download_history
        end   = datetime.now(UTC)
        start = end - timedelta(days=365 * years)
        return download_history(symbol, timeframe, start, end)
    except Exception as exc:
        logger.error("MT5 download failed for %s: %s", symbol, exc)
        return None


def _load_csv(path: Path) -> pd.DataFrame | None:
    """Load a history CSV → sorted DataFrame, or None on failure."""
    try:
        df = pd.read_csv(path)
        # Parse the time column (handles both ISO strings and Unix timestamps)
        if "time" not in df.columns:
            logger.error("'time' column missing in %s", path)
            return None
        # Try ISO first; fall back to epoch seconds
        try:
            df["time"] = pd.to_datetime(df["time"], utc=True)
        except Exception:
            df["time"] = pd.to_datetime(df["time"].astype(float), unit="s", utc=True)

        for col in ("open", "high", "low", "close", "tick_volume"):
            if col not in df.columns:
                logger.error("Missing column '%s' in %s", col, path)
                return None
        if "spread" not in df.columns:
            df["spread"] = 0.0

        df = df.sort_values("time").reset_index(drop=True)
        logger.info("Loaded %d rows from %s", len(df), path.name)
        return df
    except Exception as exc:
        logger.error("Failed to load %s: %s", path, exc)
        return None


# ── Feature engineering (vectorised pandas) ──────────────────────────────────

def compute_features_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the 12-feature vector for every bar in *df*.

    Feature ORDER must match ``models/lgbm_price_model.FEATURE_NAMES`` exactly::

        rsi_norm, close_vs_ema20, close_vs_ema50, bb_pos,
        atr_ratio, vol_ratio, ema9_slope, garch_vol,
        kalman_velocity, session_enc, day_enc, spread_norm

    garch_vol and kalman_velocity are set to 0.0 here because they require
    live filter state that is not available from static historical OHLCV.
    The model learns to treat 0.0 as "unavailable" and relies on the other
    10 features.  At inference time the real values are injected from
    MarketContext.garch_vol / kalman_velocity.
    """
    c  = df["close"].astype(float)
    h  = df["high"].astype(float)
    lo = df["low"].astype(float)
    v  = df["tick_volume"].astype(float)
    sp = df["spread"].astype(float)

    # ── True Range → ATR ─────────────────────────────────────────────────────
    tr = pd.concat(
        [h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr14  = tr.rolling(14).mean()
    atr30  = tr.rolling(30).mean()
    atr_safe = atr14.clip(lower=1e-10)
    # Ratio: current 14-bar ATR vs 30-bar ATR — captures vol expansion/contraction
    atr_ratio = (atr14 / atr30.where(atr30 > 1e-10, atr14)).clip(0.2, 5.0)

    # ── RSI (14) ─────────────────────────────────────────────────────────────
    delta  = c.diff()
    gain   = delta.clip(lower=0).rolling(14).mean()
    loss   = (-delta).clip(lower=0).rolling(14).mean()
    rsi    = (100.0 - 100.0 / (1.0 + gain / loss.clip(lower=1e-10)))
    rsi_norm = rsi / 100.0

    # ── EMA series ───────────────────────────────────────────────────────────
    ema9  = c.ewm(span=9,  adjust=False).mean()
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()

    close_vs_ema20 = ((c - ema20) / atr_safe).clip(-3.0, 3.0)
    close_vs_ema50 = ((c - ema50) / atr_safe).clip(-3.0, 3.0)

    # ── Bollinger Bands (20-period, 2σ, population std) ──────────────────────
    # ddof=0 → population std, matches the inference-path formula in lgbm_price_model.py
    bb_mean  = c.rolling(20).mean()
    bb_std   = c.rolling(20).std(ddof=0)
    bb_upper = bb_mean + 2.0 * bb_std
    bb_lower = bb_mean - 2.0 * bb_std
    bb_range = (bb_upper - bb_lower).clip(lower=1e-10)
    bb_pos   = ((c - bb_lower) / bb_range).clip(0.0, 1.0)

    # ── Volume ratio ─────────────────────────────────────────────────────────
    vol_mean20 = v.rolling(20).mean().clip(lower=1e-10)
    vol_ratio  = (v / vol_mean20).clip(0.0, 5.0)

    # ── EMA9 slope (normalised by ATR) ───────────────────────────────────────
    ema9_slope = ((ema9 - ema9.shift()) / atr_safe).clip(-2.0, 2.0)

    # ── Session / Day from bar timestamp ─────────────────────────────────────
    ts = df["time"]
    if not hasattr(ts.dtype, "tz") or ts.dtype.tz is None:
        ts = pd.to_datetime(ts, utc=True)
    session_enc = ts.dt.hour.apply(_session_from_utc_hour)
    day_enc     = ts.dt.weekday.astype(float)   # 0=Mon … 6=Sun

    # ── Spread (normalised) ──────────────────────────────────────────────────
    spread_norm = (sp / atr_safe).clip(0.0, 1.0)

    return pd.DataFrame(
        {
            "rsi_norm":         rsi_norm,
            "close_vs_ema20":   close_vs_ema20,
            "close_vs_ema50":   close_vs_ema50,
            "bb_pos":           bb_pos,
            "atr_ratio":        atr_ratio,
            "vol_ratio":        vol_ratio,
            "ema9_slope":       ema9_slope,
            "garch_vol":        0.0,         # not available from static OHLCV
            "kalman_velocity":  0.0,         # not available from static OHLCV
            "session_enc":      session_enc,
            "day_enc":          day_enc,
            "spread_norm":      spread_norm,
        },
        index=df.index,
    )


# ── Label computation ─────────────────────────────────────────────────────────

def compute_labels(df: pd.DataFrame, n_forward: int, atr_mult: float) -> np.ndarray:
    """Compute forward-return labels for every bar.

    Returns an int8 array of length ``len(df)``:
      0  → BUY   (long edge in the next *n_forward* bars)
      1  → HOLD  (no clear directional edge)
      2  → SELL  (short edge in the next *n_forward* bars)
     -1  → exclude (last *n_forward* bars or ATR unavailable)
    """
    highs  = df["high"].values.astype(np.float64)
    lows   = df["low"].values.astype(np.float64)
    closes = df["close"].values.astype(np.float64)
    n      = len(df)

    # ATR(14) via simple rolling mean of true range
    hi, lo_a, cl = df["high"].values, df["low"].values, df["close"].values
    tr_vals = np.maximum(
        hi - lo_a,
        np.maximum(
            np.abs(hi - np.roll(cl, 1)),
            np.abs(lo_a - np.roll(cl, 1)),
        ),
    )
    tr_vals[0] = hi[0] - lo_a[0]
    atr_series = pd.Series(tr_vals).rolling(14).mean().values

    labels = np.full(n, _HOLD, dtype=np.int8)

    for i in range(n - n_forward):
        atr_i = atr_series[i]
        if not atr_i or np.isnan(atr_i) or atr_i < 1e-10:
            continue
        future_highs = highs[i + 1 : i + 1 + n_forward]
        future_lows  = lows[i + 1  : i + 1 + n_forward]
        bull_edge = (np.max(future_highs) - closes[i]) / atr_i
        bear_edge = (closes[i] - np.min(future_lows)) / atr_i

        if bull_edge >= atr_mult and bull_edge > bear_edge:
            labels[i] = _BUY
        elif bear_edge >= atr_mult and bear_edge > bull_edge:
            labels[i] = _SELL
        # else remains HOLD

    # The last n_forward bars can't be labelled — mark for exclusion
    labels[n - n_forward:] = -1
    return labels


# ── Per-symbol training ───────────────────────────────────────────────────────

def train_symbol(
    symbol: str,
    df: pd.DataFrame,
    n_forward: int,
    atr_mult: float,
    weight_factor: float = 0.0,
) -> "object | None":
    """Train one LGBMClassifier for *symbol* and return it (or None on failure)."""
    try:
        from lightgbm import LGBMClassifier
    except ImportError:
        logger.error("lightgbm not installed — run: pip install lightgbm")
        return None

    min_rows = _N_WARMUP + n_forward + 50
    if len(df) < min_rows:
        logger.warning(
            "%s — insufficient rows (%d, need ≥%d) — skipping",
            symbol, len(df), min_rows,
        )
        return None

    logger.info("Computing features for %s (%d bars)…", symbol, len(df))
    feats  = compute_features_vectorized(df)
    labels = compute_labels(df, n_forward, atr_mult)

    # Valid rows: past warmup, all features finite, label assigned
    valid = (
        (~feats.isna().any(axis=1))
        & (feats.index >= _N_WARMUP)
        & (labels >= 0)
    )
    X = feats[valid].values.astype(np.float32)
    y = labels[valid]

    if len(X) < 100:
        logger.warning(
            "%s — only %d valid samples after filtering (need ≥100) — skipping",
            symbol, len(X),
        )
        return None

    # Report class balance
    total = len(y)
    for cls_idx, cls_name in zip((_BUY, _HOLD, _SELL), ("BUY", "HOLD", "SELL")):
        cnt = int((y == cls_idx).sum())
        logger.info("  %-6s %5d  (%.1f%%)", cls_name, cnt, 100.0 * cnt / total)

    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=31,
        min_child_samples=20,
        class_weight="balanced",
        random_state=42,
        verbose=-1,
    )
    # Recency-weighted training (Freqtrade/FreqAI pattern)
    weights = _compute_recency_weights(len(X), weight_factor)
    if weight_factor > 0:
        logger.info(
            "  Recency weighting active (factor=%.2f) — "
            "weight range: %.4f … %.4f",
            weight_factor, weights.min(), weights.max(),
        )
    model.fit(X, y, sample_weight=weights)
    logger.info(
        "%s — ✓ trained on %d samples (%d features)",
        symbol, len(X), X.shape[1],
    )
    return model


# ── CLI entry-point ───────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train per-symbol price-based LGBM classifiers from OHLCV history.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--symbols", nargs="+", metavar="SYM",
        default=None,
        help="Symbols to train on (default: ACTIVE_SYMBOLS from config).",
    )
    parser.add_argument(
        "--timeframe", default="H1",
        help="Candle timeframe (default: H1).",
    )
    parser.add_argument(
        "--years", type=float, default=2.0,
        help="Years of history to download when no local CSV exists (default: 2).",
    )
    parser.add_argument(
        "--forward-bars", type=int, default=5, dest="forward_bars",
        help="Look-ahead bars for labelling (default: 5).",
    )
    parser.add_argument(
        "--atr-mult", type=float, default=1.0, dest="atr_mult",
        help="ATR multiplier for BUY/SELL threshold (default: 1.0).",
    )
    parser.add_argument(
        "--no-download", action="store_true", dest="no_download",
        help="Do not connect to MT5; only use existing local CSVs.",
    )
    parser.add_argument(
        "--min-samples", type=int, default=100, dest="min_samples",
        help="Minimum valid training samples per symbol (default: 100).",
    )
    parser.add_argument(
        "--weight-factor", type=float, default=0.0, dest="weight_factor",
        help=(
            "Recency weight factor (0=disabled, 0.1=recommended). "
            "Weights recent bars exponentially more in training via "
            "exp(-i / (factor * n)). Higher = more recency emphasis. "
            "Freqtrade-style exponential decay."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Train price-LGBM for all requested symbols.

    Returns 0 on success (at least one model saved), 1 otherwise.
    """
    args = _parse_args(argv)

    symbols = args.symbols or ACTIVE_SYMBOLS
    logger.info(
        "Price-LGBM training — %d symbol(s)  TF=%s  years=%.1f  "
        "forward=%d  atr_mult=%.2f",
        len(symbols), args.timeframe, args.years,
        args.forward_bars, args.atr_mult,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    failed: list[str] = []

    logger.info(
        "Price-LGBM training — %d symbol(s)  TF=%s  years=%.1f  "
        "forward=%d  atr_mult=%.2f  weight_factor=%s",
        len(symbols), args.timeframe, args.years,
        args.forward_bars, args.atr_mult,
        f"{args.weight_factor:.2f}" if args.weight_factor > 0 else "disabled",
    )

    for sym in symbols:
        logger.info("=" * 60)
        logger.info("Symbol: %s", sym)

        # ── Locate or download history ────────────────────────────────────
        csv_path = _find_existing_csv(sym, args.timeframe)
        if csv_path:
            logger.info("Using existing CSV: %s", csv_path)
        elif not args.no_download:
            logger.info("No local CSV — downloading from MT5…")
            csv_path = _download_history(sym, args.years, args.timeframe)
        else:
            logger.warning("%s — no CSV found and --no-download set, skipping.", sym)
            failed.append(sym)
            continue

        if not csv_path or not csv_path.exists():
            logger.error("%s — could not obtain history data, skipping.", sym)
            failed.append(sym)
            continue

        # ── Load ──────────────────────────────────────────────────────────
        df = _load_csv(csv_path)
        if df is None:
            failed.append(sym)
            continue

        # ── Train ─────────────────────────────────────────────────────────
        model = train_symbol(sym, df, args.forward_bars, args.atr_mult, args.weight_factor)
        if model is None:
            failed.append(sym)
            continue

        # ── Save ──────────────────────────────────────────────────────────
        safe_key = sym.replace("/", "_").replace("\\", "_").replace(".", "_").upper()
        out_path = MODEL_DIR / f"lgbm_price_{safe_key}.pkl"
        try:
            import pickle
            with open(out_path, "wb") as fh:
                pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Saved → %s", out_path)
            saved += 1
        except Exception as exc:
            logger.error("Failed to save model for %s: %s", sym, exc)
            failed.append(sym)

    logger.info("=" * 60)
    logger.info("Done — %d saved, %d failed: %s", saved, len(failed), failed or "none")

    if failed:
        logger.warning(
            "Failed symbols: %s\n"
            "Tip: ensure MT5 is running, the symbol is in your market watch,\n"
            "     and data/history/ is writable.",
            failed,
        )

    return 0 if saved > 0 else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    _rc = main()
    logging.shutdown()
    sys.exit(_rc)
