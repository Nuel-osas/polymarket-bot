"""Compounding position sizer with liquidity-aware scaling."""

from __future__ import annotations

from config.settings import settings
from core.types import BotStats


class PositionSizer:
    """Determine bet size based on balance tier and order book depth.

    Compounding table:
        Balance < $320   → 100% of balance
        $320 – $2.2K     → 90%
        $2.2K – $12.8K   → 80%
        $12.8K – $63K    → 70%
        $63K+            → 60%

    Capped at max_book_depth_fraction of available liquidity.
    """

    # (upper_bound, fraction)
    _TIERS = [
        (320.0, 1.00),
        (2_200.0, 0.90),
        (12_800.0, 0.80),
        (63_000.0, 0.70),
        (float("inf"), 0.60),
    ]

    def compute(
        self,
        stats: BotStats,
        order_book_depth_usdc: float = float("inf"),
    ) -> float:
        """Return the USDC amount to bet.

        Args:
            stats: Current bot stats (uses current_balance).
            order_book_depth_usdc: Sum of available liquidity on the target
                side of the order book (in USDC).

        Returns:
            Amount in USDC to place as a market order.
        """
        balance = stats.current_balance

        if balance <= 0:
            return 0.0

        # Find tier fraction
        fraction = self._TIERS[-1][1]
        for upper, frac in self._TIERS:
            if balance < upper:
                fraction = frac
                break

        amount = balance * fraction

        # Cap at order book depth
        depth_cap = order_book_depth_usdc * settings.max_book_depth_fraction
        amount = min(amount, depth_cap)

        # Floor at $1 minimum viable trade
        if amount < 1.0:
            return 0.0

        return round(amount, 2)
