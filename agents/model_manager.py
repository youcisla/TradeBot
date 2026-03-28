"""ModelManager — trains, loads, saves and fine-tunes per-symbol LSTM models.

Lifecycle
---------
1. ``initialize(symbols)`` is called once at bot startup.
   - If a recent .pt file exists for a symbol → load it immediately.
   - Otherwise → queue a background training job (thread pool, max 4 workers).
2. ``predict(symbol, candles, context)`` is called every loop by NeuralStrategy.
   - Returns (direction, confidence) if the model is ready, else None.
3. ``record_outcome(symbol, candles, label)`` is called when a trade closes.
   - Adds the (feature_seq, label) pair to a per-symbol replay buffer (200 max).
   - Every NEURAL_RETRAIN_EVERY samples, triggers 5 fine-tuning epochs in
     a background thread (lr=0.0001 to avoid catastrophic forgetting).
"""

from __future__ import annotations

import collections
import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
import torch.nn as nn

from config import settings
from models.neural_model import (
    BUY, HOLD,
    LSTMTradingModel,
    FeatureNormalizer,
    build_features,
    auto_label,
)

logger = logging.getLogger(__name__)

_MAX_WORKERS  = 4   # parallel training threads
_FINE_TUNE_LR = 0.0001
_FINE_TUNE_EP = 5
_REPLAY_SIZE  = 200


class _SymbolState:
    """Per-symbol mutable state (model, normalizer, replay buffer, counters)."""

    def __init__(self) -> None:
        self.model:      LSTMTradingModel | None = None
        self.normalizer: FeatureNormalizer | None = None
        self.ready:      bool = False
        self.training:   bool = False
        self.lock        = threading.Lock()

        # Ring buffer: list of (feat_seq: np.ndarray, label: int)
        self.replay: collections.deque = collections.deque(maxlen=_REPLAY_SIZE)
        self.replay_since_ft: int = 0   # samples added since last fine-tune
        self.fine_tuning: bool = False


