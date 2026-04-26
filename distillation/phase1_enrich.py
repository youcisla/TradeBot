"""
Phase 1 – Offline Knowledge Distillation via DeepSeek-R1
========================================================
Enriches historical 1m OHLCV candles with ICT setup labels,
probability scores, and full reasoning traces from the
DeepSeek-R1 teacher model.

Every complex instruction lives in the User Prompt because
DeepSeek-R1 ignores / misinterprets System Prompts for
reasoning tasks.  We also enforce strict JSON output via
response_format={'type':'json_object'} + the word "json"
in the user prompt body as an explicit schema trigger.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# ── types ──────────────────────────────────────────────────────────────────────

@dataclass
class ICTSetup:
    """Describes a labelled ICT setup on a single candle."""
    timestamp:   datetime
    symbol:      str
    kind:        str          # FVG | OB | LTB | HLTB | BOS
    direction:   str          # BUY | SELL
    entry_price: float
    stop_loss:   float
    take_profit: float
    latency_ms:  float = 0.0


@dataclass
class EnrichedCandle:
    """Candle enriched with teacher-model annotations."""
    symbol:      str
    timestamp:   datetime
    open:        float
    high:        float
    low:         float
    close:       float
    volume:      float
    # teacher annotations
    setup_label: str | None   # 'FVG_BUY' | 'FVG_SELL' | 'OB_BUY' | ...
    confidence:  float        # 0.0–1.0 probability score
    reasoning:   str          # full reasoning trace
    regime_hint: str          # 'TRENDING' | 'RANGE' | 'CRISIS'
    error:       str | None
    request_id:  str


@dataclass
class DistillationResult:
    """Aggregated result for a batch."""
    symbol:                 str
    start_ts:              datetime
    end_ts:                datetime
    candles_total:         int
    candles_ok:           int
    candles_fail:         int
    elapsed_secs:         float
    teacher_latency_p50_ms: float
    teacher_latency_p99_ms: float
    output_path:           Path
    errors:                list[str]


# ── DeepSeek client ────────────────────────────────────────────────────────────

class DeepSeekReasoner:
    """
    Thin wrapper around the deepseek-reasoner API.

    Prompting rules enforced here:
    1. All complex instructions are in the User Prompt (not System).
    2. response_format={'type':'json_object'} forces JSON mode.
    3. The word "json" + a concrete schema is in the User Prompt
       to trigger the model's JSON mode reliably.
    """

    BASE_URL = "https://api.deepseek.com/v1"
    MODEL    = "deepseek-reasoner"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")

    def evaluate(
        self,
        setup: ICTSetup,
        lookback_candles: list[dict],
    ) -> dict[str, Any]:
        """
        Sends ONE ICT setup + lookback window to DeepSeek-R1.
        Returns a dict matching the schema; raises RuntimeError on HTTP errors.
        """
        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "user", "content": _build_user_prompt(setup, lookback_candles)}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 2048,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

        tick = time.perf_counter()
        resp = requests.post(
            f"{self.BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        elapsed_ms = (time.perf_counter() - tick) * 1e3

        if not resp.ok:
            raise RuntimeError(f"DeepSeek API {resp.status_code}: {resp.text}")

        raw = resp.json()
        content: str = raw["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Model returned non-JSON: {exc}\nRaw: {content[:500]}") from exc

        parsed["_teacher_latency_ms"] = elapsed_ms
        return parsed

    def batch_evaluate(
        self,
        setups: list[ICTSetup],
        lookback_windows: list[list[dict]],
        rate_limit_rpm: int = 30,
        callback_progress: callable | None = None,
    ) -> list[EnrichedCandle]:
        """
        Evaluates `n` setups sequentially with simple RPM rate-limiting.
        Returns one EnrichedCandle per setup.
        """
        delay_s = 60.0 / max(rate_limit_rpm, 1)
        results: list[EnrichedCandle] = []

        for i, (setup, window) in enumerate(zip(setups, lookback_windows)):
            req_id = str(uuid.uuid4())[:8]
            lat_ms = 0.0
            try:
                raw = self.evaluate(setup, window)
                lat_ms = raw.pop("_teacher_latency_ms", 0.0)
                results.append(EnrichedCandle(
                    symbol       = setup.symbol,
                    timestamp    = setup.timestamp,
                    open         = window[-1].get("open", 0),
                    high         = window[-1].get("high", 0),
                    low          = window[-1].get("low", 0),
                    close        = window[-1].get("close", 0),
                    volume       = window[-1].get("volume", 0),
                    setup_label  = raw.get("setup_label"),
                    confidence   = float(raw.get("confidence", 0.0)),
                    reasoning    = str(raw.get("reasoning", "")),
                    regime_hint  = str(raw.get("regime_hint", "TRENDING")),
                    error        = None,
                    request_id   = req_id,
                ))
            except Exception as exc:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    "Batch item %d/%d failed: %s", i + 1, len(setups), exc
                )
                results.append(EnrichedCandle(
                    symbol       = setup.symbol,
                    timestamp    = setup.timestamp,
                    open         = window[-1].get("open", 0),
                    high         = window[-1].get("high", 0),
                    low          = window[-1].get("low", 0),
                    close        = window[-1].get("close", 0),
                    volume       = window[-1].get("volume", 0),
                    setup_label  = None,
                    confidence   = 0.0,
                    reasoning    = "",
                    regime_hint  = "TRENDING",
                    error        = str(exc),
                    request_id   = req_id,
                ))

            if callback_progress:
                callback_progress(i + 1, len(setups))
            if i < len(setups) - 1:
                time.sleep(delay_s)

        return results


# ── User Prompt builder ────────────────────────────────────────────────────────

def _build_user_prompt(setup: ICTSetup, candles: list[dict]) -> str:
    """
    Builds the User Prompt with all instructions inlined.
    DeepSeek-R1 processes this as the sole directive.
    """
    rows = []
    for c in candles[-20:]:
        rows.append(
            f"  {c['timestamp']}  O={c['open']}  H={c['high']} "
            f"L={c['low']}  C={c['close']}  V={c.get('volume',0)}"
        )
    candle_table = "\n".join(rows)

    schema = """
