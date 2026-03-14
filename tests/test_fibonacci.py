"""Tests for the Fibonacci engine — retracement, Golden Zone, confluence."""

from datetime import UTC, datetime

import pytest

from models.market_data import Candle
from models.ict_models import (
    Bias, Displacement, FairValueGap, FVGType,
    OrderBlock, OBType, SwingPoint,
    LiquidityLevel, LiquidityType,
    FibonacciRetracement, ICTContext, SetupCandidate, ConfidenceBreakdown,
)
from strategies.ict.fibonacci import (
    detect_fib_levels,
    check_golden_zone_confluence,
    check_liquidity_target,
    validate_retracement_depth,
)
from strategies.ict.scoring import score_setup


# ── Helpers ──────────────────────────────────────────────────────────────

def _ts(hour=12):
    return datetime(2026, 3, 14, hour, 0, 0, tzinfo=UTC)


def _candle(o, h, l, c, idx=0):
    return Candle(
        timestamp=_ts(idx), open=o, high=h, low=l, close=c, volume=100,
    )


def _bullish_displacement_candles():
    """Create a set of candles with a clear bullish displacement.

    Candles 0-4: flat at 1.00
    Candle 5: big bullish displacement 1.00 → 1.03  (3× avg body)
    Candles 6-7: pullback
    """
    candles = []
    # Flat candles (avg body ~0.002)
    for i in range(5):
        candles.append(_candle(1.000 + i * 0.001, 1.003 + i * 0.001,
                               0.998 + i * 0.001, 1.002 + i * 0.001, i))
    # Strong bullish displacement candle (body=0.025, range=0.028)
    candles.append(_candle(1.005, 1.033, 1.003, 1.030, 5))
    # Pullback candles
    candles.append(_candle(1.030, 1.031, 1.020, 1.022, 6))
    candles.append(_candle(1.022, 1.024, 1.018, 1.020, 7))
    return candles


class TestFibonacciLevels:
    """Test Fibonacci level detection from displacement legs."""

    def test_fib_levels_from_bullish_displacement(self):
        """Verify Fibonacci levels are correctly calculated."""
        candles = _bullish_displacement_candles()
        disp = Displacement(
            direction=Bias.BULLISH, candle_idx=5,
            body_size=0.025, avg_body=0.002, ratio=12.5,
            timestamp=_ts(5),
        )
        # Swing low before displacement
        swing_lows = [SwingPoint(index=2, price=0.998, is_high=False, timestamp=_ts(2))]
        swing_highs = [SwingPoint(index=3, price=1.003, is_high=True, timestamp=_ts(3))]

        fib = detect_fib_levels(candles, [disp], swing_highs, swing_lows, Bias.BULLISH)

        assert fib is not None
        assert fib.direction == Bias.BULLISH
        assert fib.anchor_low == 0.998
        assert fib.anchor_high == 1.033

        # Check level count
        assert len(fib.levels) == 5

        # Check ratios
        ratios = [l.ratio for l in fib.levels]
        assert 0.382 in ratios
        assert 0.5 in ratios
        assert 0.618 in ratios
        assert 0.705 in ratios
        assert 0.786 in ratios

    def test_golden_zone_boundaries(self):
        """Verify Golden Zone is correctly identified (0.618–0.705)."""
        candles = _bullish_displacement_candles()
        disp = Displacement(
            direction=Bias.BULLISH, candle_idx=5,
            body_size=0.025, avg_body=0.002, ratio=12.5,
            timestamp=_ts(5),
        )
        swing_lows = [SwingPoint(index=2, price=0.998, is_high=False, timestamp=_ts(2))]
        swing_highs = []

        fib = detect_fib_levels(candles, [disp], swing_highs, swing_lows, Bias.BULLISH)

        assert fib is not None
        leg = fib.anchor_high - fib.anchor_low

        # Golden Zone for bullish: high - 0.618*leg to high - 0.705*leg
        expected_gz_top = round(fib.anchor_high - 0.618 * leg, 6)
        expected_gz_bot = round(fib.anchor_high - 0.705 * leg, 6)
        assert fib.golden_zone_top == expected_gz_top
        assert fib.golden_zone_bottom == expected_gz_bot
        assert fib.golden_zone_top > fib.golden_zone_bottom

    def test_no_fib_without_displacement(self):
        """No Fibonacci without displacement."""
        candles = _bullish_displacement_candles()
        fib = detect_fib_levels(candles, [], [], [], Bias.BULLISH)
        assert fib is None

    def test_bearish_fib_levels(self):
        """Test bearish Fibonacci (retracement is a bounce UP)."""
        candles = []
        for i in range(5):
            candles.append(_candle(1.030 - i * 0.001, 1.033 - i * 0.001,
                                   1.028 - i * 0.001, 1.029 - i * 0.001, i))
        # Bearish displacement
        candles.append(_candle(1.025, 1.027, 0.998, 1.000, 5))
        candles.append(_candle(1.000, 1.012, 0.998, 1.010, 6))

        disp = Displacement(
            direction=Bias.BEARISH, candle_idx=5,
            body_size=0.025, avg_body=0.002, ratio=12.5,
            timestamp=_ts(5),
        )
        swing_highs = [SwingPoint(index=0, price=1.033, is_high=True, timestamp=_ts(0))]
        swing_lows = []

        fib = detect_fib_levels(candles, [disp], swing_highs, swing_lows, Bias.BEARISH)

        assert fib is not None
        assert fib.direction == Bias.BEARISH
        assert fib.anchor_high == 1.033
        # Bearish GZ: prices are ABOVE anchor_low (bounce up into GZ)
        assert fib.golden_zone_top > fib.golden_zone_bottom


