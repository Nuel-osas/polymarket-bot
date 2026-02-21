"""Tests for strategy.position_sizer."""

from core.types import BotStats
from strategy.position_sizer import PositionSizer


class TestPositionSizer:
    def test_small_balance_full_bet(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=20.0)

        amount = sizer.compute(stats)
        assert amount == 20.0  # 100% at < $320

    def test_tier_two(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=500.0)

        amount = sizer.compute(stats)
        assert amount == 450.0  # 90% of $500

    def test_tier_three(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=5000.0)

        amount = sizer.compute(stats)
        assert amount == 4000.0  # 80% of $5000

    def test_tier_four(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=20_000.0)

        amount = sizer.compute(stats)
        assert amount == 14_000.0  # 70% of $20K

    def test_tier_five(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=80_000.0)

        amount = sizer.compute(stats)
        assert amount == 48_000.0  # 60% of $80K

    def test_liquidity_cap(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=1000.0)

        # Order book only has $500 total depth
        amount = sizer.compute(stats, order_book_depth_usdc=500.0)
        # 30% of $500 = $150
        assert amount == 150.0

    def test_zero_balance(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=0.0)

        amount = sizer.compute(stats)
        assert amount == 0.0

    def test_tiny_balance(self):
        sizer = PositionSizer()
        stats = BotStats(current_balance=0.50)

        amount = sizer.compute(stats)
        assert amount == 0.0  # Below $1 minimum
