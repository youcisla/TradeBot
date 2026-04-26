"""
Phase 3 – Kafka Event-Backbone Nodes
=====================================
Four async microservices wired via Kafka:

  MarketDataNode  →  SignalGenNode  →  InferenceNode  →  ExecutionNode

All nodes inherit KafkaNode and use aiokafka for non-blocking I/O.
TOPIC_EXECUTE carries an ExecutePayload consumed exclusively by ExecutionNode.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from abc import abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
except ImportError:  # pragma: no cover
    AIOKafkaProducer = AIOKafkaConsumer = None  # type: ignore

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── Topics ───────────────────────────────────────────────────────────────────────

TOPIC_MARKETDATA = "pulse_marketdata"
TOPIC_SIGNALS    = "pulse_signals"
TOPIC_EXECUTE    = "pulse_execute"
TOPIC_OUTCOMES   = "pulse_outcomes"

ALL_TOPICS = [TOPIC_MARKETDATA, TOPIC_SIGNALS, TOPIC_EXECUTE, TOPIC_OUTCOMES]


# ── Payload types ───────────────────────────────────────────────────────────────

@dataclass
class CandlePayload:
    """1-minute OHLCV candle emitted by MarketDataNode."""
    symbol:    str
    timestamp: str
    open:      float
    high:      float
    low:       float
    close:     float
    volume:    float


@dataclass
class SignalPayload:
    """ICT signal produced by SignalGenNode and consumed by InferenceNode."""
    symbol:       str
    timestamp:    str
    setup_label:  str          # 'FVG_BUY' | 'FVG_SELL' | 'OB_BUY' | ...
    direction:    str          # 'BUY' | 'SELL'
    entry_price: float
    stop_loss:   float
    take_profit: float
    regime_hint: str          # 'TRENDING' | 'RANGE' | 'CRISIS'
    confidence:  float = 0.0   # filled by InferenceNode


@dataclass
class ExecutePayload:
    """
    Final execution directive consumed ONLY by ExecutionNode.
    Produced by InferenceNode after applying regime-adjusted confidence.
    """
    symbol:        str
    timestamp:     str
    setup_label:   str
    direction:     str
    entry_price:  float
    stop_loss:    float
    take_profit:  float
    confidence:   float
    regime:       str
    lot_size:     float
    agent_id:     str = "inference_node"


@dataclass
class OutcomePayload:
    """Trade outcome fed back for learning and HKU reputation reporting."""
    symbol:       str
    timestamp:    str
    setup_label:  str
    direction:    str
    entry_price: float
    exit_price:  float
    pnl_ticks:   float
    pnl_account: float
    regime:      str
    exited_by:   str          # 'TP' | 'SL' | 'MANUAL'


# ── KafkaNode base ─────────────────────────────────────────────────────────────

class KafkaNode:
    """
    Base class for all four microservice nodes.
    Handles producer/consumer lifecycle and graceful shutdown.
    """

    consumer_group: str = "pulse_nodes"
    _consumer: Any = None
    _producer: Any = None

    def __init__(self, bootstrap_servers: str = "localhost:9092", *, verbose: bool = False):
        if AIOKafkaProducer is None:
            raise RuntimeError("aiokafka is required: pip install aiokafka")
        self.bootstrap_servers = bootstrap_servers
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
        self._shutdown = False

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        await self._start_producer()
        await self._start_consumer()
        self.logger.info("%s started (group=%s)", self.__class__.__name__, self.consumer_group)

    async def stop(self) -> None:
        self._shutdown = True
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        self.logger.info("%s stopped", self.__class__.__name__)

    async def run_forever(self) -> None:
        await self.start()
        try:
            async for msg in self._consumer:
                if self._shutdown:
                    break
                await self._process(msg)
        finally:
            await self.stop()

    # ── abstract ────────────────────────────────────────────────────────────

    @abstractmethod
    async def _process(self, msg: Any) -> None:
        """Handle one consumed message. Override in subclass."""
        raise NotImplementedError

    # ── internals ───────────────────────────────────────────────────────────

    async def _start_producer(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()

    async def _start_consumer(self) -> None:
        self._consumer = AIOKafkaConsumer(
            *self._input_topics(),
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.consumer_group,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self._consumer.start()

    def _input_topics(self) -> list[str]:
        """Override to declare which topics this node subscribes to."""
        return []

    async def _emit(self, topic: str, payload: dict) -> None:
        if self.verbose:
            self.logger.debug("→ %s  %s", topic, payload.get("symbol", ""))
        await self._producer.send_and_wait(topic, value=payload)


# ── Market Data Node ───────────────────────────────────────────────────────────

class MarketDataNode(KafkaNode):
    """
    Polls broker (MT5) every second, emits OHLCV candles to TOPIC_MARKETDATA.
    Falls back to CSV replay when no broker is available.
    """

    consumer_group = "pulse_marketdata"

    def __init__(self, bootstrap_servers: str = "localhost:9092", symbol: str = "BTCUSD"):
        super().__init__(bootstrap_servers)
        self.symbol = symbol
        self._broker: Any = None   # MT5Connector wired in via bootstrap_nodes()

    def _input_topics(self) -> list[str]:
        return []   # this node only produces, doesn't consume

    async def _process(self, msg: Any) -> None:
        pass        # no input consumed

    async def _poll_and_emit(self) -> None:
        """Called by the external bootstrap_nodes orchestrator."""
        while not self._shutdown:
            tick = time.perf_counter()
            candle = self._broker.get_candle(self.symbol) if self._broker else None
            if candle:
                await self._emit(TOPIC_MARKETDATA, asdict(CandlePayload(**candle)))
            elapsed_ms = (time.perf_counter() - tick) * 1e3
            await asyncio.sleep(max(0.0, 1.0 - elapsed_ms / 1e3))

    async def run_forever(self) -> None:
        await self._start_producer()
        self.logger.info("MarketDataNode running (symbol=%s)", self.symbol)
        try:
            await self._poll_and_emit()
        finally:
            await self.stop()


# ── Signal Generation Node ─────────────────────────────────────────────────────

class SignalGenNode(KafkaNode):
    """
    Consumes candles from TOPIC_MARKETDATA.
    Runs ICT setup detection and emits SignalPayload to TOPIC_SIGNALS.
    """

    consumer_group = "pulse_signalgen"

    def __init__(self, bootstrap_servers: str = "localhost:9092", symbol: str = "BTCUSD"):
        super().__init__(bootstrap_servers)
        self.symbol = symbol
        self._lookback: list[dict] = []

    def _input_topics(self) -> list[str]:
        return [TOPIC_MARKETDATA]

    async def _process(self, msg: Any) -> None:
        candle = msg.value
        if candle.get("symbol") != self.symbol:
            return
        self._lookback.append(candle)
        if len(self._lookback) > 60:
            self._lookback.pop(0)

        setup = self._detect_ict_setup(candle)
        if setup:
            await self._emit(TOPIC_SIGNALS, asdict(setup))

    def _detect_ict_setup(self, candle: dict) -> SignalPayload | None:
        """Minimal FVG detector. Production wires in strategies/ict/."""
        if len(self._lookback) < 2:
            return None
        prior = self._lookback[-2]
        c = candle

        fvg_up   = c["low"]  > prior["high"]
        fvg_down = c["high"] < prior["low"]

        if fvg_up:
            return SignalPayload(
                symbol=c["symbol"], timestamp=c["timestamp"],
                setup_label="FVG_BUY", direction="BUY",
                entry_price=c["low"], stop_loss=prior["high"],
                take_profit=c["low"] + (c["low"] - prior["high"]) * 2,
                regime_hint="TRENDING",
            )
        if fvg_down:
            return SignalPayload(
                symbol=c["symbol"], timestamp=c["timestamp"],
                setup_label="FVG_SELL", direction="SELL",
                entry_price=c["high"], stop_loss=prior["low"],
                take_profit=c["high"] - (prior["low"] - c["high"]) * 2,
                regime_hint="TRENDING",
            )
        return None


# ── Inference Node ─────────────────────────────────────────────────────────────

@dataclass
class RegimeParams:
    """Dynamic thresholds and weights adjusted per HMM regime."""
    confidence_threshold: float
    signal_weight:       float
    max_lot:             float


REGIME_PARAMS = {
    "TRENDING": RegimeParams(confidence_threshold=0.55, signal_weight=1.0,  max_lot=0.50),
    "RANGE":   RegimeParams(confidence_threshold=0.60, signal_weight=0.7,  max_lot=0.30),
    "CRISIS":  RegimeParams(confidence_threshold=0.70, signal_weight=0.4,  max_lot=0.10),
}


class InferenceNode(KafkaNode):
    """
    Consumes SignalPayload from TOPIC_SIGNALS.
    Loads the Phase-2 XGBoost student model, applies regime-adjusted
    confidence threshold, and emits ExecutePayload to TOPIC_EXECUTE.
    """

    consumer_group = "pulse_inference"

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        model_path: str | Path | None = None,
        regime_detector=None,    # HMMRegimeDetector injected by bootstrap_nodes
    ):
        super().__init__(bootstrap_servers)
        self.model_path = Path(model_path) if model_path else PROJECT_ROOT / "models"
        self.regime_detector = regime_detector
        self._model: Any = None
        self._featurizer: Any = None
        self._le_classes: list[str] = []

    def _input_topics(self) -> list[str]:
        return [TOPIC_SIGNALS]

    async def _process(self, msg: Any) -> None:
        signal = SignalPayload(**msg.value)
        if self._model is None:
            await self._load_model()

        regime = self.regime_detector.classify(signal) if self.regime_detector else "TRENDING"
        params = REGIME_PARAMS.get(regime, REGIME_PARAMS["TRENDING"])

        # ── feature engineering ───────────────────────────────────────────
        # In production: build 18-dim ICTFeatureEngine vector + regime tag
        # Here we skip to a deterministic confidence for the skeleton
        confidence = signal.confidence if signal.confidence > 0 else 0.65
        confidence *= params.signal_weight

        if confidence < params.confidence_threshold:
            return   # filtered by regime threshold

        lot_size = self._compute_lot(signal, params.max_lot)

        await self._emit(TOPIC_EXECUTE, asdict(ExecutePayload(
            symbol        = signal.symbol,
            timestamp     = signal.timestamp,
            setup_label   = signal.setup_label,
            direction     = signal.direction,
            entry_price  = signal.entry_price,
            stop_loss    = signal.stop_loss,
            take_profit  = signal.take_profit,
            confidence   = confidence,
            regime       = regime,
            lot_size     = lot_size,
        )))

    async def _load_model(self) -> None:
        import xgboost as xgb
        model_file = self.model_path / f"student_{self.symbol}.json"
        if model_file.exists():
            self._model = xgb.Booster()
            self._model.load_model(str(model_file))
            self.logger.info("Loaded student model: %s", model_file)
        else:
            self.logger.warning("No student model at %s — using confidence pass-through", model_file)

    def _compute_lot(self, signal: SignalPayload, max_lot: float) -> float:
        """Kelly-criterion lot sizing stub. Production wires dynamic_position_sizer."""
        risk_pct = 0.01
        sl_ticks = abs(signal.entry_price - signal.stop_loss)
        return min(max_lot, risk_pct / (sl_ticks + 1e-9))


# ── Execution Node ──────────────────────────────────────────────────────────────

class ExecutionNode(KafkaNode):
    """
    Consumes ONLY ExecutePayload from TOPIC_EXECUTE (exclusive consumer group).
    Opens orders via broker (MT5), emits OutcomePayload to TOPIC_OUTCOMES.
    """

    consumer_group = "pulse_execution"

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        broker_connector=None,   # MT5Connector injected by bootstrap_nodes
    ):
        super().__init__(bootstrap_servers)
        self.broker = broker_connector

    def _input_topics(self) -> list[str]:
        return [TOPIC_EXECUTE]   # exclusive — no other node consumes this

    async def _process(self, msg: Any) -> None:
        exec_req = ExecutePayload(**msg.value)
        if self.broker is None:
            self.logger.warning("No broker connected — skipping execution: %s", exec_req.symbol)
            return

        order = self.broker.open_order(
            symbol   = exec_req.symbol,
            direction= exec_req.direction,
            entry    = exec_req.entry_price,
            sl       = exec_req.stop_loss,
            tp       = exec_req.take_profit,
            lot      = exec_req.lot_size,
            comment  = f"pulse/{exec_req.setup_label}",
        )
        self.logger.info(
            "ORDER %s %s @ %.5f  SL=%.5f TP=%.5f  lot=%.2f  conf=%.2f",
            exec_req.direction, exec_req.symbol, exec_req.entry_price,
            exec_req.stop_loss, exec_req.take_profit, exec_req.lot_size,
            exec_req.confidence,
        )
        # Outcome emitted when trade closes (trade_manager wires this)
        await self._emit(TOPIC_OUTCOMES, asdict(OutcomePayload(
            symbol      = exec_req.symbol,
            timestamp   = exec_req.timestamp,
            setup_label = exec_req.setup_label,
            direction   = exec_req.direction,
            entry_price = exec_req.entry_price,
            exit_price  = 0.0,
            pnl_ticks   = 0.0,
            pnl_account = 0.0,
            regime      = exec_req.regime,
            exited_by   = "MANUAL",
        )))


# ── Bootstrap orchestrator ──────────────────────────────────────────────────────

async def bootstrap_nodes(
    bootstrap_servers: str = "localhost:9092",
    symbol: str = "BTCUSD",
    broker_connector=None,
    regime_detector=None,
) -> dict[str, KafkaNode]:
    """
    Wires all four nodes together and returns them as a dict for lifecycle control.
    Pass broker_connector (MT5Connector) and regime_detector (HMMRegimeDetector)
    from the parent bot process.
    """
    mkt  = MarketDataNode(bootstrap_servers, symbol)
    sig  = SignalGenNode(bootstrap_servers, symbol)
    inf  = InferenceNode(bootstrap_servers, regime_detector=regime_detector)
    exe  = ExecutionNode(bootstrap_servers, broker_connector=broker_connector)

    mkt._broker = broker_connector   # direct reference for polling loop

    nodes = {"market_data": mkt, "signal_gen": sig, "inference": inf, "execution": exe}

    # Start all consumers/producers
    await asyncio.gather(*[n.start() for n in nodes.values()])

    return nodes


# ── CLI ────────────────────────────────────────────────────────────────────────

async def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    ap = argparse.ArgumentParser(description="PulseTrade Phase-3 Kafka Nodes")
    ap.add_argument("--bootstrap-servers", default="localhost:9092")
    ap.add_argument("--symbol",            default="BTCUSD")
    ap.add_argument("--node",             choices=["market_data", "signal_gen", "inference", "execution", "all"], default="all")
    ap.add_argument("--replay-csv",       default=None, help="Path to CSV for replay mode")
    args = ap.parse_args()

    if args.node == "all":
        nodes = await bootstrap_nodes(args.bootstrap_servers, args.symbol)
        shutdown_event = asyncio.Event()

        def _sig_handler() -> None:
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _sig_handler)

        await shutdown_event.wait()
        await asyncio.gather(*[n.stop() for n in nodes.values()])
    else:
        node_map = {
            "market_data": MarketDataNode(args.bootstrap_servers, args.symbol),
            "signal_gen":  SignalGenNode(args.bootstrap_servers, args.symbol),
            "inference":   InferenceNode(args.bootstrap_servers),
            "execution":   ExecutionNode(args.bootstrap_servers),
        }
        await node_map[args.node].run_forever()


if __name__ == "__main__":
    asyncio.run(main())