class TestGoldenZoneConfluence:
    """Test FVG CE and OB mean threshold confluence with Golden Zone."""

    def _make_fib(self) -> FibonacciRetracement:
        return FibonacciRetracement(
            direction=Bias.BULLISH,
            anchor_low=1.000,
            anchor_high=1.100,
            golden_zone_top=1.0382,   # high - 0.618 * 0.1
            golden_zone_bottom=1.0295,  # high - 0.705 * 0.1
            timestamp=_ts(),
        )

    def test_gz_fvg_confluence(self):
        """FVG CE inside Golden Zone → confluence flagged."""
        fib = self._make_fib()
        fvg = FairValueGap(
            kind=FVGType.BULLISH,
            high=1.040, low=1.030,
            # CE = midpoint = 1.035 → inside GZ [1.0295, 1.0382]
        )
        fvg.ce = 1.035

        check_golden_zone_confluence(fib, [fvg], [])

        assert fib.gz_fvg_confluence is True
        assert fib.gz_ce_confluence is True

    def test_no_fvg_confluence_outside_gz(self):
        """FVG CE outside Golden Zone → no confluence."""
        fib = self._make_fib()
        fvg = FairValueGap(kind=FVGType.BULLISH, high=1.080, low=1.070)
        fvg.ce = 1.075  # way above GZ

        check_golden_zone_confluence(fib, [fvg], [])

        assert fib.gz_fvg_confluence is False

    def test_gz_ob_confluence(self):
        """OB mean threshold inside Golden Zone → confluence flagged."""
        fib = self._make_fib()
        ob = OrderBlock(
            kind=OBType.BULLISH,
            high=1.038, low=1.030,
        )
        ob.mean_threshold = 1.034  # inside GZ

        check_golden_zone_confluence(fib, [], [ob])

        assert fib.gz_ob_confluence is True

    def test_triple_confluence(self):
        """FVG CE + OB mean_threshold both in GZ → full confluence."""
        fib = self._make_fib()
        fvg = FairValueGap(kind=FVGType.BULLISH, high=1.040, low=1.030)
        fvg.ce = 1.035
        ob = OrderBlock(kind=OBType.BULLISH, high=1.038, low=1.030)
        ob.mean_threshold = 1.034

        check_golden_zone_confluence(fib, [fvg], [ob])

        assert fib.gz_fvg_confluence is True
        assert fib.gz_ob_confluence is True
        assert fib.gz_ce_confluence is True


class TestLiquidityTarget:
    """Test liquidity target validation (Rule #2)."""

    def test_bullish_has_target(self):
        fib = FibonacciRetracement(direction=Bias.BULLISH, timestamp=_ts())
        bsl = [LiquidityLevel(price=1.100, kind=LiquidityType.BSL)]

        check_liquidity_target(fib, bsl, [], current_price=1.050)

        assert fib.has_liquidity_target is True

    def test_bullish_no_target(self):
        fib = FibonacciRetracement(direction=Bias.BULLISH, timestamp=_ts())
        bsl = [LiquidityLevel(price=1.020, kind=LiquidityType.BSL)]  # below price

        check_liquidity_target(fib, bsl, [], current_price=1.050)

        assert fib.has_liquidity_target is False

    def test_bearish_has_target(self):
        fib = FibonacciRetracement(direction=Bias.BEARISH, timestamp=_ts())
        ssl = [LiquidityLevel(price=0.990, kind=LiquidityType.SSL)]

        check_liquidity_target(fib, [], ssl, current_price=1.050)

        assert fib.has_liquidity_target is True


