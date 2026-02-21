"""Tests for feeds.price_tracker."""

import time

from feeds.price_tracker import PriceTracker


class TestPriceTracker:
    def test_momentum_positive(self):
        t = PriceTracker(window_seconds=60)
        base_ts = int(time.time() * 1000)

        t.update(100_000.0, base_ts)
        t.update(100_100.0, base_ts + 30_000)
        t.update(100_200.0, base_ts + 59_000)

        assert t.momentum_pct > 0
        assert abs(t.momentum_pct - 0.002) < 0.001

    def test_momentum_negative(self):
        t = PriceTracker(window_seconds=60)
        base_ts = int(time.time() * 1000)

        t.update(100_000.0, base_ts)
        t.update(99_900.0, base_ts + 30_000)

        assert t.momentum_pct < 0

    def test_momentum_empty(self):
        t = PriceTracker()
        assert t.momentum_pct == 0.0

    def test_eviction(self):
        t = PriceTracker(window_seconds=10)
        base_ts = int(time.time() * 1000)

        t.update(100.0, base_ts)
        t.update(101.0, base_ts + 5_000)
        t.update(102.0, base_ts + 15_000)  # first tick is >10s old

        assert t.window_size == 2
        assert t.latest_price == 102.0

    def test_oracle_divergence(self):
        t = PriceTracker()
        base_ts = int(time.time() * 1000)

        t.update(100_000.0, base_ts)
        t.update_oracle(99_950.0, base_ts - 3_000)

        assert t.oracle_divergence_pct > 0
        assert abs(t.oracle_divergence_pct - 0.0005) < 0.001

    def test_oracle_lag_seconds(self):
        t = PriceTracker()
        base_ts = int(time.time() * 1000)

        t.update(100_000.0, base_ts)
        t.update_oracle(100_000.0, base_ts - 5_000)

        assert t.oracle_lag_seconds == 5.0

    def test_trend_consistent(self):
        t = PriceTracker(window_seconds=60)
        base_ts = int(time.time() * 1000)

        # Consistent uptrend
        for i in range(10):
            t.update(100_000.0 + i * 10, base_ts + i * 5000)

        assert t.trend_consistent is True

    def test_trend_inconsistent(self):
        t = PriceTracker(window_seconds=60)
        base_ts = int(time.time() * 1000)

        # Up then down
        t.update(100.0, base_ts)
        t.update(110.0, base_ts + 10_000)
        t.update(105.0, base_ts + 20_000)
        t.update(95.0, base_ts + 30_000)

        assert t.trend_consistent is False
