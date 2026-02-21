"""Rolling price window, momentum calculation, and oracle lag tracking."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class PriceSnapshot:
    price: float
    timestamp_ms: int


class PriceTracker:
    """Tracks Binance BTC prices over a rolling window and computes momentum."""

    def __init__(self, window_seconds: int = 60):
        self._window_ms = window_seconds * 1000
        self._prices: deque[PriceSnapshot] = deque()
        self.latest_price: float = 0.0
        self.latest_ts_ms: int = 0

        # Chainlink / oracle tracking
        self._oracle_price: float = 0.0
        self._oracle_ts_ms: int = 0

    def update(self, price: float, ts_ms: int) -> None:
        """Add a new Binance price tick."""
        self._prices.append(PriceSnapshot(price, ts_ms))
        self.latest_price = price
        self.latest_ts_ms = ts_ms
        self._evict()

    def update_oracle(self, price: float, ts_ms: int) -> None:
        """Update the last known oracle (Chainlink) price."""
        self._oracle_price = price
        self._oracle_ts_ms = ts_ms

    @property
    def momentum_pct(self) -> float:
        """Percentage price change over the rolling window.

        Positive = price going up, negative = going down.
        """
        if len(self._prices) < 2:
            return 0.0
        oldest = self._prices[0].price
        if oldest == 0:
            return 0.0
        return (self.latest_price - oldest) / oldest

    @property
    def oracle_divergence_pct(self) -> float:
        """Absolute % divergence between Binance and oracle price."""
        if self._oracle_price == 0 or self.latest_price == 0:
            return 0.0
        return abs(self.latest_price - self._oracle_price) / self._oracle_price

    @property
    def oracle_lag_seconds(self) -> float:
        """Seconds since last oracle update (relative to Binance feed time)."""
        if self._oracle_ts_ms == 0 or self.latest_ts_ms == 0:
            return 0.0
        return max(0, (self.latest_ts_ms - self._oracle_ts_ms) / 1000.0)

    @property
    def trend_consistent(self) -> bool:
        """Check if price has moved consistently in one direction.

        Splits the window into two halves and checks that both halves
        moved in the same direction.
        """
        if len(self._prices) < 4:
            return False
        mid = len(self._prices) // 2
        first_half = list(self._prices)[:mid]
        second_half = list(self._prices)[mid:]

        delta1 = first_half[-1].price - first_half[0].price
        delta2 = second_half[-1].price - second_half[0].price
        # Same sign and both nonzero
        return delta1 * delta2 > 0

    @property
    def window_size(self) -> int:
        return len(self._prices)

    def _evict(self) -> None:
        cutoff = self.latest_ts_ms - self._window_ms
        while self._prices and self._prices[0].timestamp_ms < cutoff:
            self._prices.popleft()