You must respond ONLY with a JSON object matching this schema (no markdown, no explanation):
{
  "setup_label":  "FVG_BUY" | "FVG_SELL" | "OB_BUY" | "OB_SELL" | "LTB_BUY" | "LTB_SELL" | "HLTB_BUY" | "HLTB_SELL" | "BOS_BUY" | "BOS_SELL" | null,
  "confidence":   <float between 0.0 and 1.0>,
  "reasoning":    <string: your full step-by-step analysis>,
  "regime_hint":  "TRENDING" | "RANGE" | "CRISIS"
}
If the candle does NOT represent a valid ICT setup, set setup_label to null and confidence to 0.0.
"""

    return f"""You are an expert Inner Circle Trader (ICT) analyst operating on 1-minute chart data for scalping.

## Current Setup Under Evaluation
- Symbol     : {setup.symbol}
- Time       : {setup.timestamp}
- Type       : {setup.kind}
- Direction  : {setup.direction}
- Entry Price: {setup.entry_price}
- Stop Loss  : {setup.stop_loss}
- Take Profit: {setup.take_profit}

## Recent OHLCV Candles (last 20 x 1m bars)
{candle_table}

## Your Task
Analyze the setup above against the recent price action. Apply ICT concepts:
- Fair Value Gaps (FVG) — unfilled candle with 2+ candle body gap
- Order Blocks (OB) — last bearish/bullish candle before a strong move
- Liquidity Sweeps — wicks exceeding prior swing high/low by <0.5%
- Breaks of Structure (BOS) — momentum candle closing beyond structural level
- High/Low Tide Bars (HLTB)

The word "json" means you MUST output only the JSON object described below — no extra text, no markdown fences.