class ModelManager:
    """Manages per-symbol LSTM models through their full lifecycle."""

    def __init__(self, broker=None) -> None:
        self._broker  = broker
        self._states:  dict[str, _SymbolState] = {}
        self._executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS,
                                            thread_name_prefix="nn-train")
        self._models_dir = Path(settings.NEURAL_MODELS_DIR)
        self._models_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────

    def initialize(self, symbols: Sequence[str]) -> None:
        """Called at bot startup.  Returns immediately; training is async."""
        for sym in symbols:
            self._states[sym] = _SymbolState()
            pt_path  = self._pt_path(sym)
            jsn_path = self._json_path(sym)

            # Load if model exists and is < 7 days old
            if pt_path.exists() and jsn_path.exists():
                age = time.time() - pt_path.stat().st_mtime
                if age < 7 * 86400:
                    try:
                        self._load_model(sym)
                        logger.info("[neural] %s: loaded existing model (age %.1fh)",
                                    sym, age / 3600)
                        continue
                    except Exception as exc:
                        logger.warning("[neural] %s: failed to load model (%s) — retraining",
                                       sym, exc)

            # Queue background training
            logger.info("[neural] %s: queuing background training", sym)
            self._states[sym].training = True
            self._executor.submit(self._train_symbol_safe, sym)

    def predict(
        self,
        symbol: str,
        candles,
        context=None,
    ) -> tuple[str, float] | None:
        """Return (direction, confidence) or None if model not ready / says HOLD."""
        state = self._states.get(symbol)
        if state is None or not state.ready:
            return None

        spread     = getattr(context, "spread",     0.0)  if context else 0.0
        sma_fast   = getattr(context, "sma_fast",   None) if context else None
        sma_slow   = getattr(context, "sma_slow",   None) if context else None
        timestamp  = getattr(context, "timestamp",  None) if context else None
        h4_candles = getattr(context, "h4_candles", None) if context else None
        d1_candles = getattr(context, "d1_candles", None) if context else None

        feat = build_features(
            candles,
            seq_len=settings.NEURAL_SEQ_LEN,
            spread=spread,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            timestamp=timestamp,
            h4_candles=h4_candles,
            d1_candles=d1_candles,
        )
        if feat is None:
            return None

        with state.lock:
            norm = state.normalizer
            model = state.model

        if norm is None or model is None:
            return None

        feat_norm = norm.transform(feat)   # (seq_len, N_FEATURES)
        proba = model.predict_proba(feat_norm)   # [p_buy, p_sell, p_hold]

        best_class = int(np.argmax(proba))
        confidence = float(proba[best_class])

        if confidence < settings.NEURAL_MIN_CONFIDENCE:
            return None
        if best_class == HOLD:
            return None

        direction = "BUY" if best_class == BUY else "SELL"
        logger.debug("[neural] %s: %s %.1f%%", symbol, direction, confidence * 100)
        return direction, confidence

    def record_outcome(
        self,
        symbol: str,
        candles,
        label: int,           # BUY=0, SELL=1, HOLD=2
        context=None,
    ) -> None:
        """Add a real trade outcome to the replay buffer; trigger fine-tuning."""
        state = self._states.get(symbol)
        if state is None or not state.ready:
            return

        # If no candles provided, fetch current ones from broker (fine-tune is async)
        if not candles and self._broker is not None:
            try:
                needed = settings.NEURAL_SEQ_LEN + 30
                candles = self._broker.get_candles(symbol, "H1", needed) or []
            except Exception:
                pass

        if not candles:
            return

        spread     = getattr(context, "spread",     0.0)  if context else 0.0
        sma_fast   = getattr(context, "sma_fast",   None) if context else None
        sma_slow   = getattr(context, "sma_slow",   None) if context else None
        timestamp  = getattr(context, "timestamp",  None) if context else None
        h4_candles = getattr(context, "h4_candles", None) if context else None
        d1_candles = getattr(context, "d1_candles", None) if context else None

        feat = build_features(
            candles,
            seq_len=settings.NEURAL_SEQ_LEN,
            spread=spread,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            timestamp=timestamp,
            h4_candles=h4_candles,
            d1_candles=d1_candles,
        )
        if feat is None:
            return

        with state.lock:
            norm = state.normalizer
        if norm:
            feat = norm.transform(feat)

        state.replay.append((feat, label))
        state.replay_since_ft += 1

        if (state.replay_since_ft >= settings.NEURAL_RETRAIN_EVERY
                and not state.fine_tuning):
            state.fine_tuning = True
            state.replay_since_ft = 0
            self._executor.submit(self._fine_tune_safe, symbol)

    def is_ready(self, symbol: str) -> bool:
        state = self._states.get(symbol)
        return state is not None and state.ready

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    # ── Internal — training ──────────────────────────────────────────────

    def _train_symbol_safe(self, symbol: str) -> None:
        try:
            self._train_symbol(symbol)
        except Exception:
            logger.exception("[neural] %s: training failed", symbol)
            state = self._states.get(symbol)
            if state:
                state.training = False

    def _train_symbol(self, symbol: str) -> None:
        logger.info("[neural] %s: starting training (downloading %d yr H1 history)",
                    symbol, settings.NEURAL_TRAIN_YEARS)
        state = self._states[symbol]

        # ── Download historical candles ───────────────────────────────────
        candles = self._download_candles(symbol)
        if candles is None or len(candles) < settings.NEURAL_SEQ_LEN + 50:
            logger.warning("[neural] %s: not enough history — skipping", symbol)
            state.training = False
            return

        logger.info("[neural] %s: %d candles downloaded", symbol, len(candles))

        # ── Build feature matrix ──────────────────────────────────────────
        seq_len  = settings.NEURAL_SEQ_LEN
        features = []
        labels   = auto_label(candles)

        for i in range(len(candles) - seq_len):
            window = candles[i : i + seq_len + 14 + 1]  # extra for warm-up
            feat = build_features(window, seq_len=seq_len)
            if feat is not None:
                features.append(feat)

        if not features:
            logger.warning("[neural] %s: no feature windows built — skipping", symbol)
            state.training = False
            return

        X = np.stack(features)                     # (N, seq_len, 9)
        y = labels[14 : 14 + len(features)]        # align with warm-up offset
        y = y.astype(np.int64)

        # ── Train / val split (temporal — NO shuffle) ────────────────────
        split = int(len(X) * 0.8)
        X_tr, X_val = X[:split], X[split:]
        y_tr, y_val = y[:split], y[split:]

        # ── Normalise ────────────────────────────────────────────────────
        norm = FeatureNormalizer()
        X_tr_n  = norm.fit_transform(X_tr)
        X_val_n = norm.transform(X_val)

        # ── Class weights for imbalance ───────────────────────────────────
        class_counts = np.bincount(y_tr, minlength=3).astype(np.float32)
        class_counts = np.where(class_counts == 0, 1, class_counts)
        weights      = torch.tensor(1.0 / class_counts)

        # ── Model ─────────────────────────────────────────────────────────
        model = LSTMTradingModel(
            hidden_size=settings.NEURAL_HIDDEN_SIZE,
            num_layers=settings.NEURAL_NUM_LAYERS,
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss(weight=weights)

        X_tr_t  = torch.tensor(X_tr_n,  dtype=torch.float32)
        y_tr_t  = torch.tensor(y_tr,    dtype=torch.long)
        X_val_t = torch.tensor(X_val_n, dtype=torch.float32)
        y_val_t = torch.tensor(y_val,   dtype=torch.long)

        best_val_loss = float("inf")
        patience = 0
        best_state = None

        batch_size = 32
        n_batches  = math.ceil(len(X_tr_t) / batch_size)

        for epoch in range(settings.NEURAL_TRAIN_EPOCHS):
            model.train()
            total_loss = 0.0
            perm = torch.randperm(len(X_tr_t))

            for b in range(n_batches):
                idx    = perm[b * batch_size : (b + 1) * batch_size]
                xb, yb = X_tr_t[idx], y_tr_t[idx]
                optimizer.zero_grad()
                loss = criterion(model(xb), yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

            # Validation
            model.eval()
            with torch.no_grad():
                val_loss = criterion(model(X_val_t), y_val_t).item()
                val_preds = model(X_val_t).argmax(dim=1)
                val_acc   = (val_preds == y_val_t).float().mean().item()

            logger.info("[neural] %s epoch %d/%d — train_loss=%.4f val_loss=%.4f val_acc=%.2f%%",
                        symbol, epoch + 1, settings.NEURAL_TRAIN_EPOCHS,
                        total_loss / n_batches, val_loss, val_acc * 100)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state    = {k: v.clone() for k, v in model.state_dict().items()}
                patience = 0
            else:
                patience += 1
                if patience >= 3:
                    logger.info("[neural] %s: early stop at epoch %d", symbol, epoch + 1)
                    break

        if best_state:
            model.load_state_dict(best_state)
        model.eval()

        # ── Save ─────────────────────────────────────────────────────────
        model.save(self._pt_path(symbol))
        norm.save(self._json_path(symbol))

        # ── Activate ─────────────────────────────────────────────────────
        with state.lock:
            state.model      = model
            state.normalizer = norm
            state.ready      = True
            state.training   = False

        logger.info("[neural] %s: model READY (val_loss=%.4f val_acc=%.1f%%)",
                    symbol, best_val_loss, val_acc * 100)

    # ── Internal — fine-tuning ───────────────────────────────────────────

    def _fine_tune_safe(self, symbol: str) -> None:
        try:
            self._fine_tune(symbol)
        except Exception:
            logger.exception("[neural] %s: fine-tuning failed", symbol)
        finally:
            state = self._states.get(symbol)
            if state:
                state.fine_tuning = False

    def _fine_tune(self, symbol: str) -> None:
        state = self._states.get(symbol)
        if state is None or not state.ready or len(state.replay) < 5:
            return

        with state.lock:
            samples = list(state.replay)

        X = np.stack([s[0] for s in samples])
        y = np.array([s[1] for s in samples], dtype=np.int64)

        X_t = torch.tensor(X, dtype=torch.float32)
        y_t = torch.tensor(y, dtype=torch.long)

        with state.lock:
            model = state.model

        if model is None:
            return

        optimizer = torch.optim.Adam(model.parameters(), lr=_FINE_TUNE_LR)
        criterion = nn.CrossEntropyLoss()

        model.train()
        for ep in range(_FINE_TUNE_EP):
            optimizer.zero_grad()
            loss = criterion(model(X_t), y_t)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        model.eval()
        model.save(self._pt_path(symbol))
        logger.info("[neural] %s: fine-tuned on %d samples", symbol, len(samples))

    # ── Internal — loading ───────────────────────────────────────────────

    def _load_model(self, symbol: str) -> None:
        state = self._states[symbol]
        model = LSTMTradingModel(
            hidden_size=settings.NEURAL_HIDDEN_SIZE,
            num_layers=settings.NEURAL_NUM_LAYERS,
        )
        model.load_state_dict(
            torch.load(self._pt_path(symbol), map_location="cpu", weights_only=True)
        )
        model.eval()

        norm = FeatureNormalizer()
        norm.load(self._json_path(symbol))

        with state.lock:
            state.model      = model
            state.normalizer = norm
            state.ready      = True
            state.training   = False

    # ── Internal — data download ─────────────────────────────────────────

    def _download_candles(self, symbol: str):
        """Fetch NEURAL_TRAIN_YEARS years of H1 candles via the live broker."""
        if self._broker is None:
            logger.warning("[neural] %s: no broker available for data download", symbol)
            return None

        end   = datetime.now(UTC)
        start = end - timedelta(days=365 * settings.NEURAL_TRAIN_YEARS)

        # Try the existing data_downloader first (saves to CSV for reuse)
        try:
            from backtesting.data_downloader import download_history
            path = download_history(symbol, "H1", start, end)
            if path and path.exists():
                from models.market_data import Candle
                import csv
                candles = []
                with open(path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            candles.append(Candle(
                                timestamp=datetime.fromtimestamp(int(row["time"]), tz=UTC),
                                open=float(row["open"]),
                                high=float(row["high"]),
                                low=float(row["low"]),
                                close=float(row["close"]),
                                volume=float(row["tick_volume"]),
                            ))
                        except Exception:
                            continue
                if candles:
                    return candles
        except Exception as exc:
            logger.debug("[neural] %s: data_downloader failed (%s) — using broker API", symbol, exc)

        # Fallback: fetch directly from broker (limited to broker's history)
        try:
            years_of_bars = 365 * settings.NEURAL_TRAIN_YEARS * 24
            candles = self._broker.get_candles(symbol, "H1", min(years_of_bars, 50000))
            return candles if candles else None
        except Exception as exc:
            logger.error("[neural] %s: candle fetch failed: %s", symbol, exc)
            return None

    # ── Path helpers ─────────────────────────────────────────────────────

    def _pt_path(self, symbol: str) -> Path:
        return self._models_dir / f"{symbol}_H1.pt"

    def _json_path(self, symbol: str) -> Path:
        return self._models_dir / f"{symbol}_H1.json"
