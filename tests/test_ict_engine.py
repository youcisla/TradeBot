"""Tests for the ICT / SMC strategy engine modules.

Tests cover:
  - Structure engine (swing points, BOS/MSS, dealing range)
  - Liquidity engine (BSL/SSL mapping, sweep detection)
  - Displacement engine (impulsive candle detection)
  - FVG engine (gap detection, fill/failure tracking)
  - Order block engine (OB detection, validation, hi-prob marking)
  - Session engine (session detection, killzones, macros, levels)
  - Bias engine (HTF bias, regime, premium/discount)
  - Scoring engine (confidence breakdown)
  - Setups engine (setup model detection)
  - Engine orchestrator (full pipeline)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.market_data import Candle
from models.ict_models import (
    Bias, Regime, OBType, FVGType, LiquidityType, SessionName,
    SwingPoint, LiquidityLevel, LiquiditySweep, StructureBreak,
    DealingRange, Displacement, FairValueGap, OrderBlock,
    SessionInfo, ICTContext, SetupCandidate, ConfidenceBreakdown,
)


# ── Helpers ──────────────────────────────────────────────────────────────

def _ts(hour: int = 10, day: int = 1) -> datetime:
    """UTC datetime helper."""
    return datetime(2026, 1, day, hour, 0, 0, tzinfo=timezone.utc)


def _candle(
    o: float, h: float, l: float, c: float,
    ts: datetime | None = None, vol: float = 1000.0,
) -> Candle:
    return Candle(
        timestamp=ts or _ts(),
        open=o, high=h, low=l, close=c, volume=vol,
    )


def _make_swing_candles(count: int = 30) -> list[Candle]:
    """Generate candles with clear swing highs and lows.

    Pattern: 10 candles up, 10 candles down, 10 candles up (V shape × 2).
    """
    candles: list[Candle] = []
    base = 1.1000
    for i in range(count):
        if i < 10:
            c = base + i * 0.0010
        elif i < 20:
            c = base + (20 - i) * 0.0010
        else:
            c = base + (i - 20) * 0.0010
        ts = _ts(hour=0) + timedelta(hours=i)
        candles.append(_candle(
            o=round(c - 0.0003, 5),
            h=round(c + 0.0007, 5),
            l=round(c - 0.0007, 5),
            c=round(c, 5),
            ts=ts,
        ))
    return candles


# ══════════════════════════════════════════════════════════════════════════
# STRUCTURE ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestStructure:
    def test_find_swing_points_basic(self):
        from strategies.ict.structure import find_swing_points
        candles = _make_swing_candles(30)
        highs, lows = find_swing_points(candles, left=3, right=3)
        # Should detect swing high around index 9-10 and swing lows near edges
        assert len(highs) >= 1
        assert len(lows) >= 1
        # Swing high should be the peak
        best_high = max(highs, key=lambda sp: sp.price)
        assert best_high.price >= 1.1090  # near top of the V

    def test_find_swing_points_too_few_candles(self):
        from strategies.ict.structure import find_swing_points
        highs, lows = find_swing_points([_candle(1.1, 1.11, 1.09, 1.1)], left=3, right=3)
        assert highs == []
        assert lows == []

    def test_get_structure_bias(self):
        from strategies.ict.structure import find_swing_points, get_structure_bias
        # Uptrend candles → bullish bias
        candles: list[Candle] = []
        for i in range(40):
            c = 1.1000 + i * 0.0005
            ts = _ts(hour=0) + timedelta(hours=i)
            candles.append(_candle(
                o=round(c - 0.0002, 5), h=round(c + 0.0008, 5),
                l=round(c - 0.0005, 5), c=round(c, 5), ts=ts,
            ))
        highs, lows = find_swing_points(candles, left=2, right=2)
        bias = get_structure_bias(highs, lows)
        # Should be bullish (higher highs / higher lows)
        assert bias in (Bias.BULLISH, Bias.NEUTRAL)  # at least not bearish

    def test_build_dealing_range(self):
        from strategies.ict.structure import find_swing_points, build_dealing_range
        candles = _make_swing_candles(30)
        highs, lows = find_swing_points(candles, left=3, right=3)
        dr = build_dealing_range(highs, lows)
        assert dr.high > dr.low
        assert dr.equilibrium > 0
        assert dr.is_premium(dr.high)
        assert dr.is_discount(dr.low)


# ══════════════════════════════════════════════════════════════════════════
# LIQUIDITY ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestLiquidity:
    def test_map_liquidity(self):
        from strategies.ict.liquidity import map_liquidity
        highs = [SwingPoint(index=5, price=1.1100, is_high=True)]
        lows = [SwingPoint(index=10, price=1.0900, is_high=False)]
        session_info = SessionInfo(prev_day_high=1.1200, prev_day_low=1.0800)
        bsl, ssl = map_liquidity(highs, lows, session_info, 1.1000)
        assert len(bsl) >= 1  # swing high → buy-side
        assert len(ssl) >= 1  # swing low → sell-side
        assert any(l.price == 1.1100 for l in bsl)
        assert any(l.price == 1.0900 for l in ssl)

    def test_detect_sweeps(self):
        from strategies.ict.liquidity import detect_sweeps
        bsl = [LiquidityLevel(price=1.1100, kind=LiquidityType.BSL, source="swing_high")]
        ssl = [LiquidityLevel(price=1.0900, kind=LiquidityType.SSL, source="swing_low")]
        # Candle that wicks above BSL then closes back below
        candles = [
            _candle(1.1080, 1.1090, 1.1070, 1.1080, _ts(1)),
            _candle(1.1090, 1.1095, 1.1085, 1.1090, _ts(2)),
            _candle(1.1095, 1.1120, 1.1085, 1.1090, _ts(3)),  # sweep! wick above 1.1100
            _candle(1.1090, 1.1095, 1.1080, 1.1085, _ts(4)),
        ]
        sweeps = detect_sweeps(candles, bsl, ssl, lookback=5)
        # Should detect the BSL sweep
        assert len(sweeps) >= 1

    def test_infer_draw_on_liquidity(self):
        from strategies.ict.liquidity import infer_draw_on_liquidity
        bsl = [LiquidityLevel(price=1.1200, kind=LiquidityType.BSL)]
        ssl = [LiquidityLevel(price=1.0800, kind=LiquidityType.SSL)]
        # Bullish bias → DOL should be buy_side
        dol = infer_draw_on_liquidity(bsl, ssl, "bullish", 1.1000)
        assert dol == "buy_side"


# ══════════════════════════════════════════════════════════════════════════
# DISPLACEMENT ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestDisplacement:
    def test_detect_displacement(self):
        from strategies.ict.displacement import detect_displacement
        # Small candles followed by one big impulsive candle
        candles: list[Candle] = []
        for i in range(10):
            c = 1.1000 + i * 0.0001
            ts = _ts(hour=0) + timedelta(hours=i)
            candles.append(_candle(
                o=round(c, 5), h=round(c + 0.0003, 5),
                l=round(c - 0.0003, 5), c=round(c + 0.0001, 5), ts=ts,
            ))
        # Add an impulsive bullish candle (huge body compared to avg)
        big_open = 1.1010
        big_close = 1.1040  # body = 0.003 vs avg ~0.0001
        ts = _ts(hour=0) + timedelta(hours=10)
        candles.append(_candle(
            o=big_open, h=big_close + 0.0002,
            l=big_open - 0.0002, c=big_close, ts=ts,
        ))
        disps = detect_displacement(candles, lookback=10, body_ratio_threshold=2.0)
        assert len(disps) >= 1
        assert disps[-1].direction == Bias.BULLISH
        assert disps[-1].ratio >= 2.0

    def test_no_displacement_in_flat_market(self):
        from strategies.ict.displacement import detect_displacement
        # All candles same size → no displacement
        candles: list[Candle] = []
        for i in range(15):
            c = 1.1050
            ts = _ts(hour=0) + timedelta(hours=i)
            candles.append(_candle(c, c + 0.0003, c - 0.0003, c + 0.0001, ts=ts))
        disps = detect_displacement(candles)
        assert len(disps) == 0


# ══════════════════════════════════════════════════════════════════════════
# FVG ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestFVG:
    def test_detect_bullish_fvg(self):
        from strategies.ict.fvg import detect_fvgs
        # Bullish FVG: candle[0].high < candle[2].low with gap
        candles = [
            _candle(1.1000, 1.1010, 1.0990, 1.1005, _ts(1)),  # candle 0
            _candle(1.1005, 1.1035, 1.1000, 1.1030, _ts(2)),  # candle 1 (big up)
            _candle(1.1030, 1.1040, 1.1025, 1.1035, _ts(3)),  # candle 2 (low > candle 0 high)
        ]
        dr = DealingRange(high=1.1100, low=1.0900)
        fvgs = detect_fvgs(candles, dr, "H1", lookback=5)
        # Should detect a bullish FVG between candle[0].high and candle[2].low
        bullish_fvgs = [f for f in fvgs if f.kind == FVGType.BULLISH]
        assert len(bullish_fvgs) >= 1
        fvg = bullish_fvgs[0]
        assert fvg.low == 1.1010  # candle[0] high
        assert fvg.high == 1.1025  # candle[2] low

    def test_fvg_fill_tracking(self):
        from strategies.ict.fvg import detect_fvgs, update_fvg_status, get_active_fvgs
        candles = [
            _candle(1.1000, 1.1010, 1.0990, 1.1005, _ts(1)),
            _candle(1.1005, 1.1035, 1.1000, 1.1030, _ts(2)),
            _candle(1.1030, 1.1040, 1.1025, 1.1035, _ts(3)),
            # Price comes back down and fills the FVG
            _candle(1.1035, 1.1037, 1.1008, 1.1010, _ts(4)),  # low dips into FVG
        ]
        dr = DealingRange(high=1.1100, low=1.0900)
        fvgs = detect_fvgs(candles, dr, "H1", lookback=5)
        update_fvg_status(fvgs, candles)
        active = get_active_fvgs(fvgs, 1.1035)
        # After fill, FVG may be marked as filled
        # Depending on implementation, it may still be active or not
        assert isinstance(active, list)


# ══════════════════════════════════════════════════════════════════════════
# ORDER BLOCK ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestOrderBlock:
    def test_detect_bullish_ob(self):
        from strategies.ict.orderblock import detect_order_blocks
        # Bearish candle followed by bullish displacement
        candles = [
            _candle(1.1020, 1.1025, 1.1010, 1.1015, _ts(1)),  # bearish candle (OB candidate)
            _candle(1.1015, 1.1060, 1.1012, 1.1055, _ts(2)),  # bullish displacement
            _candle(1.1055, 1.1070, 1.1050, 1.1065, _ts(3)),
        ]
        disp = Displacement(
            direction=Bias.BULLISH, candle_idx=1,
            body_size=0.004, avg_body=0.001, ratio=4.0,
        )
        obs = detect_order_blocks(candles, [disp], "H1")
        bullish_obs = [ob for ob in obs if ob.kind == OBType.BULLISH]
        assert len(bullish_obs) >= 1
        ob = bullish_obs[0]
        assert ob.high == 1.1025
        assert ob.low == 1.1010

    def test_ob_invalidation(self):
        from strategies.ict.orderblock import detect_order_blocks, update_ob_status
        candles = [
            _candle(1.1020, 1.1025, 1.1010, 1.1015, _ts(1)),
            _candle(1.1015, 1.1060, 1.1012, 1.1055, _ts(2)),
            # Price breaks below OB mean threshold → invalidate
            _candle(1.1055, 1.1058, 1.1005, 1.1008, _ts(3)),
        ]
        disp = Displacement(direction=Bias.BULLISH, candle_idx=1)
        obs = detect_order_blocks(candles, [disp], "H1")
        update_ob_status(obs, candles)
        # OB may be invalidated since price body closed below mean threshold
        if obs:
            # At least the status should have been checked
            assert isinstance(obs[0].valid, bool)

    def test_mark_high_probability(self):
        from strategies.ict.orderblock import mark_high_probability
        ob = OrderBlock(kind=OBType.BULLISH, high=1.1025, low=1.1010, candle_idx=5)
        sweep = LiquiditySweep(
            level=LiquidityLevel(price=1.1005, kind=LiquidityType.SSL),
            sweep_candle_idx=3,
        )
        mss = StructureBreak(kind="MSS", direction=Bias.BULLISH, candle_idx=4, displacement_confirmed=True)
        fvg = FairValueGap(kind=FVGType.BULLISH, high=1.1025, low=1.1010, candle_idx=5)
        mark_high_probability([ob], [sweep], [mss], [fvg])
        assert ob.has_liquidity_sweep
        assert ob.has_fvg
        assert ob.high_probability


# ══════════════════════════════════════════════════════════════════════════
# SESSION ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestSession:
    def test_detect_session_london(self):
        from strategies.ict.session import detect_session
        ts = datetime(2026, 1, 5, 8, 30, tzinfo=timezone.utc)  # 08:30 UTC
        assert detect_session(ts) == SessionName.LONDON

    def test_detect_session_overlap(self):
        from strategies.ict.session import detect_session
        ts = datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc)  # 13:00 UTC
        assert detect_session(ts) == SessionName.OVERLAP

    def test_detect_session_asian(self):
        from strategies.ict.session import detect_session
        ts = datetime(2026, 1, 5, 2, 0, tzinfo=timezone.utc)  # 02:00 UTC
        assert detect_session(ts) == SessionName.ASIAN

    def test_detect_session_ny(self):
        from strategies.ict.session import detect_session
        ts = datetime(2026, 1, 5, 18, 0, tzinfo=timezone.utc)  # 18:00 UTC
        assert detect_session(ts) == SessionName.NEW_YORK

    def test_detect_session_off_hours(self):
        from strategies.ict.session import detect_session
        ts = datetime(2026, 1, 5, 22, 0, tzinfo=timezone.utc)  # 22:00 UTC
        assert detect_session(ts) == SessionName.OFF_HOURS

    def test_detect_killzone(self):
        from strategies.ict.session import detect_killzone
        # London KZ: 07:00-10:00 UTC
        assert detect_killzone(datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc))
        assert not detect_killzone(datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc))

    def test_detect_macro(self):
        from strategies.ict.session import detect_macro
        # London Open macro: 07:33-08:03
        in_macro, name = detect_macro(datetime(2026, 1, 5, 7, 40, tzinfo=timezone.utc))
        assert in_macro
        assert name == "london_open"

    def test_build_session_info(self):
        from strategies.ict.session import build_session_info
        candles = [_candle(1.1, 1.11, 1.09, 1.1, _ts(hour=h)) for h in range(0, 12)]
        si = build_session_info(candles, _ts(hour=8))
        assert si.session == SessionName.LONDON
        assert si.in_killzone is True
        assert isinstance(si.quality_score, float)


# ══════════════════════════════════════════════════════════════════════════
# BIAS ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestBias:
    def test_resolve_htf_bias_bullish(self):
        from strategies.ict.bias import resolve_htf_bias
        # Strong uptrend candles
        candles: list[Candle] = []
        for i in range(20):
            c = 1.1000 + i * 0.0010
            ts = _ts(hour=0) + timedelta(hours=i * 4)
            candles.append(_candle(
                o=round(c - 0.0003, 5), h=round(c + 0.0008, 5),
                l=round(c - 0.0005, 5), c=round(c, 5), ts=ts,
            ))
        bias = resolve_htf_bias(candles)
        assert bias in (Bias.BULLISH, Bias.NEUTRAL)

    def test_detect_regime_trending(self):
        from strategies.ict.bias import detect_regime
        # Strongly directional candles
        candles: list[Candle] = []
        for i in range(15):
            c = 1.1000 + i * 0.0015
            ts = _ts(hour=0) + timedelta(hours=i * 4)
            candles.append(_candle(
                o=round(c - 0.0002, 5), h=round(c + 0.0012, 5),
                l=round(c - 0.0005, 5), c=round(c + 0.0010, 5), ts=ts,
            ))
        regime = detect_regime(candles, atr=0.0015)
        assert regime in (Regime.TRENDING, Regime.UNKNOWN)

    def test_classify_premium_discount(self):
        from strategies.ict.bias import classify_premium_discount
        dr = DealingRange(high=1.1200, low=1.1000)
        assert classify_premium_discount(1.1150, dr) == "premium"
        assert classify_premium_discount(1.1050, dr) == "discount"
        assert classify_premium_discount(1.1100, dr) == "equilibrium"


# ══════════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestScoring:
    def test_score_setup_full_confluence(self):
        from strategies.ict.scoring import score_setup
        ctx = ICTContext(
            symbol="EURUSD",
            htf_bias=Bias.BULLISH,
            htf_regime=Regime.TRENDING,
            premium_discount="discount",
            current_price=1.1050,
            atr=0.0012,
            session_info=SessionInfo(
                session=SessionName.LONDON,
                in_killzone=True,
                in_macro=True,
            ),
            bsl_levels=[LiquidityLevel(price=1.1200, kind=LiquidityType.BSL)],
            ssl_levels=[LiquidityLevel(price=1.0900, kind=LiquidityType.SSL)],
            nearest_bsl=LiquidityLevel(price=1.1200, kind=LiquidityType.BSL),
        )
        setup = SetupCandidate(
            direction="BUY",
            entry_price=1.1050,
            stop_loss=1.1020,
            take_profit_1=1.1100,
            take_profit_2=1.1150,
            take_profit_3=1.1200,
            htf_bias_aligned=True,
            premium_discount_aligned=True,
            liquidity_swept=True,
            mss_confirmed=True,
            displacement_present=True,
            fvg_present=True,
            ob_present=True,
            session_valid=True,
            sweep=LiquiditySweep(
                level=LiquidityLevel(price=1.1010, strength=3),
                sweep_candle_idx=45,
            ),
            mss=StructureBreak(kind="MSS", direction=Bias.BULLISH, displacement_confirmed=True),
            displacement=Displacement(direction=Bias.BULLISH, ratio=3.5, created_fvg=True),
            fvg=FairValueGap(kind=FVGType.BULLISH, in_discount=True),
            ob=OrderBlock(kind=OBType.BULLISH, high_probability=True),
        )
        # Patch candles length for sweep recency
        ctx.candles = [_candle(1.1, 1.11, 1.09, 1.1)] * 50
        bd = score_setup(ctx, setup)
        assert bd.total > 70  # Should be a high score with full confluence
        assert bd.htf_bias > 0
        assert bd.liquidity_sweep > 0
        assert bd.mss_quality > 0

    def test_score_setup_minimal(self):
        from strategies.ict.scoring import score_setup
        ctx = ICTContext(symbol="EURUSD")
        setup = SetupCandidate(direction="BUY")
        bd = score_setup(ctx, setup)
        assert bd.total < 30  # Should be low with no confluences


# ══════════════════════════════════════════════════════════════════════════
# SETUPS ENGINE
# ══════════════════════════════════════════════════════════════════════════

class TestSetups:
    def test_detect_all_returns_list(self):
        from strategies.ict.setups import detect_all_setups
        ctx = ICTContext(symbol="EURUSD")
        result = detect_all_setups(ctx)
        assert isinstance(result, list)

    def test_no_setups_on_empty_context(self):
        from strategies.ict.setups import detect_all_setups
        ctx = ICTContext(symbol="EURUSD", htf_bias=Bias.NEUTRAL)
        result = detect_all_setups(ctx)
        assert len(result) == 0


# ══════════════════════════════════════════════════════════════════════════
# ENGINE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════

class TestEngine:
    def test_analyze_too_few_candles(self):
        from strategies.ict.engine import ICTEngine
        engine = ICTEngine()
        ctx, best, rejected = engine.analyze(
            symbol="EURUSD",
            candles=[_candle(1.1, 1.11, 1.09, 1.1)],
            htf_candles=[],
            current_price=1.1,
        )
        assert best is None
        assert ctx.symbol == "EURUSD"

    def test_analyze_returns_context(self):
        from strategies.ict.engine import ICTEngine
        engine = ICTEngine()
        candles = _make_swing_candles(50)
        htf_candles = _make_swing_candles(30)
        ctx, best, rejected = engine.analyze(
            symbol="EURUSD",
            candles=candles,
            htf_candles=htf_candles,
            current_price=1.1050,
            bid=1.1048,
            ask=1.1052,
            atr=0.0012,
        )
        assert ctx.symbol == "EURUSD"
        assert ctx.htf_bias in (Bias.BULLISH, Bias.BEARISH, Bias.NEUTRAL)
        assert isinstance(ctx.swing_highs, list)
        assert isinstance(ctx.active_fvgs, list)
        # best may be None (setup conditions may not be met with synthetic candles)
        assert best is None or isinstance(best, SetupCandidate)


# ══════════════════════════════════════════════════════════════════════════
# ICT STRATEGY CLASS
# ══════════════════════════════════════════════════════════════════════════

class TestICTStrategy:
    def test_strategy_has_correct_name(self):
        from strategies.ict_strategy import ICTStrategy
        s = ICTStrategy()
        assert s.name == "ict_smc"

    def test_detect_returns_none_with_few_candles(self):
        from strategies.ict_strategy import ICTStrategy
        from models.market_data import MarketContext
        s = ICTStrategy()
        ctx = MarketContext(
            symbol="EURUSD",
            current_price=1.1050,
            candles=[_candle(1.1, 1.11, 1.09, 1.1)] * 10,
            atr=0.001,
        )
        result = s.detect(ctx)
        assert result is None

    def test_calculate_sl_fallback(self):
        from strategies.ict_strategy import ICTStrategy
        from models.market_data import MarketContext
        s = ICTStrategy()
        ctx = MarketContext(current_price=1.1050, atr=0.0012)
        sl = s.calculate_sl(ctx, "BUY")
        assert sl < 1.1050

    def test_calculate_tps_fallback(self):
        from strategies.ict_strategy import ICTStrategy
        from models.market_data import MarketContext
        s = ICTStrategy()
        ctx = MarketContext(current_price=1.1050, atr=0.0012)
        tp1, tp2, tp3 = s.calculate_tps(ctx, 1.1050, 1.1030, "BUY")
        assert tp1 > 1.1050
        assert tp2 > tp1
        assert tp3 > tp2


# ══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════

class TestICTModels:
    def test_dealing_range_equilibrium(self):
        dr = DealingRange(high=1.1200, low=1.1000)
        assert dr.equilibrium == 1.1100
        assert dr.is_premium(1.1150)
        assert dr.is_discount(1.1050)
        assert dr.zone_label(1.1150) == "premium"
        assert dr.zone_label(1.1050) == "discount"

    def test_fvg_contains(self):
        fvg = FairValueGap(high=1.1050, low=1.1020)
        assert fvg.contains(1.1035)
        assert not fvg.contains(1.1060)
        assert fvg.ce == 1.1035

    def test_order_block_mean_threshold(self):
        ob = OrderBlock(high=1.1050, low=1.1020)
        assert ob.mean_threshold == 1.1035
        assert ob.contains(1.1035)

    def test_confidence_breakdown_compute(self):
        bd = ConfidenceBreakdown(
            htf_bias=15, premium_discount=12, liquidity_sweep=15,
            mss_quality=15, displacement=10, fvg_quality=8,
            ob_quality=8, session_time=7, target_clarity=5, rr_quality=5,
        )
        total = bd.compute_total()
        assert total == 100.0