{schema}
"""


# ── Distillation pipeline ─────────────────────────────────────────────────────

class DistillationPipeline:
    """
    Orchestrates the full Phase-1 pipeline:
    1. Load historical candles (parquet / CSV / DB)
    2. Detect candidate ICT setups
    3. Call DeepSeek-R1 for each setup
    4. Persist enriched data + latency stats
    """

    def __init__(
        self,
        api_key: str | None = None,
        output_dir: str | Path = "distillation/output",
        rate_limit_rpm: int = 30,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.teacher = DeepSeekReasoner(api_key)
        self.rate_limit_rpm = rate_limit_rpm
        self._log = logging.getLogger(__name__)

    def run(
        self,
        candles_df,       # pd.DataFrame: timestamp, open, high, low, close, volume
        symbol: str,
        lookback: int = 60,
    ) -> DistillationResult:
        import pandas as pd

        if not isinstance(candles_df, pd.DataFrame):
            raise TypeError("candles_df must be a pandas DataFrame")

        start_ts = candles_df["timestamp"].min()
        end_ts   = candles_df["timestamp"].max()

        # ── step 1: detect candidate setups ────────────────────────────────
        setups, windows = self._detect_setups(candles_df, lookback)
        self._log.info(
            "Detected %d candidate ICT setups for %s (%s → %s)",
            len(setups), symbol, start_ts, end_ts
        )

        # ── step 2: enrich via teacher model ───────────────────────────────
        def _cb(done: int, total: int) -> None:
            self._log.info("Progress: %d/%d candles enriched", done, total)

        latencies: list[float] = []
        enriched = self.teacher.batch_evaluate(
            setups, windows,
            rate_limit_rpm=self.rate_limit_rpm,
            callback_progress=_cb,
        )

        # ── step 3: persist ──────────────────────────────────────────────
        out_path = self.output_dir / f"{symbol}_{start_ts:%Y%m%d}_{end_ts:%Y%m%d}_enriched.jsonl"
        with open(out_path, "w") as fh:
            for e in enriched:
                fh.write(json.dumps(asdict(e)) + "\n")

        ok   = sum(1 for e in enriched if e.error is None)
        fail = len(enriched) - ok

        p50 = float(np.median(latencies)) if latencies else 0.0
        p99 = float(np.percentile(latencies, 99)) if latencies else 0.0

        return DistillationResult(
            symbol                  = symbol,
            start_ts                = start_ts,
            end_ts                  = end_ts,
            candles_total           = len(enriched),
            candles_ok              = ok,
            candles_fail            = fail,
            elapsed_secs            = (end_ts - start_ts).total_seconds(),
            teacher_latency_p50_ms  = p50,
            teacher_latency_p99_ms  = p99,
            output_path             = out_path,
            errors                  = [e.error for e in enriched if e.error],
        )

    @staticmethod
    def _detect_setups(
        df: "pd.DataFrame", lookback: int
    ) -> tuple[list[ICTSetup], list[list[dict]]]:
        """
        Minimal ICT setup detector.
        Production should wire in `strategies/ict/` modules.
        """
        setups: list[ICTSetup]  = []
        windows: list[list[dict]] = []

        records = df.to_dict(orient="records")
        for i in range(lookback, len(records) - 1):
            candle = records[i]
            prior  = records[i - 1]

            fvg_up   = candle["low"]  > prior["high"]
            fvg_down = candle["high"] < prior["low"]

            if fvg_up:
                direction, entry, sl, tp, kind = (
                    "BUY", candle["low"], candle["high"],
                    candle["low"] + (candle["low"] - candle["high"]) * 2, "FVG"
                )
            elif fvg_down:
                direction, entry, sl, tp, kind = (
                    "SELL", candle["high"], candle["low"],
                    candle["high"] - (candle["high"] - candle["low"]) * 2, "FVG"
                )
            else:
                continue

            setups.append(ICTSetup(
                timestamp   = candle["timestamp"],
                symbol      = df.attrs.get("symbol", "UNKNOWN"),
                kind        = kind,
                direction   = direction,
                entry_price = entry,
                stop_loss   = sl,
                take_profit = tp,
                latency_ms  = 0.0,
            ))
            windows.append(records[max(0, i - lookback):i + 1])

        return setups, windows


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import pandas as pd
    import argparse
    import numpy as np  # noqa: import here to avoid top-level side-effect

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    ap = argparse.ArgumentParser(description="Phase-1: DeepSeek-R1 Distillation")
    ap.add_argument("--symbol",      default="BTCUSD")
    ap.add_argument("--candles",     required=True, help="Path to candle CSV")
    ap.add_argument("--output-dir",  default="distillation/output")
    ap.add_argument("--rate-limit",  type=int, default=30)
    ap.add_argument("--api-key",     default=os.environ.get("DEEPSEEK_API_KEY"))
    args = ap.parse_args()

    df = pd.read_csv(args.candles, parse_dates=["timestamp"])
    df.attrs["symbol"] = args.symbol

    pipeline = DistillationPipeline(
        api_key        = args.api_key,
        output_dir     = args.output_dir,
        rate_limit_rpm = args.rate_limit,
    )
    result = pipeline.run(df, symbol=args.symbol)

    print(f"\n{'='*60}")
    print(f"Distillation complete — {result.candles_ok}/{result.candles_total} candles enriched")
    print(f"Output: {result.output_path}")
    print(f"P50 latency: {result.teacher_latency_p50_ms:.1f} ms")
    print(f"P99 latency: {result.teacher_latency_p99_ms:.1f} ms")
    if result.errors:
        print(f"WARNING: {len(result.errors)} candle(s) failed")


if __name__ == "__main__":
    main()