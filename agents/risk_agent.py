"""Risk Agent — validates every signal before execution.

Answers: *Is it safe?*

Implements (in order):
1.  Drawdown circuit breaker
1b. Crucix macro blackout
2.  Duplicate signal guard
3.  Correlation guard
4.  Max open trades
5.  Live spread check (per-asset-class)
7.  Position sizing
"""

from __future__ import annotations

import logging
import math
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Callable

from broker.connector import BrokerConnector
from config import settings
from config.symbols import pip_value, asset_class
from models.signal import Signal
from models.trade import Trade
from utils import telegram_bot
from utils.helpers import current_session, day_of_week, is_weekend
from utils.mesh_bus import mesh_span

if TYPE_CHECKING:
    from agents.crucix_agent import CrucixAgent
    from agents.exposure_agent import ExposureCoach
    from database.db import Database

logger = logging.getLogger(__name__)


# ── Cross-pair correlation table ─────────────────────────────────────────
# Maps each symbol to a set of symbols that are *positively* correlated
# with it in the same direction (e.g. all USD-short vs USD-long pairs).
# Holding a signal's symbol AND any of these in the SAME direction means
# overlapping exposure — the second trade is blocked.
_CORRELATED_PAIRS: dict[str, frozenset[str]] = {
    # USD-short pairs (BUY = short USD)
    "EURUSD": frozenset({"GBPUSD", "AUDUSD", "NZDUSD", "EURJPY", "GBPJPY",
                          "EURCAD", "EURAUD", "EURCHF"}),
    "GBPUSD": frozenset({"EURUSD", "AUDUSD", "NZDUSD", "GBPJPY", "GBPAUD",
                          "GBPCHF"}),
    "AUDUSD": frozenset({"EURUSD", "GBPUSD", "NZDUSD", "AUDJPY", "EURAUD",
                          "GBPAUD", "AUDNZD"}),
    "NZDUSD": frozenset({"EURUSD", "GBPUSD", "AUDUSD", "AUDNZD"}),
    # USD-long pairs (BUY = long USD)
    "USDJPY": frozenset({"USDCAD", "USDCHF", "USDZAR", "USDMXN", "CADJPY",
                          "CHFJPY"}),
    "USDCAD": frozenset({"USDJPY", "USDCHF", "CADJPY"}),
    "USDCHF": frozenset({"USDJPY", "USDCAD", "CHFJPY"}),
    # JPY crosses
    "EURJPY": frozenset({"GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"}),
    "GBPJPY": frozenset({"EURJPY", "AUDJPY", "CADJPY"}),
    "AUDJPY": frozenset({"EURJPY", "GBPJPY", "CADJPY"}),
    "CADJPY": frozenset({"USDJPY", "USDCAD", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY"}),
    "CHFJPY": frozenset({"USDJPY", "USDCHF", "EURJPY", "CADJPY"}),
    # Non-USD crosses
    "GBPAUD": frozenset({"GBPUSD", "AUDUSD", "EURAUD"}),
    "GBPCHF": frozenset({"GBPUSD", "USDCHF", "EURCHF"}),
    "EURAUD": frozenset({"EURUSD", "AUDUSD", "GBPAUD"}),
    "EURCHF": frozenset({"EURUSD", "USDCHF", "GBPCHF"}),
    "EURCAD": frozenset({"EURUSD", "USDCAD"}),
    "AUDNZD": frozenset({"AUDUSD", "NZDUSD"}),
    # Indices — US cluster
    "US30":   frozenset({"US500", "USTEC"}),
    "US500":  frozenset({"US30",  "USTEC"}),
    "USTEC":  frozenset({"US30",  "US500"}),
    # Indices — European cluster
    "GER40":  frozenset({"FRA40", "EU50", "UK100"}),
    "FRA40":  frozenset({"GER40", "EU50"}),
    "EU50":   frozenset({"GER40", "FRA40"}),
    # Precious metals / safe-haven
    "XAUUSD": frozenset({"XAGUSD", "XPTUSD", "XPDUSD"}),
    "XAGUSD": frozenset({"XAUUSD"}),
    "XPTUSD": frozenset({"XAUUSD", "XPDUSD"}),
    "XPDUSD": frozenset({"XPTUSD"}),
    # Crypto cluster
    "BTCUSD": frozenset({"ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD"}),
    "ETHUSD": frozenset({"BTCUSD", "LTCUSD", "XRPUSD", "SOLUSD"}),
    "LTCUSD": frozenset({"BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD"}),
    "XRPUSD": frozenset({"BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD"}),
    "SOLUSD": frozenset({"BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"}),
    # Oil
    "USOIL":  frozenset({"UKOIL"}),
    "UKOIL":  frozenset({"USOIL"}),
}


class RiskAgent:
    """Central risk gate.  Every signal must pass ``validate()``."""

    def __init__(
        self,
        broker: BrokerConnector,
        get_open_trades: Callable[[], list[Trade]],
        crucix_agent: "CrucixAgent | None" = None,
        db: "Database | None" = None,
    ) -> None:
        self._broker = broker
        self._get_open_trades = get_open_trades
        self._crucix = crucix_agent
        self._db = db

        # Drawdown tracking
        self._day_start_equity: float = 0.0
        self._day_date: str = ""
        self._circuit_breaker_active = False
        self._circuit_breaker_until: datetime | None = None

        # Short-lived caches to avoid redundant broker IPC calls inside the
        # hot path (risk validation is called once per ranked signal per loop).
        # TTL = 10s — stale enough to survive a multi-signal loop, fresh enough
        # to catch real equity changes between loops.
        self._equity_cache: tuple[float, float] = (0.0, 0.0)  # (monotonic_ts, value)
        self._tick_cache: dict[str, tuple[float, dict]] = {}  # symbol → (monotonic_ts, tick)
        self._spread_reject_counts: dict[str, int] = {}
        self._spread_reject_until: dict[str, datetime] = {}
        self._emergency_max_risk_per_trade: float | None = None
        self._emergency_max_open_trades: int | None = None
        self._symbol_lock_until: dict[str, datetime] = {}
        self._global_lock_until: datetime | None = None
        self._closed_trades_cache: tuple[float, list[Trade]] = (0.0, [])
        # Tick spec cache (tick_size, tick_value) — refreshed every 60s.
        # tick_value is in account currency (MT5 converts automatically), so
        # this is the source of truth for EUR/USD and other cross-currency accounts.
        self._tick_spec_cache: dict[str, tuple[float, float, float]] = {}  # symbol → (ts, size, value)
        self._last_reject_reason: str = ""
        self._last_reject_hard: bool = True
        self._last_reject_message: str = ""
        # Monthly loss gate cache (60 s TTL — same batch = same answer)
        self._daily_cache_ts: float = 0.0
        self._daily_loss_blocked: bool = False
        self._monthly_cache_ts: float = 0.0
        self._monthly_loss_blocked: bool = False
        # Exposure Coach singleton — lazily constructed on first _exposure access.
        self._exposure_instance: "ExposureCoach | None" = None

    # ── lazy singletons ──────────────────────────────────────────────────

    @property
    def _exposure(self) -> "ExposureCoach":
        if self._exposure_instance is None:
            from agents.exposure_agent import ExposureCoach
            self._exposure_instance = ExposureCoach(
                db=self._db, crucix_agent=self._crucix
            )
        return self._exposure_instance

    # ── public API ───────────────────────────────────────────────────────

    def validate(self, signal: Signal, mode: str = "full",
                 post_entry: bool = False) -> bool:
        """Return True if risk checks pass for the selected mode.

        Modes:
        - ``hard``: ultra-fast safety checks for fast-lane / instant-entry
        - ``full``: complete validation (default)

        ``post_entry=True``: skips the duplicate and correlation guards.
        Use this for the post-entry full check so the trade we JUST opened
        doesn't trigger "DUPLICATE" and get immediately closed.
        """
        try:
            if not self._check_signal_geometry(signal):
                return False
            if mode == "hard":
                with mesh_span("risk"):
                    return self._validate_hard(signal)
            with mesh_span("risk"):
                return self._validate_inner(signal, skip_duplicate=post_entry)
        except Exception:
            logger.exception("RiskAgent.validate crashed — rejecting signal")
            return False

    def calculate_position_size(self, signal: Signal) -> float:
        """Return lot size based on risk parameters.

        Uses MT5's trade_tick_value (account currency per tick per lot) so the
        formula is correct regardless of account denomination.  For a EUR account
        trading BTCUSD, balance is in EUR and tick_value is also in EUR — no
        manual EUR/USD conversion needed.

        Formula: lot_size = risk_amount / risk_per_lot
          risk_amount  = balance × MAX_RISK_PER_TRADE            (account currency)
          risk_per_lot = (sl_distance / tick_size) × tick_value  (account currency)

        Falls back to sl_distance × contract_size if tick data is unavailable
        (mock connector, symbol not in MT5).
        """
        balance = self._broker.get_balance()
        equity = self._broker.get_equity()
        max_risk_per_trade = (
            self._emergency_max_risk_per_trade
            if self._emergency_max_risk_per_trade is not None
            else settings.MAX_RISK_PER_TRADE
        )
        mode = settings.POSITION_SIZE_MODE
        if mode == "fixed_lot":
            return max(
                settings.MIN_LOT_SIZE,
                min(settings.MAX_LOT_SIZE, round(settings.POSITION_SIZE_FIXED_LOT, 2)),
            )

        if mode == "fixed_risk_amount":
            risk_amount = max(0.0, settings.POSITION_SIZE_FIXED_RISK_AMOUNT)
        elif mode == "balance_pct":
            risk_amount = balance * max_risk_per_trade
        elif mode == "kelly":
            # Kelly Criterion: size based on historical edge (win-rate / payoff ratio).
            # Falls back to equity_pct when trade history is insufficient.
            risk_amount = equity * self._compute_kelly_fraction()
        else:
            # Default and fallback: equity-based risk percentage.
            risk_amount = equity * max_risk_per_trade

        sl_distance = abs(signal.entry_price - signal.stop_loss)
        if sl_distance == 0:
            return settings.MIN_LOT_SIZE

        # Tick spec — cached 60s to avoid an extra IPC call per signal.
        _now_mono = time.monotonic()
        _spec = self._tick_spec_cache.get(signal.symbol)
        if _spec is None or _now_mono - _spec[0] > 60.0:
            _tick_sz  = self._broker.get_tick_size(signal.symbol)
            _tick_val = self._broker.get_tick_value(signal.symbol)
            self._tick_spec_cache[signal.symbol] = (_now_mono, _tick_sz, _tick_val)
        else:
            _, _tick_sz, _tick_val = _spec

        if _tick_sz > 0 and _tick_val > 0:
            # MT5-accurate: account currency on both sides — no FX mismatch.
            risk_per_lot = (sl_distance / _tick_sz) * _tick_val
        else:
            # Fallback: original formula (mock connector / missing symbol info).
            cs = self._broker.get_contract_size(signal.symbol)
            risk_per_lot = sl_distance * cs

        if risk_per_lot == 0:
            return settings.MIN_LOT_SIZE
        lot_size = risk_amount / risk_per_lot
        raw_lot = round(lot_size, 2)
        lot_size = max(settings.MIN_LOT_SIZE, min(settings.MAX_LOT_SIZE, raw_lot))
        if raw_lot > settings.MAX_LOT_SIZE:
            logger.warning(
                "LOT CAP applied for %s: calculated %.2f → capped at %.2f (SL distance=%.5f)",
                signal.symbol, raw_lot, lot_size, sl_distance,
            )

        # Apply confidence scaling bands (borderline setups are sized down,
        # not blindly rejected).
        conf = signal.confidence
        if conf < settings.SIZE_SCALE_VERY_LOW_THRESHOLD:
            scale = settings.SIZE_SCALE_VERY_LOW
        elif conf < settings.SIZE_SCALE_LOW_THRESHOLD:
            scale = settings.SIZE_SCALE_LOW
        elif conf < settings.SIZE_SCALE_MEDIUM_THRESHOLD:
            scale = settings.SIZE_SCALE_MEDIUM
        else:
            scale = settings.SIZE_SCALE_FULL
        lot_size = round(lot_size * scale, 2)

        # Macro risk scaling from Crucix
        if self._crucix:
            try:
                macro = self._crucix.get_context()
                scale = macro.lot_scale_factor
                if scale != 1.0:
                    lot_size = round(lot_size * scale, 2)
                    logger.info(
                        "MACRO LOT SCALE applied: tier=%s scale=%.2f → lot=%.2f",
                        macro.risk_tier, scale, lot_size,
                    )
            except Exception:
                pass  # Crucix unavailable — use unscaled lot

        return max(settings.MIN_LOT_SIZE, min(settings.MAX_LOT_SIZE, lot_size))

    def _compute_kelly_fraction(self) -> float:
        """Return the Kelly-optimal risk fraction for the current strategy edge.

        Uses closed trades from the last KELLY_LOOKBACK_DAYS days (default 90).
        Applies half-Kelly by default (KELLY_HALF=true) to reduce variance.
        Falls back to ``settings.MAX_RISK_PER_TRADE`` when fewer than
        ``settings.KELLY_MIN_TRADES`` trades are available.

        Formula (full-Kelly):
            f* = (W × R - (1 - W)) / R
        where:
            W = win-rate (fraction of profitable closes)
            R = avg_win_pnl / avg_loss_pnl  (reward-to-risk ratio)

        Reference: BackTrader KellyCriterion Sizer, Thorp (1962)
        """
        from datetime import UTC, timedelta
        since = datetime.now(UTC) - timedelta(days=settings.KELLY_LOOKBACK_DAYS)
        trades = self._db.get_closed_trades_since(since, limit=500)

        if len(trades) < settings.KELLY_MIN_TRADES:
            logger.debug(
                "Kelly fallback: only %d trades (need %d) — using equity_pct",
                len(trades), settings.KELLY_MIN_TRADES,
            )
            return settings.MAX_RISK_PER_TRADE

        wins  = [t.pnl for t in trades if t.pnl and t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl and t.pnl <= 0]

        if not wins or not losses:
            # Edge-case: all wins or all losses — defer to equity_pct
            return settings.MAX_RISK_PER_TRADE

        W = len(wins) / len(trades)
        avg_win  = sum(wins)  / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        R = avg_win / avg_loss if avg_loss > 0 else 1.0

        f_star = (W * R - (1.0 - W)) / R

        if settings.KELLY_HALF:
            f_star *= 0.5  # Half-Kelly reduces variance without sacrificing much growth

        # Cap at MAX_RISK_PER_TRADE so Kelly can never exceed the configured risk limit.
        kelly = max(0.0, min(f_star, settings.MAX_RISK_PER_TRADE))
        logger.info(
            "Kelly fraction: W=%.1f%% R=%.2f f*=%.4f %s=%.4f",
            W * 100, R, f_star,
            "half-kelly" if settings.KELLY_HALF else "full-kelly",
            kelly,
        )
        return kelly

    def set_emergency_caps(self, *, max_risk_per_trade: float, max_open_trades: int) -> None:
        self._emergency_max_risk_per_trade = max(0.0001, float(max_risk_per_trade))
        self._emergency_max_open_trades = max(1, int(max_open_trades))

    def clear_emergency_caps(self) -> None:
        self._emergency_max_risk_per_trade = None
        self._emergency_max_open_trades = None

    def get_emergency_caps(self) -> dict[str, float | int | None]:
        return {
            "max_risk_per_trade": self._emergency_max_risk_per_trade,
            "max_open_trades": self._emergency_max_open_trades,
        }

    # ── internal checks (ordered fail-fast) ──────────────────────────────

    def _validate_hard(self, signal: Signal) -> bool:
        """Fast-lane safety checks only.

        Includes only the non-negotiable risk controls needed for rapid entry.
        """
        # 1. Drawdown circuit breaker
        if self._check_drawdown():
            self._emit("warn", "Drawdown breaker is ON — no trades allowed!", {"check": "drawdown"})
            return False

        # 1b. Crucix macro blackout check
        if self._crucix and self._crucix.is_blackout(signal.symbol):
            self._emit("warn", f"MACRO BLACKOUT: FLASH alert active on {signal.symbol}",
                       {"symbol": signal.symbol, "check": "crucix_blackout"})
            return False

        # 1c. Protection layer (cooldown, stoploss guard, global loss guard).
        if not self._check_protections(signal):
            return False

        agile_high_conf = self._is_agile_high_conf(signal)

        # 1d. Session gate — only enter in allowed sessions (data-driven)
        if settings.ENTRY_ALLOWED_SESSIONS and not agile_high_conf:
            sess = current_session()
            if sess not in settings.ENTRY_ALLOWED_SESSIONS:
                self._emit("warn",
                           f"SESSION GATE: {signal.symbol} blocked — session={sess} "
                           f"not in {settings.ENTRY_ALLOWED_SESSIONS}",
                           {"symbol": signal.symbol, "session": sess,
                            "allowed": settings.ENTRY_ALLOWED_SESSIONS})
                return False

        # 1e. Day-of-week gate — block systematic losing days
        if settings.ENTRY_BLOCKED_DAYS and not agile_high_conf:
            today = day_of_week()
            weekend_crypto = (
                asset_class(signal.symbol) == "crypto" and is_weekend()
            )
            if today in settings.ENTRY_BLOCKED_DAYS and not weekend_crypto:
                self._emit("warn",
                           f"DAY GATE: {signal.symbol} blocked — {today} in blocked days",
                           {"symbol": signal.symbol, "day": today,
                            "blocked": settings.ENTRY_BLOCKED_DAYS})
                return False

        # 1f. Time-phase confidence gate (optional).
        if not self._check_time_phase_confidence(signal):
            return False

        open_trades = self._get_open_trades()

        # 2. Duplicate and correlation exposure guards
        if self._check_duplicate(signal, open_trades):
            self._emit("warn", f"DUPLICATE — {signal.symbol} {signal.direction} already open")
            return False
        if self._check_correlation(signal, open_trades) and not agile_high_conf:
            self._emit("warn", f"CORRELATION — {signal.symbol} {signal.direction} blocked")
            return False

        # 3. Max concurrent trades
        if not self._check_open_trade_cap(open_trades):
            self._emit("warn", "MAX_TRADES — concurrent position cap reached", {"check": "max_trades"})
            return False

        # 4. Spread check (fast path)
        if not self._check_spread(signal):
            return False

        return True

    def _validate_inner(self, signal: Signal, skip_duplicate: bool = False) -> bool:
        # 1. Drawdown circuit breaker
        if self._check_drawdown():
            logger.warning("RISK REJECT [DRAWDOWN]: circuit breaker active")
            self._emit("warn", "Drawdown breaker is ON — no trades allowed!", {"check": "drawdown"})
            return False

        # 1a. Daily realised-PnL gate — blocks rest-of-day when closed-trade loss ≥ MAX_DAILY_LOSS.
        # Complements the equity-based drawdown circuit breaker (check 1 above) with a
        # realised-only view so partial-close profits don't mask locked-in losses.
        if self._check_daily_loss():
            self._emit(
                "warn",
                f"DAILY LOSS GATE: today's realised PnL loss ≥ {settings.MAX_DAILY_LOSS:.0%}"
                " — no new trades today",
                {"check": "daily_loss"},
            )
            return False

        # 1b. Monthly realised-PnL gate (MT5_Trade_Connector RiskManagement_v1 pattern)
        if self._check_monthly_loss():
            self._emit(
                "warn",
                f"MONTHLY LOSS GATE: MTD loss exceeds {settings.MAX_MONTHLY_LOSS:.0%} — trading halted",
                {"check": "monthly_loss"},
            )
            return False

        # 1b. Crucix macro blackout check
        if self._crucix and self._crucix.is_blackout(signal.symbol):
            self._emit("warn",
                       f"MACRO BLACKOUT: FLASH alert active on {signal.symbol}",
                       {"symbol": signal.symbol, "check": "crucix_blackout"})
            return False

        # 1c. Protection layer — skip on post-entry checks.
        if not skip_duplicate and not self._check_protections(signal):
            return False

        agile_high_conf = self._is_agile_high_conf(signal)

        # 1d. Session gate — only allow new entries in proven sessions.
        # skip_duplicate=True means this is a post-entry check; don't close
        # a trade simply because the session changed after entry.
        if not skip_duplicate and settings.ENTRY_ALLOWED_SESSIONS and not agile_high_conf:
            sess = signal.entry_snapshot.session or current_session()
            if sess not in settings.ENTRY_ALLOWED_SESSIONS:
                logger.warning(
                    "RISK REJECT [SESSION]: %s blocked — session=%s not in %s",
                    signal.symbol, sess, settings.ENTRY_ALLOWED_SESSIONS,
                )
                self._emit("warn",
                           f"SESSION GATE: {signal.symbol} blocked — "
                           f"session={sess} not in {settings.ENTRY_ALLOWED_SESSIONS}",
                           {"symbol": signal.symbol, "session": sess,
                            "check": "session_gate"})
                return False

        # 1e. Day-of-week gate — skip on post-entry checks for same reason.
        if not skip_duplicate and settings.ENTRY_BLOCKED_DAYS and not agile_high_conf:
            today = signal.entry_snapshot.day_of_week or day_of_week()
            weekend_crypto = (
                asset_class(signal.symbol) == "crypto" and is_weekend()
            )
            if today in settings.ENTRY_BLOCKED_DAYS and not weekend_crypto:
                logger.warning(
                    "RISK REJECT [DAY_GATE]: %s blocked — %s in blocked days",
                    signal.symbol, today,
                )
                self._emit("warn",
                           f"DAY GATE: {signal.symbol} blocked — {today} in blocked days",
                           {"symbol": signal.symbol, "day": today,
                            "check": "day_gate"})
                return False

        # 1f. Time-phase confidence gate — skip on post-entry checks.
        if not skip_duplicate and not self._check_time_phase_confidence(signal):
            return False

        open_trades = self._get_open_trades()

        # 1g. Exposure Coach — synthesises 8 environment signals into a
        # single directive.  Skipped on post-entry checks (the exposure
        # evaluation already ran before the trade was opened).
        if settings.EXPOSURE_ENABLED and not skip_duplicate:
            _exp = self._exposure.evaluate(
                signal,
                open_trades=open_trades,
                account_equity=self._broker.get_equity(),
            )
            if not _exp.skipped and _exp.directive != "NEW_ENTRY_ALLOWED":
                logger.warning(
                    "RISK REJECT [EXPOSURE]: %s — %s",
                    _exp.directive, _exp.reason,
                )
                self._emit(
                    "warn",
                    f"EXPOSURE COACH: {_exp.directive} — {_exp.reason}",
                    {
                        "check": "exposure",
                        "directive": _exp.directive,
                        "ceiling": _exp.exposure_ceiling_pct,
                    },
                )
                return False

        # 2. Duplicate signal guard — skipped on post-entry validation because
        # the trade we just opened would always trigger this as a false positive.
        if not skip_duplicate and self._check_duplicate(signal, open_trades):
            logger.warning(
                "RISK REJECT [DUPLICATE]: %s %s %s already open",
                signal.symbol, signal.direction, signal.strategy,
            )
            self._emit("warn",
                       f"DUPLICATE — {signal.symbol} {signal.direction} already open",
                       {"symbol": signal.symbol, "check": "duplicate"})
            return False

        # 3. Correlation guard (same symbol or correlated pair, same direction)
        if not skip_duplicate and self._check_correlation(signal, open_trades) and not agile_high_conf:
            logger.warning(
                "RISK REJECT [CORRELATION]: %s %s blocked by existing exposure",
                signal.symbol, signal.direction,
            )
            self._emit("warn",
                       f"CORRELATION — {signal.symbol} {signal.direction} blocked by correlated open position",
                       {"symbol": signal.symbol, "check": "correlation"})
            return False

        # 4. Maximum concurrent open trades
        if not self._check_open_trade_cap(open_trades):
            logger.warning(
                "RISK REJECT [MAX_TRADES]: %d open >= limit %d",
                len(open_trades), self._emergency_max_open_trades or settings.MAX_OPEN_TRADES,
            )
            self._emit(
                "warn",
                (
                    f"MAX_TRADES — {len(open_trades)} open trades >= limit "
                    f"{self._emergency_max_open_trades or settings.MAX_OPEN_TRADES}"
                ),
                {"check": "max_trades",
                 "count": len(open_trades),
                 "limit": self._emergency_max_open_trades or settings.MAX_OPEN_TRADES},
            )
            return False

        # 5. Live spread check (per-asset-class limits)
        if not self._check_spread(signal):
            return False

        # 7. Position size sanity
        lot_size = self.calculate_position_size(signal)
        if lot_size < settings.MIN_LOT_SIZE:
            logger.warning("RISK REJECT [LOT_SIZE]: calculated %.2f < min %.2f",
                           lot_size, settings.MIN_LOT_SIZE)
            self._emit("warn",
                       f"LOT_SIZE — {signal.symbol} calculated {lot_size:.3f} < min {settings.MIN_LOT_SIZE}",
                       {"symbol": signal.symbol, "check": "lot_size",
                        "lot_size": lot_size, "min": settings.MIN_LOT_SIZE})
            return False

        logger.info("RISK APPROVED: %s %s %s (lot=%.2f)",
                     signal.symbol, signal.direction, signal.strategy, lot_size)
        self._emit("info",
                   f"All clear — {signal.direction} {signal.symbol} approved (lot={lot_size:.2f})",
                   {"symbol": signal.symbol, "direction": signal.direction,
                    "lot_size": lot_size})
        return True

    def _check_signal_geometry(self, signal: Signal) -> bool:
        """Validate direction/SL/TP geometry before any risk or execution checks."""
        direction = signal.direction.upper().strip()
        entry = signal.entry_price
        sl = signal.stop_loss
        tp1 = signal.take_profit_1
        tp2 = signal.take_profit_2
        tp3 = signal.take_profit_3
        tp4 = signal.take_profit_4

        numeric = {
            "entry": entry,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "take_profit_4": tp4,
        }

        if direction not in {"BUY", "SELL"}:
            self._emit(
                "warn",
                f"GEOMETRY INVALID: {signal.symbol} direction={signal.direction!r}",
                {"symbol": signal.symbol, "check": "signal_geometry"},
            )
            return False

        for name, value in numeric.items():
            if value <= 0:
                continue
            if not math.isfinite(value):
                self._emit(
                    "warn",
                    f"GEOMETRY INVALID: {signal.symbol} {name} not finite ({value})",
                    {
                        "symbol": signal.symbol,
                        "check": "signal_geometry",
                        "field": name,
                        "value": value,
                    },
                )
                return False

        if entry <= 0 or sl <= 0 or tp1 <= 0:
            self._emit(
                "warn",
                (
                    f"GEOMETRY INVALID: {signal.symbol} missing core levels "
                    f"(entry={entry}, sl={sl}, tp1={tp1})"
                ),
                {
                    "symbol": signal.symbol,
                    "check": "signal_geometry",
                    "entry": entry,
                    "sl": sl,
                    "tp1": tp1,
                },
            )
            return False

        if direction == "BUY":
            if sl >= entry or tp1 <= entry:
                self._emit(
                    "warn",
                    (
                        f"GEOMETRY INVALID: BUY {signal.symbol} requires sl < entry < tp1 "
                        f"(entry={entry}, sl={sl}, tp1={tp1})"
                    ),
                    {"symbol": signal.symbol, "check": "signal_geometry"},
                )
                return False
            if tp2 > 0 and tp2 < tp1:
                return False
            if tp3 > 0 and tp2 > 0 and tp3 < tp2:
                return False
            if tp4 > 0 and tp3 > 0 and tp4 < tp3:
                return False
        else:
            if sl <= entry or tp1 >= entry:
                self._emit(
                    "warn",
                    (
                        f"GEOMETRY INVALID: SELL {signal.symbol} requires sl > entry > tp1 "
                        f"(entry={entry}, sl={sl}, tp1={tp1})"
                    ),
                    {"symbol": signal.symbol, "check": "signal_geometry"},
                )
                return False
            if tp2 > 0 and tp2 > tp1:
                return False
            if tp3 > 0 and tp2 > 0 and tp3 > tp2:
                return False
            if tp4 > 0 and tp3 > 0 and tp4 > tp3:
                return False

        return True

    def _check_spread(self, signal: Signal) -> bool:
        """Return True if spread is within limits for the signal's asset class."""
        now_utc = datetime.now(UTC)
        spread_block_until = self._spread_reject_until.get(signal.symbol)
        if spread_block_until and now_utc < spread_block_until:
            return False

        live_spread = signal.entry_snapshot.spread
        # Reuse tick fetched by MarketAgent earlier in the same loop iteration
        # if it is still fresh (< 10s old), avoiding a redundant MT5 IPC call.
        _now_mono = time.monotonic()
        _tick_ts, _cached_tick = self._tick_cache.get(signal.symbol, (0.0, {}))
        if _now_mono - _tick_ts < 10.0 and _cached_tick:
            if _cached_tick.get("spread", 0) > 0:
                live_spread = _cached_tick["spread"]
        else:
            try:
                tick = self._broker.get_tick(signal.symbol)
                if tick and tick.get("spread", 0) > 0:
                    live_spread = tick["spread"]
                    self._tick_cache[signal.symbol] = (_now_mono, tick)
            except Exception:
                pass

        ac = asset_class(signal.symbol)
        spread_mult = 1.0
        if self._is_agile_high_conf(signal):
            spread_mult = max(1.0, settings.RISK_AGILE_SPREAD_MULTIPLIER)
        if ac == "crypto":
            price = signal.entry_price or 1.0
            spread_pct = (live_spread / price) * 100
            allowed_pct = settings.MAX_SPREAD_PCT_CRYPTO * spread_mult
            if spread_pct > allowed_pct:
                self._register_spread_reject(signal.symbol, now_utc)
                logger.warning(
                    "RISK REJECT [SPREAD]: %.3f%% > max %.2f%% for %s (crypto)",
                    spread_pct, allowed_pct, signal.symbol,
                )
                self._emit(
                    "warn",
                    (
                        f"SPREAD — {signal.symbol} {spread_pct:.2f}% > "
                        f"max {allowed_pct:.2f}%"
                    ),
                    {
                        "symbol": signal.symbol,
                        "check": "spread",
                        "spread_pct": round(spread_pct, 3),
                        "max": allowed_pct,
                    },
                )
                return False
            self._clear_spread_reject(signal.symbol)
            return True

        pv = pip_value(signal.symbol)
        spread_pips = live_spread / pv
        if ac == "commodity":
            max_spread = settings.MAX_SPREAD_PIPS_COMMODITY
        elif ac == "index":
            max_spread = settings.MAX_SPREAD_POINTS_INDEX
        elif ac == "exotic":
            max_spread = settings.MAX_SPREAD_PIPS_EXOTIC
        else:
            max_spread = settings.MAX_SPREAD_PIPS

        allowed_spread = max_spread * spread_mult
        if spread_pips > allowed_spread:
            self._register_spread_reject(signal.symbol, now_utc)
            logger.warning(
                "RISK REJECT [SPREAD]: %.1f pips > max %.1f for %s (%s)",
                spread_pips, allowed_spread, signal.symbol, ac,
            )
            self._emit(
                "warn",
                (
                    f"SPREAD — {signal.symbol} {spread_pips:.1f} pips > "
                    f"max {allowed_spread:.1f} ({ac})"
                ),
                {
                    "symbol": signal.symbol,
                    "check": "spread",
                    "spread_pips": round(spread_pips, 1),
                    "max": allowed_spread,
                },
            )
            return False

        self._clear_spread_reject(signal.symbol)
        return True

    def _check_time_phase_confidence(self, signal: Signal) -> bool:
        """Gate entries by candle-time phase when enabled.

        Phase is derived from the signal timestamp modulo TIME_PHASE_BUCKET_MINUTES.
        """
        if not settings.TIME_PHASE_CONFIDENCE_ENABLED:
            return True
        if self._is_agile_high_conf(signal):
            return True

        bucket = max(1, settings.TIME_PHASE_BUCKET_MINUTES)
        minute_in_bucket = signal.timestamp.minute % bucket
        early_max = settings.TIME_PHASE_EARLY_MAX_MINUTE
        mid_max = settings.TIME_PHASE_MID_MAX_MINUTE

        if minute_in_bucket < early_max:
            phase = "early"
            required = settings.TIME_PHASE_MIN_CONF_EARLY
        elif minute_in_bucket < mid_max:
            phase = "mid"
            required = settings.TIME_PHASE_MIN_CONF_MID
        else:
            phase = "late"
            required = settings.TIME_PHASE_MIN_CONF_LATE

        if signal.confidence < required:
            logger.warning(
                "RISK REJECT [TIME_PHASE]: %s confidence %.2f < %.2f (%s phase, m=%d/%d)",
                signal.symbol,
                signal.confidence,
                required,
                phase,
                minute_in_bucket,
                bucket,
            )
            self._emit(
                "warn",
                (
                    f"TIME_PHASE — {signal.symbol} confidence {signal.confidence:.2f} < "
                    f"required {required:.2f} ({phase})"
                ),
                {
                    "symbol": signal.symbol,
                    "check": "time_phase_confidence",
                    "phase": phase,
                    "confidence": signal.confidence,
                    "required": required,
                    "minute_in_bucket": minute_in_bucket,
                    "bucket_minutes": bucket,
                },
            )
            return False

        return True

    def _check_protections(self, signal: Signal) -> bool:
        """Freqtrade-style entry protections.

        Applies global lock, per-symbol lock, per-symbol cooldown, and
        stoploss/loss cluster guards based on recent closed trades.
        """
        if not settings.PROTECTIONS_ENABLED:
            return True

        agile_high_conf = self._is_agile_high_conf(signal)

        now = datetime.now(UTC)

        if self._global_lock_until and now < self._global_lock_until:
            self._emit(
                "warn",
                f"PROTECTION — global lock active until {self._global_lock_until.isoformat()}",
                {
                    "symbol": signal.symbol,
                    "check": "protection_global_lock",
                    "lock_until": self._global_lock_until.isoformat(),
                },
            )
            return False

        symbol_lock = self._symbol_lock_until.get(signal.symbol)
        if symbol_lock and now < symbol_lock:
            self._emit(
                "warn",
                f"PROTECTION — {signal.symbol} locked until {symbol_lock.isoformat()}",
                {
                    "symbol": signal.symbol,
                    "check": "protection_symbol_lock",
                    "lock_until": symbol_lock.isoformat(),
                },
            )
            return False

        lookback_minutes = max(
            settings.PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES,
            settings.PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES,
            settings.PROTECTION_COOLDOWN_MINUTES,
        )
        recent = self._get_closed_trades_recent(lookback_minutes)
        if not recent:
            return True

        symbol_recent = [t for t in recent if t.symbol == signal.symbol]

        cooldown = 0 if agile_high_conf else max(0, settings.PROTECTION_COOLDOWN_MINUTES)
        if cooldown > 0 and symbol_recent:
            last_close = max(
                self._ensure_utc_trade_time(t.close_time)
                for t in symbol_recent
                if t.close_time is not None
            )
            if (now - last_close).total_seconds() < cooldown * 60:
                lock_until = last_close + timedelta(minutes=cooldown)
                self._symbol_lock_until[signal.symbol] = lock_until
                self._emit(
                    "warn",
                    (
                        f"PROTECTION — cooldown: {signal.symbol} last close at "
                        f"{last_close.isoformat()} (lock until {lock_until.isoformat()})"
                    ),
                    {
                        "symbol": signal.symbol,
                        "check": "protection_cooldown",
                        "lock_until": lock_until.isoformat(),
                    },
                )
                return False

        stoploss_lookback = max(1, settings.PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES)
        stoploss_limit = max(1, settings.PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT)
        stoploss_recent = [
            t for t in symbol_recent
            if t.close_time is not None
            and (now - self._ensure_utc_trade_time(t.close_time)).total_seconds() <= stoploss_lookback * 60
            and t.close_reason == "SL"
        ]
        if len(stoploss_recent) >= stoploss_limit and not agile_high_conf:
            lock_minutes = max(1, settings.PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES)
            latest_sl = max(self._ensure_utc_trade_time(t.close_time) for t in stoploss_recent)
            lock_until = latest_sl + timedelta(minutes=lock_minutes)
            self._symbol_lock_until[signal.symbol] = lock_until
            self._emit(
                "warn",
                (
                    f"PROTECTION — stoploss guard: {signal.symbol} has "
                    f"{len(stoploss_recent)} SL closes in {stoploss_lookback}m"
                ),
                {
                    "symbol": signal.symbol,
                    "check": "protection_stoploss_guard",
                    "sl_count": len(stoploss_recent),
                    "lock_until": lock_until.isoformat(),
                },
            )
            return False

        global_lookback = max(1, settings.PROTECTION_GLOBAL_LOSS_GUARD_LOOKBACK_MINUTES)
        global_loss_limit = max(1, settings.PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES)
        losing_recent = [
            t for t in recent
            if t.close_time is not None
            and (now - self._ensure_utc_trade_time(t.close_time)).total_seconds() <= global_lookback * 60
            and t.pnl < 0
        ]
        if len(losing_recent) >= global_loss_limit:
            lock_minutes = max(1, settings.PROTECTION_GLOBAL_LOSS_GUARD_LOCK_MINUTES)
            latest_loss = max(self._ensure_utc_trade_time(t.close_time) for t in losing_recent)
            self._global_lock_until = latest_loss + timedelta(minutes=lock_minutes)
            self._emit(
                "warn",
                (
                    f"PROTECTION — global loss guard: {len(losing_recent)} losing closes "
                    f"in {global_lookback}m"
                ),
                {
                    "symbol": signal.symbol,
                    "check": "protection_global_loss_guard",
                    "loss_count": len(losing_recent),
                    "lock_until": self._global_lock_until.isoformat(),
                },
            )
            return False

        return True

    @staticmethod
    def _is_agile_profile() -> bool:
        return settings.RISK_VALIDATION_PROFILE == "agile"

    def _is_agile_high_conf(self, signal: Signal) -> bool:
        if not self._is_agile_profile():
            return False
        return signal.confidence >= settings.RISK_AGILE_HIGH_CONF_THRESHOLD

    def _get_closed_trades_recent(self, lookback_minutes: int) -> list[Trade]:
        """Load recent closed trades from DB with a short TTL cache."""
        if self._db is None or not hasattr(self._db, "get_closed_trades_since"):
            return []

        now_mono = time.monotonic()
        cache_ts, cached_trades = self._closed_trades_cache
        if now_mono - cache_ts < 5.0:
            return cached_trades

        since = datetime.now(UTC) - timedelta(minutes=max(1, int(lookback_minutes)))
        try:
            trades = self._db.get_closed_trades_since(since, limit=1000)
        except Exception:
            logger.exception("Failed to load closed trades for protection checks")
            trades = []

        self._closed_trades_cache = (now_mono, trades)
        return trades

    @staticmethod
    def _ensure_utc_trade_time(dt: datetime | None) -> datetime:
        if dt is None:
            return datetime.min.replace(tzinfo=UTC)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def _register_spread_reject(self, symbol: str, now_utc: datetime) -> None:
        count = self._spread_reject_counts.get(symbol, 0) + 1
        self._spread_reject_counts[symbol] = count
        if count >= settings.SPREAD_REJECT_COOLDOWN_HITS:
            self._spread_reject_until[symbol] = now_utc + timedelta(
                seconds=settings.SPREAD_REJECT_COOLDOWN_SECONDS
            )
            self._spread_reject_counts[symbol] = 0

    def _clear_spread_reject(self, symbol: str) -> None:
        self._spread_reject_counts[symbol] = 0
        self._spread_reject_until.pop(symbol, None)

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if level == "warn":
            check = "unknown"
            if isinstance(data, dict):
                check = str(data.get("check", "unknown"))
            self._last_reject_reason = check
            self._last_reject_hard = self._is_hard_reject(check)
            self._last_reject_message = msg
        if self._db:
            self._db.log_agent_event("risk", level, msg, data)

    @staticmethod
    def _is_hard_reject(reason: str) -> bool:
        # Hard rejects should never be bypassed/deferred by orchestration.
        return reason in {
            "drawdown",
            "crucix_blackout",
            "max_trades",
            "lot_size",
        }

    def get_last_reject_info(self) -> dict[str, str | bool]:
        return {
            "reason": self._last_reject_reason,
            "hard": self._last_reject_hard,
            "message": self._last_reject_message,
        }

    # ── drawdown circuit breaker ─────────────────────────────────────────

    def _check_drawdown(self) -> bool:
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")

        # If breaker fired, check if cooldown has elapsed
        if self._circuit_breaker_active:
            if self._circuit_breaker_until and now < self._circuit_breaker_until:
                return True
            self._circuit_breaker_active = False
            self._circuit_breaker_until = None
            logger.info("Drawdown circuit breaker cooldown expired — trading resumed")

        # Reset day tracking at midnight UTC
        if today != self._day_date:
            self._day_date = today
            self._day_start_equity = self._broker.get_equity()
            logger.info("Drawdown tracker reset: start_equity=%.2f", self._day_start_equity)

        if self._day_start_equity <= 0:
            return False

        # Use cached equity to avoid a redundant MT5 IPC call for every signal
        # in the ranked list.  10s TTL is safe — drawdown changes slowly.
        _now_mono = time.monotonic()
        _cache_ts, _cached_eq = self._equity_cache
        if _now_mono - _cache_ts < 10.0 and _cached_eq > 0:
            current_equity = _cached_eq
        else:
            current_equity = self._broker.get_equity()
            self._equity_cache = (_now_mono, current_equity)

        drawdown = (self._day_start_equity - current_equity) / self._day_start_equity

        if drawdown >= settings.MAX_DAILY_LOSS:
            self._circuit_breaker_active = True
            self._circuit_breaker_until = now + timedelta(hours=settings.DRAWDOWN_COOLDOWN_HOURS)
            msg = (
                f"🚨 DRAWDOWN CIRCUIT BREAKER: lost {drawdown:.1%} today "
                f"(limit {settings.MAX_DAILY_LOSS:.1%}). "
                f"Trading halted until {self._circuit_breaker_until.isoformat()}"
            )
            logger.critical(msg)
            telegram_bot.send_message(msg)
            return True

        return False

    # ── daily / monthly loss gates ──────────────────────────────────────
    # Pattern: MT5_Trade_Connector RiskManagement_v1 (daily 5% / monthly 10%)

    def _check_daily_loss(self) -> bool:
        """Return True (block trading) if today's realised PnL loss >= MAX_DAILY_LOSS.

        Complements ``_check_drawdown()`` (equity-based) with a realised-only
        view: open floating profits cannot mask locked-in losses.
        Cached for 60 s to avoid a DB round-trip on every signal in a batch.
        """
        if self._db is None:
            return False

        now_mono = time.monotonic()
        if now_mono - self._daily_cache_ts < 60.0:
            return self._daily_loss_blocked

        now_utc = datetime.now(UTC)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            trades = self._db.get_closed_trades_since(today_start, limit=500)
        except Exception:
            logger.exception("_check_daily_loss: DB query failed — skipping gate (non-fatal)")
            self._daily_cache_ts = now_mono
            self._daily_loss_blocked = False
            return False

        daily_pnl = sum(t.pnl for t in trades if t.pnl is not None)

        equity = self._broker.get_equity()
        if equity <= 0:
            self._daily_cache_ts = now_mono
            self._daily_loss_blocked = False
            return False

        daily_loss_pct = -daily_pnl / equity  # positive when losing
        self._daily_cache_ts = now_mono
        self._daily_loss_blocked = daily_loss_pct >= settings.MAX_DAILY_LOSS

        if self._daily_loss_blocked:
            logger.critical(
                "DAILY LOSS GATE: today's PnL=%.2f (%.1f%%) exceeds limit %.1f%%",
                daily_pnl, daily_loss_pct * 100, settings.MAX_DAILY_LOSS * 100,
            )
        return self._daily_loss_blocked

    def _check_monthly_loss(self) -> bool:
        """Return True (block trading) if month-to-date PnL loss exceeds MAX_MONTHLY_LOSS.

        Computes MTD loss from closed trades in the DB.  Cached for 60 s to
        avoid hammering the database on every signal in a ranked batch.
        """
        if self._db is None:
            return False
        now_mono = time.monotonic()
        if now_mono - self._monthly_cache_ts < 60.0:
            return self._monthly_loss_blocked

        # Refresh MTD closed-trade PnL
        now_utc = datetime.now(UTC)
        month_start = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        trades = self._db.get_closed_trades_since(month_start, limit=2000)
        mtd_pnl = sum(t.pnl for t in trades if t.pnl is not None)

        # We need equity at month-start to express loss as a fraction.
        # Use current equity as a conservative proxy (equity decreases → ratio safe).
        equity = self._broker.get_equity()
        if equity <= 0:
            self._monthly_cache_ts = now_mono
            self._monthly_loss_blocked = False
            return False

        mtd_loss_pct = -mtd_pnl / equity  # positive when losing
        self._monthly_cache_ts = now_mono
        self._monthly_loss_blocked = mtd_loss_pct >= settings.MAX_MONTHLY_LOSS

        if self._monthly_loss_blocked:
            logger.critical(
                "MONTHLY LOSS GATE: MTD PnL=%.2f (%.1f%%) exceeds limit %.1f%%",
                mtd_pnl, mtd_loss_pct * 100, settings.MAX_MONTHLY_LOSS * 100,
            )
        return self._monthly_loss_blocked

    # ── duplicate guard ──────────────────────────────────────────────────

    @staticmethod
    def _check_duplicate(signal: Signal, open_trades: list[Trade]) -> bool:
        for t in open_trades:
            if (t.symbol == signal.symbol
                    and t.direction == signal.direction
                    and t.strategy == signal.strategy
                    and t.is_open()):
                return True
        return False

    def _check_open_trade_cap(self, open_trades: list[Trade]) -> bool:
        max_open_trades = self._emergency_max_open_trades or settings.MAX_OPEN_TRADES
        return len(open_trades) < max_open_trades

    # ── correlation guard ────────────────────────────────────────────────

    @staticmethod
    def _check_correlation(signal: Signal, open_trades: list[Trade]) -> bool:
        """Block if already holding the same symbol+direction from any strategy,
        OR if holding a highly-correlated pair in the same direction."""
        correlated = _CORRELATED_PAIRS.get(signal.symbol, frozenset())
        for t in open_trades:
            if not t.is_open():
                continue
            # Same symbol, any strategy (catches cross-strategy duplicates)
            if t.symbol == signal.symbol and t.direction == signal.direction:
                return True
            # Correlated pair, same direction → overlapping exposure
            if t.symbol in correlated and t.direction == signal.direction:
                logger.debug(
                    "Correlation block: %s %s blocked by open %s %s",
                    signal.direction, signal.symbol, t.direction, t.symbol,
                )
                return True
        return False
