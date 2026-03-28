"""LSTM trading model — neural network core.

Architecture
------------
LSTMTradingModel:
  Input : (batch, seq_len, 20) — 20 normalised features per H1 bar
  Output: (batch, 3)           — logits for [BUY, SELL, HOLD]

Supporting utilities
--------------------
FeatureNormalizer  — per-feature z-score, save/load as JSON
build_features()   — candle list → numpy array (seq_len × 9)
auto_label()       — look-forward labelling for initial training
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)

# Class indices
BUY  = 0
SELL = 1
HOLD = 2

# ── Feature indices (must match build_features) ──────────────────────────
FEAT_NAMES = [
    # ── Base candle features (0–8) ────────────────────────────────────────
    "close_ret",        # log(close / prev_close)
    "high_body",        # (high - close) / ATR
    "low_body",         # (close - low) / ATR
    "candle_body",      # (close - open) / ATR
    "volume_z",         # (volume - vol_mean) / vol_std
    "rsi_centered",     # (RSI - 50) / 50
    "sma_ratio",        # (sma_fast - sma_slow) / ATR
    "atr_pct",          # ATR / close
    "spread_atr",       # spread / ATR  (0 when not available)
    # ── Time encoding (9–12) — circular so Mon≡Sun boundary is smooth ─────
    "hour_sin",         # sin(2π * hour / 24)
    "hour_cos",         # cos(2π * hour / 24)
    "dow_sin",          # sin(2π * day_of_week / 7)
    "dow_cos",          # cos(2π * day_of_week / 7)
    # ── Momentum & volatility envelope (13–14) ────────────────────────────
    "macd_hist",        # (MACD line - signal line) / ATR
    "bb_pos",           # (close - BB_lower) / (BB_upper - BB_lower)  ∈ [0,1]
    # ── Multi-timeframe bias (15–19, scalar broadcast across sequence) ────
    "h4_close_ret",     # log return of latest H4 candle
    "h4_rsi_centered",  # (H4 RSI - 50) / 50
    "h4_atr_pct",       # H4 ATR / H4 close
    "d1_close_ret",     # log return of latest D1 candle
    "d1_range_pos",     # (H1_close - D1_low) / (D1_high - D1_low)
]
N_FEATURES = len(FEAT_NAMES)  # 20


# ── RSI helper (does not require context — computed from candles) ─────────

def _compute_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Vectorised Wilder RSI over a close price array."""
    rsi = np.full(len(closes), 50.0)
    if len(closes) < period + 1:
        return rsi
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 1e-9 else 1e9
        rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def _compute_atr(highs: np.ndarray, lows: np.ndarray,
                 closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range array."""
    tr = np.maximum(highs[1:] - lows[1:],
         np.maximum(np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:]  - closes[:-1])))
    atr = np.full(len(closes), np.mean(tr[:period]) if len(tr) >= period else np.mean(tr))
    for i in range(1, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
    return atr


def _compute_ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    ema = np.full_like(arr, arr[0])
    k = 2.0 / (period + 1)
    for i in range(1, len(arr)):
        ema[i] = arr[i] * k + ema[i - 1] * (1 - k)
    return ema


def _compute_macd(closes: np.ndarray,
                  fast: int = 12, slow: int = 26, signal: int = 9
                  ) -> np.ndarray:
    """Return MACD histogram array (macd_line - signal_line)."""
    ema_fast   = _compute_ema(closes, fast)
    ema_slow   = _compute_ema(closes, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = _compute_ema(macd_line, signal)
    return macd_line - signal_line


def _compute_bb(closes: np.ndarray, period: int = 20,
                n_std: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Return (BB_lower, BB_upper) arrays."""
    lower = np.full_like(closes, closes[0])
    upper = np.full_like(closes, closes[0])
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        mean   = np.mean(window)
        std    = np.std(window) + 1e-9
        lower[i] = mean - n_std * std
        upper[i] = mean + n_std * std
    return lower, upper


# ── Feature builder ───────────────────────────────────────────────────────

def build_features(
    candles,                          # list[Candle] — must have ≥ seq_len bars
    seq_len: int = 50,
    spread: float = 0.0,
    sma_fast: float | None = None,
    sma_slow: float | None = None,
    timestamp=None,                   # datetime of the latest candle (for time encoding)
    h4_candles=None,                  # list[Candle] H4 — latest bars for HTF bias
    d1_candles=None,                  # list[Candle] D1 — latest bars for HTF bias
) -> np.ndarray | None:
    """Convert the last *seq_len* candles to a (seq_len, N_FEATURES) float32 array.

    Returns None if fewer than seq_len + 14 candles are available (need room
    to compute rolling indicators without look-ahead).
    """
    needed = seq_len + 14 + 1          # +14 for ATR/RSI warm-up, +1 for returns
    if len(candles) < needed:
        return None

    window = candles[-(needed):]       # enough history to warm up indicators

    opens   = np.array([c.open   for c in window], dtype=np.float64)
    highs   = np.array([c.high   for c in window], dtype=np.float64)
    lows    = np.array([c.low    for c in window], dtype=np.float64)
    closes  = np.array([c.close  for c in window], dtype=np.float64)
    volumes = np.array([c.volume for c in window], dtype=np.float64)

    atr_arr = _compute_atr(highs, lows, closes)
    rsi_arr = _compute_rsi(closes)

    # log returns
    log_ret = np.zeros_like(closes)
    log_ret[1:] = np.log(closes[1:] / np.where(closes[:-1] > 0, closes[:-1], 1e-9))

    # volume z-score (rolling over seq_len window)
    vol_mean = np.mean(volumes[-seq_len:])
    vol_std  = np.std(volumes[-seq_len:]) + 1e-9

    # SMA ratio — use passed-in context values for the most recent bar,
    # approximate for earlier bars via EWM
    if sma_fast is None or sma_slow is None:
        # Approximate from closes
        fast = np.convolve(closes, np.ones(10) / 10, mode='same')
        slow = np.convolve(closes, np.ones(50) / 50, mode='same') if len(closes) >= 50 else fast
    else:
        fast = np.convolve(closes, np.ones(10) / 10, mode='same')
        slow = np.convolve(closes, np.ones(50) / 50, mode='same') if len(closes) >= 50 else fast
        # Override last bar with live context values
        fast[-1] = sma_fast
        slow[-1] = sma_slow

    atr_safe = np.where(atr_arr > 1e-10, atr_arr, 1e-10)

    # ── Time encoding (circular, derived from each candle's timestamp) ────
    # Fall back to the provided timestamp or the candle's own timestamp.
    # For training windows we use each candle's actual timestamp.
    ts_arr = np.array([
        getattr(c, "timestamp", None) for c in window
    ], dtype=object)
    hours = np.array([
        (t.hour if t is not None else 0) for t in ts_arr
    ], dtype=np.float64)
    dows  = np.array([
        (t.weekday() if t is not None else 0) for t in ts_arr
    ], dtype=np.float64)
    if timestamp is not None:
        hours[-1] = float(timestamp.hour)
        dows[-1]  = float(timestamp.weekday())
    hour_sin = np.sin(2.0 * np.pi * hours / 24.0)
    hour_cos = np.cos(2.0 * np.pi * hours / 24.0)
    dow_sin  = np.sin(2.0 * np.pi * dows  /  7.0)
    dow_cos  = np.cos(2.0 * np.pi * dows  /  7.0)

    # ── MACD histogram ────────────────────────────────────────────────────
    macd_hist = _compute_macd(closes) / atr_safe

    # ── Bollinger Band position ───────────────────────────────────────────
    bb_lower, bb_upper = _compute_bb(closes)
    bb_range = np.where((bb_upper - bb_lower) > 1e-10, bb_upper - bb_lower, 1e-10)
    bb_pos   = np.clip((closes - bb_lower) / bb_range, 0.0, 1.0)

    # ── Multi-timeframe scalars (broadcast as constants across the window) ─
    def _scalar_feature(val: float) -> np.ndarray:
        return np.full(len(closes), val, dtype=np.float64)

    # H4 features
    if h4_candles and len(h4_candles) >= 2:
        h4c = h4_candles[-2:]
        h4_ret   = float(np.log(h4c[-1].close / h4c[-2].close) if h4c[-2].close > 0 else 0.0)
        h4_highs = np.array([c.high  for c in h4_candles[-15:]], dtype=np.float64)
        h4_lows  = np.array([c.low   for c in h4_candles[-15:]], dtype=np.float64)
        h4_cls   = np.array([c.close for c in h4_candles[-15:]], dtype=np.float64)
        h4_atr_v = float(_compute_atr(h4_highs, h4_lows, h4_cls)[-1])
        h4_rsi_v = float(_compute_rsi(h4_cls)[-1])
        h4_close_v = float(h4_candles[-1].close) or 1e-9
    else:
        h4_ret   = 0.0
        h4_atr_v = float(atr_arr[-1])
        h4_rsi_v = 50.0
        h4_close_v = float(closes[-1]) or 1e-9

    # D1 features
    if d1_candles and len(d1_candles) >= 2:
        d1c = d1_candles[-2:]
        d1_ret  = float(np.log(d1c[-1].close / d1c[-2].close) if d1c[-2].close > 0 else 0.0)
        d1_high = float(d1_candles[-1].high)
        d1_low  = float(d1_candles[-1].low)
    else:
        d1_ret  = 0.0
        d1_high = float(np.max(closes[-24:])) if len(closes) >= 24 else float(closes[-1])
        d1_low  = float(np.min(closes[-24:])) if len(closes) >= 24 else float(closes[-1])

    d1_range = (d1_high - d1_low) or 1e-9
    d1_range_pos_val = float(np.clip((closes[-1] - d1_low) / d1_range, 0.0, 1.0))

    feat_matrix = np.stack([
        log_ret,                                                    # 0  close_ret
        (highs  - closes) / atr_safe,                              # 1  high_body
        (closes - lows  ) / atr_safe,                              # 2  low_body
        (closes - opens ) / atr_safe,                              # 3  candle_body
        (volumes - vol_mean) / vol_std,                            # 4  volume_z
        (rsi_arr - 50.0) / 50.0,                                   # 5  rsi_centered
        (fast - slow) / atr_safe,                                  # 6  sma_ratio
        atr_arr / np.where(closes > 0, closes, 1e-9),              # 7  atr_pct
        np.full_like(closes, spread / (atr_safe[-1] or 1e-10)),    # 8  spread_atr
        hour_sin,                                                   # 9  hour_sin
        hour_cos,                                                   # 10 hour_cos
        dow_sin,                                                    # 11 dow_sin
        dow_cos,                                                    # 12 dow_cos
        macd_hist,                                                  # 13 macd_hist
        bb_pos,                                                     # 14 bb_pos
        _scalar_feature(h4_ret),                                   # 15 h4_close_ret
        _scalar_feature((h4_rsi_v - 50.0) / 50.0),                # 16 h4_rsi_centered
        _scalar_feature(h4_atr_v / h4_close_v),                   # 17 h4_atr_pct
        _scalar_feature(d1_ret),                                   # 18 d1_close_ret
        _scalar_feature(d1_range_pos_val),                         # 19 d1_range_pos
    ], axis=1)  # (needed, N_FEATURES=20)

    # Return only the last seq_len bars (indicators are warmed up now)
    return feat_matrix[-seq_len:].astype(np.float32)


# ── Auto-labeller for initial training ───────────────────────────────────

def auto_label(
    candles,
    horizon: int = 20,
    atr_mult: float = 1.5,
) -> np.ndarray:
    """Label every bar in *candles* as BUY/SELL/HOLD.

    For bar i, look forward *horizon* bars.  The first direction to move
    ≥ atr_mult × ATR from the entry (close[i]) wins:
      - Up first  → BUY  (0)
      - Down first → SELL (1)
      - Neither    → HOLD (2)

    Returns an int8 array of length len(candles).
    """
    closes = np.array([c.close for c in candles], dtype=np.float64)
    highs  = np.array([c.high  for c in candles], dtype=np.float64)
    lows   = np.array([c.low   for c in candles], dtype=np.float64)
    atr_arr = _compute_atr(highs, lows, closes)

    labels = np.full(len(candles), HOLD, dtype=np.int8)

    for i in range(len(candles) - horizon):
        entry = closes[i]
        atr   = atr_arr[i] or 1e-9
        target_up   = entry + atr_mult * atr
        target_down = entry - atr_mult * atr

        hit_up = hit_down = False
        for j in range(i + 1, i + 1 + horizon):
            if highs[j] >= target_up and not hit_down:
                hit_up = True
                break
            if lows[j] <= target_down and not hit_up:
                hit_down = True
                break

        if hit_up:
            labels[i] = BUY
        elif hit_down:
            labels[i] = SELL
        # else HOLD

    return labels


# ── Feature normaliser ───────────────────────────────────────────────────

class FeatureNormalizer:
    """Per-feature z-score normaliser.  Fitted on training data only."""

    def __init__(self) -> None:
        self.mean: np.ndarray | None = None
        self.std:  np.ndarray | None = None

    def fit(self, X: np.ndarray) -> None:
        """X: (N, seq_len, n_features) or (N, n_features)."""
        flat = X.reshape(-1, X.shape[-1])
        self.mean = flat.mean(axis=0).astype(np.float32)
        self.std  = (flat.std(axis=0) + 1e-9).astype(np.float32)

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean is None:
            return X
        return ((X - self.mean) / self.std).astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "mean": self.mean.tolist() if self.mean is not None else None,
            "std":  self.std.tolist()  if self.std  is not None else None,
        }
        path.write_text(json.dumps(data), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.mean = np.array(data["mean"], dtype=np.float32) if data["mean"] else None
        self.std  = np.array(data["std"],  dtype=np.float32) if data["std"]  else None


# ── LSTM model ───────────────────────────────────────────────────────────

class LSTMTradingModel(nn.Module):
    """2-layer LSTM + self-attention head → 3-class output.

    Architecture
    ------------
    LSTM(input_size, hidden_size, num_layers)  → (batch, seq_len, hidden)
    Attention linear(hidden → 1)               → softmax weights over seq_len
    Weighted sum                               → context vector (batch, hidden)
    Dropout → Linear(hidden → 3)              → logits (batch, 3)

    Input : (batch, seq_len, N_FEATURES)
    Output: (batch, 3)  raw logits (apply softmax for probabilities)
    """

    def __init__(
        self,
        input_size:  int = N_FEATURES,
        hidden_size: int = 64,
        num_layers:  int = 2,
        dropout:     float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.attn    = nn.Linear(hidden_size, 1, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.fc      = nn.Linear(hidden_size, 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)                          # (batch, seq_len, hidden)
        scores  = self.attn(out)                       # (batch, seq_len, 1)
        weights = torch.softmax(scores, dim=1)         # (batch, seq_len, 1)
        context = (weights * out).sum(dim=1)           # (batch, hidden)
        return self.fc(self.dropout(context))          # (batch, 3) logits

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "LSTMTradingModel":
        model = cls(**kwargs)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        model.eval()
        return model

    # ── Inference helper ─────────────────────────────────────────────────

    @torch.no_grad()
    def predict_proba(self, x_seq: np.ndarray) -> np.ndarray:
        """x_seq: (seq_len, n_features) → probabilities [BUY, SELL, HOLD]."""
        t = torch.tensor(x_seq, dtype=torch.float32).unsqueeze(0)  # (1, seq, feat)
        logits = self(t)
        return torch.softmax(logits, dim=-1).squeeze(0).numpy()