class TestRetracementDepth:
    """Test retracement depth classification (Rule #8)."""

    def _make_bullish_fib(self):
        return FibonacciRetracement(
            direction=Bias.BULLISH,
            anchor_low=1.000, anchor_high=1.100,
            timestamp=_ts(),
        )

    def test_golden_zone(self):
        fib = self._make_bullish_fib()
        # Price at 0.65 retracement: 1.100 - 0.65*0.1 = 1.035
        result = validate_retracement_depth(fib, 1.035)
        assert result == "golden_zone"

    def test_too_shallow(self):
        fib = self._make_bullish_fib()
        # Price at 0.2 retracement: 1.100 - 0.2*0.1 = 1.080
        result = validate_retracement_depth(fib, 1.080)
        assert result == "too_shallow"

    def test_too_deep(self):
        fib = self._make_bullish_fib()
        # Price at 0.9 retracement: 1.100 - 0.9*0.1 = 1.010
        result = validate_retracement_depth(fib, 1.010)
        assert result == "too_deep"

    def test_acceptable(self):
        fib = self._make_bullish_fib()
        # Price at 0.5 retracement: 1.100 - 0.5*0.1 = 1.050
        result = validate_retracement_depth(fib, 1.050)
        assert result == "acceptable"

    def test_deep(self):
        fib = self._make_bullish_fib()
        # Price at 0.75 retracement: 1.100 - 0.75*0.1 = 1.025
        result = validate_retracement_depth(fib, 1.025)
        assert result == "deep"

    def test_outside_above(self):
        fib = self._make_bullish_fib()
        result = validate_retracement_depth(fib, 1.150)
        assert result == "outside"


class TestScoringFibonacci:
    """Test Fibonacci scoring component integration."""

    def test_scoring_includes_fibonacci(self):
        """Verify ConfidenceBreakdown includes fibonacci_quality."""
        bd = ConfidenceBreakdown()
        bd.htf_bias = 10
        bd.fibonacci_quality = 12
        bd.compute_total()
        assert bd.fibonacci_quality == 12
        assert bd.total >= 22  # at least htf_bias + fibonacci

    def test_full_fib_confluence_scoring(self):
        """Max Fibonacci score with full confluence: GZ + CE + OB + target + P/D."""
        fib = FibonacciRetracement(
            direction=Bias.BULLISH,
            anchor_low=1.000, anchor_high=1.100,
            timestamp=_ts(),
        )
        fib.retracement_depth = "golden_zone"  # +5
        fib.gz_fvg_confluence = True           # +3
        fib.gz_ob_confluence = True            # +3
        fib.has_liquidity_target = True        # +2

        ctx = ICTContext(
            fibonacci=fib,
            htf_bias=Bias.BULLISH,
        )
        setup = SetupCandidate(
            direction="BUY",
            premium_discount_aligned=True,     # +2
        )

        from strategies.ict.scoring import _score_fibonacci
        score = _score_fibonacci(ctx, setup)

        assert score == 15.0  # capped at 15

    def test_penalty_too_deep(self):
        """Score penalty when retracement is too deep (>0.786)."""
        fib = FibonacciRetracement(
            direction=Bias.BULLISH,
            anchor_low=1.000, anchor_high=1.100,
            timestamp=_ts(),
        )
        fib.retracement_depth = "too_deep"

        ctx = ICTContext(fibonacci=fib, htf_bias=Bias.BULLISH)
        setup = SetupCandidate(direction="BUY")

        from strategies.ict.scoring import _score_fibonacci
        score = _score_fibonacci(ctx, setup)

        assert score == -3.0

    def test_no_fib_zero_score(self):
        """No Fibonacci → 0 score (never blocks a trade)."""
        ctx = ICTContext(fibonacci=None)
        setup = SetupCandidate(direction="BUY")

        from strategies.ict.scoring import _score_fibonacci
        score = _score_fibonacci(ctx, setup)

        assert score == 0.0


class TestFibonacciTargets:
    """Test Fibonacci integration for TP, SL, and Entry refinement."""

    def _make_bullish_fib(self):
        # Bullish leg from 1.000 to 1.100 (range 0.100)
        # GZ = 0.618 to 0.705 retracement
        return FibonacciRetracement(
            direction=Bias.BULLISH,
            anchor_low=1.000, anchor_high=1.100,
            golden_zone_top=1.0382,
            golden_zone_bottom=1.0295,
            golden_zone_mid=1.03385,
            invalidation_price=1.0214,  # 1.100 - (0.786 * 0.1)
            ext_1_000=1.100,
            ext_neg_0_272=1.1272,      # 1.100 + (0.272 * 0.1)
            ext_neg_0_618=1.1618,      # 1.100 + (0.618 * 0.1)
            timestamp=_ts(),
        )

    def test_calc_sl_uses_fibonacci_invalidation(self):
        ctx = ICTContext(fibonacci=self._make_bullish_fib())
        ctx.atr = 0.001
        
        from strategies.ict.setups import _calc_sl
        sl, reason = _calc_sl(ctx, "BUY")
        
        # Should be invalidation_price - atr*0.3 buffer
        expected_sl = round(1.0214 - 0.0003, 5)
        assert sl == expected_sl
        assert reason == "fib_invalidation"

    def test_calc_tps_uses_fibonacci_extensions(self):
        ctx = ICTContext(fibonacci=self._make_bullish_fib())
        
        from strategies.ict.setups import _calc_tps
        tp1, tp2, tp3, reason = _calc_tps(ctx, entry=1.03385, sl=1.0211, direction="BUY")
        
        assert tp1 == 1.100
        assert tp2 == 1.1272
        assert tp3 == 1.1618
        assert reason == "fib_extensions"

