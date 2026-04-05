"""train_lgbm.py — Build and save the LGBMEnsemble from closed trade history.

Pulls closed trades from PostgreSQL, engineers features from stored
entry-snapshot columns, and trains the 3-class LightGBM classifier.

Labels
------
  0 = BUY  (direction=BUY  and pnl > 0)
  2 = SELL (direction=SELL and pnl > 0)
  1 = HOLD (trade lost money — signal should have been avoided)

Feature vector (11 numerical features, all column-native from the DB)
-----------------------------------------------------------------------
  rsi_aligned          0 / 1
  trend_aligned        0 / 1
  volume_sufficient    0 / 1
  near_news_event      0 / 1  (inverted — 1 means news present, bad)
  session_enc          0–3   (London=0, NY=1, Asian=2, overlap=3, other=-1)
  day_enc              0–6   (Mon=0 … Fri=4, weekend rarely traded)
  spread_at_entry      raw float (pips-ish)
  expected_edge_pct    raw float
  strategy_enc         hash-mod-8 bucket of strategy name
  direction_enc        BUY=1, SELL=-1
  mtf_alignment        0.0–1.0  (not stored yet → filled with 0.5)

Usage
-----
  python -m scripts.train_lgbm
  python -m scripts.train_lgbm --min-trades 50 --output models/lgbm_model.pkl

The script honours LGBM_ENSEMBLE_ENABLED=false in settings but forces-enables
training regardless so you can pre-train before toggling the flag.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── make project root importable ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_lgbm")

# ── feature engineering ───────────────────────────────────────────────────

_SESSION_MAP = {"london": 0, "ny": 1, "new york": 1, "newyork": 1,
                "asian": 2, "asia": 2, "overlap": 3}
_DAY_MAP = {"monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def _encode_session(s: str) -> float:
    return float(_SESSION_MAP.get((s or "").lower(), -1))


def _encode_day(d: str) -> float:
    return float(_DAY_MAP.get((d or "").lower(), -1))


def _encode_strategy(name: str) -> float:
    """Stable bucket in [0, 7] so new strategies get a slot without retraining."""
    if not name:
        return 0.0
    return float(abs(hash(name)) % 8)


def _encode_direction(d: str) -> float:
    return 1.0 if d.upper() == "BUY" else -1.0


def _make_label(direction: str, pnl: float) -> int:
    """BUY=0, SELL=2, HOLD=1 (wrong direction or breakeven)."""
    if pnl > 0:
        return 0 if direction.upper() == "BUY" else 2
    return 1


def _row_to_features(row: dict) -> list[float]:
    return [
        float(row.get("snap_rsi_aligned") or 0),
        float(row.get("snap_trend_aligned") or 0),
        float(row.get("snap_volume_sufficient") or 0),
        float(row.get("snap_near_news_event") or 0),
        _encode_session(row.get("snap_session") or ""),
        _encode_day(row.get("snap_day_of_week") or ""),
        float(row.get("spread_at_entry") or 0),
        float(row.get("expected_edge_pct") or 0),
        _encode_strategy(row.get("strategy") or ""),
        _encode_direction(row.get("direction") or ""),
        0.5,   # mtf_alignment placeholder (not yet stored per-trade)
    ]


FEATURE_NAMES = [
    "rsi_aligned", "trend_aligned", "volume_sufficient", "near_news_event",
    "session_enc", "day_enc", "spread_at_entry", "expected_edge_pct",
    "strategy_enc", "direction_enc", "mtf_alignment",
]

# ── data loading ──────────────────────────────────────────────────────────

def load_closed_trades(db_url: str | None = None) -> list[dict]:
    """Fetch closed, non-zero-pnl trades from PostgreSQL."""
    import psycopg2
    import psycopg2.extras

    from config import settings as cfg
    url = db_url or cfg.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL not set — cannot load training data.")

    conn = psycopg2.connect(url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    strategy, direction, pnl, spread_at_entry,
                    expected_edge_pct,
                    snap_rsi_aligned, snap_trend_aligned, snap_volume_sufficient,
                    snap_near_news_event, snap_session, snap_day_of_week
                FROM trades
                WHERE status = 'CLOSED'
                  AND pnl IS NOT NULL
                  AND pnl != 0
                ORDER BY close_time DESC
            """)
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    logger.info("Loaded %d closed trades from DB.", len(rows))
    return rows


# ── model training ────────────────────────────────────────────────────────

def train(rows: list[dict], output_path: Path) -> bool:
    """Build feature matrix, train, and save the LGBMEnsemble."""
    if not rows:
        logger.error("No training rows — nothing to train.")
        return False

    X = [_row_to_features(r) for r in rows]
    y = [_make_label(r.get("direction", ""), float(r.get("pnl", 0))) for r in rows]

    buy_count  = y.count(0)
    hold_count = y.count(1)
    sell_count = y.count(2)
    logger.info("Label distribution — BUY=%d, HOLD=%d, SELL=%d", buy_count, hold_count, sell_count)

    # Force-enable so LGBMEnsemble.train() doesn't no-op even if env var is missing
    import config.settings as cfg_mod
    cfg_mod.LGBM_ENSEMBLE_ENABLED = True

    import models.lgbm_ensemble as _lgbm_mod  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    # Redirect save path if user requested a custom location
    default_path = Path("models") / "lgbm_model.pkl"
    if output_path != default_path:
        _lgbm_mod._MODEL_PATH = output_path
        logger.info("Model will be saved to custom path: %s", output_path)
    else:
        logger.info("Model will be saved to %s", default_path)

    ensemble = _lgbm_mod.LGBMEnsemble()

    ok = ensemble.train(np.array(X), np.array(y))

    if ok:
        logger.info("Training complete.")
        # Sanity check: pass full feature row as macro_vec, empty micro_vec
        # _build_input concatenates both so this reproduces the 11-feature shape
        pred = ensemble.predict(X[0], [])
        logger.info("Sanity check -> direction=%s confidence=%.3f trained=%s",
                    pred.direction, pred.confidence, pred.model_trained)
    else:
        logger.error("LGBMEnsemble.train() returned False.")
    return ok


# ── entrypoint ────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the LGBMEnsemble from closed trades.")
    p.add_argument("--min-trades", type=int, default=30,
                   help="Minimum closed trades required to proceed (default: 30).")
    p.add_argument("--output", type=Path, default=Path("models/lgbm_model.pkl"),
                   help="Path to save the trained model file.")
    p.add_argument("--db-url", type=str, default=None,
                   help="Override DATABASE_URL for this run.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    _rc = 1
    try:
        try:
            rows = load_closed_trades(args.db_url)
        except Exception as exc:
            logger.error("Failed to load trades: %s", exc)
            sys.exit(1)

        if len(rows) < args.min_trades:
            logger.error(
                "Only %d closed trades found, need at least %d. "
                "Run more paper/live trades before training.",
                len(rows), args.min_trades,
            )
            sys.exit(1)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        ok = train(rows, args.output)
        _rc = 0 if ok else 1
    except SystemExit as exc:
        raise
    except Exception:
        logger.exception("Unhandled exception in training pipeline")
        _rc = 1
    finally:
        logging.shutdown()
    sys.exit(_rc)


if __name__ == "__main__":
    main()
