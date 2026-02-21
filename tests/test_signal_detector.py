"""Tests for strategy.signal_detector."""

import time
from unittest.mock import patch

from core.types import MarketInfo, Side
from feeds.price_tracker import PriceTracker
from strategy.signal_detector import SignalDetector


def _make_market(
    up_price: float = 0.50,
    down_price: float = 0.50,
    window_start=None,
) -> MarketInfo:
    if window_start is None:
        window_start = int(time.time()) - 60  # 60s into window
    return MarketInfo(
        condition_id="test_cond",
        question="BTC up or down?",
        up_token_id="up_token",
        down_token_id="down_token",
        up_price=up_price,
        down_price=down_price,
        window_start=int(window_start),
        window_end=int(window_start) + 300,
    )


def _make_tracker_with_momentum(momentum_pct: float, oracle_lag_pct: float = 0.001) -> PriceTracker:
    """Build a tracker that shows the desired momentum."""
    t = PriceTracker(window_seconds=60)
    base_ts = int(time.time() * 1000)
    base_price = 100_000.0
    end_price = base_price * (1 + momentum_pct)

    # Build consistent trend
    steps = 10
    for i in range(steps + 1):
        frac = i / steps
        price = base_price + (end_price - base_price) * frac
        t.update(price, base_ts + int(frac * 55_000))

    # Set oracle behind
    oracle_price = end_price * (1 - oracle_lag_pct)
    t.update_oracle(oracle_price, base_ts)

    return t


class TestSignalDetector:
    def test_strong_up_signal(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(0.002, 0.001)  # 0.2% up
        market = _make_market(up_price=0.48, down_price=0.52)

        signal = d.evaluate(tracker, market)

        assert signal is not None
        assert signal.side == Side.UP
        assert signal.confidence >= 0.70

    def test_strong_down_signal(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(-0.002, 0.001)  # 0.2% down
        market = _make_market(up_price=0.52, down_price=0.48)

        signal = d.evaluate(tracker, market)

        assert signal is not None
        assert signal.side == Side.DOWN
        assert signal.confidence >= 0.70

    def test_no_signal_low_momentum(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(0.0001)  # too low
        market = _make_market()

        signal = d.evaluate(tracker, market)
        assert signal is None

    def test_no_signal_bad_timing_too_early(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(0.002, 0.001)
        # Only 10s into window
        market = _make_market(window_start=time.time() - 10)

        signal = d.evaluate(tracker, market)
        assert signal is None

    def test_no_signal_bad_timing_too_late(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(0.002, 0.001)
        # 250s into window (past 180s cutoff)
        market = _make_market(window_start=time.time() - 250)

        signal = d.evaluate(tracker, market)
        assert signal is None

    def test_no_signal_price_too_high(self):
        d = SignalDetector()
        tracker = _make_tracker_with_momentum(0.002, 0.001)
        market = _make_market(up_price=0.70, down_price=0.30)

        signal = d.evaluate(tracker, market)
        # Should still work — UP side is 0.70 (too expensive)
        # but DOWN side might not trigger since momentum is positive
        assert signal is None

    def test_confidence_scaling(self):
        d = SignalDetector()
        # High momentum + deep lag + good price + consistent trend → high confidence
        tracker = _make_tracker_with_momentum(0.003, 0.002)
        market = _make_market(up_price=0.38, down_price=0.62)

        signal = d.evaluate(tracker, market)
        assert signal is not None
        assert signal.confidence >= 0.85
