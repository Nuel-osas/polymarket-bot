"""Multi-factor signal detection for BTC Up/Down markets."""

from __future__ import annotations

import time
from typing import Optional

from config.settings import settings
from core.types import MarketInfo, Side, Signal
from feeds.price_tracker import PriceTracker


class SignalDetector:
    """Evaluates whether conditions are met to trade a 5-min BTC market.

    All 4 gates must pass, then a confidence score determines trade viability.
    """

    def evaluate(
        self,
        tracker: PriceTracker,
        market: MarketInfo,
    ) -> Optional[Signal]:
        """Return a Signal if all gates pass and confidence >= threshold."""
        now = time.time()
        elapsed = now - market.window_start

        # Gate 1: Timing — must be within entry window
        if not (settings.entry_min_seconds <= elapsed <= settings.entry_max_seconds):
            return None

        # Gate 2: Momentum — BTC must have moved > threshold
        momentum = tracker.momentum_pct
        abs_momentum = abs(momentum)
        if abs_momentum < settings.momentum_threshold:
            return None

        # Determine direction
        side = Side.UP if momentum > 0 else Side.DOWN

        # Gate 3: Oracle lag — Chainlink must diverge or be stale
        oracle_div = tracker.oracle_divergence_pct
        oracle_lag_s = tracker.oracle_lag_seconds
        oracle_lagging = (
            oracle_div > settings.oracle_lag_threshold or oracle_lag_s > 2.0
        )
        if not oracle_lagging:
            return None

        # Gate 4: Market price — target side must be ≤ max entry price
        target_price = market.price_for(side)
        if target_price > settings.max_entry_price:
            return None

        # All gates passed — compute confidence
        confidence = self._compute_confidence(
            abs_momentum, oracle_div, oracle_lag_s, target_price, tracker
        )

        if confidence < settings.min_confidence:
            return None

        return Signal(
            side=side,
            confidence=confidence,
            momentum_pct=momentum,
            oracle_lag_pct=oracle_div,
            oracle_lag_seconds=oracle_lag_s,
            target_price=target_price,
            binance_price=tracker.latest_price,
            window_elapsed_seconds=elapsed,
        )

    def _compute_confidence(
        self,
        abs_momentum: float,
        oracle_div: float,
        oracle_lag_s: float,
        target_price: float,
        tracker: PriceTracker,
    ) -> float:
        """Score from 0.50 to 0.95 based on signal quality."""
        score = 0.50

        # Strong momentum bonus (+0.15)
        if abs_momentum > settings.momentum_threshold * 2:
            score += 0.15
        elif abs_momentum > settings.momentum_threshold * 1.5:
            score += 0.10

        # Deep oracle lag bonus (+0.10)
        if oracle_div > settings.oracle_lag_threshold * 2 or oracle_lag_s > 4.0:
            score += 0.10
        elif oracle_div > settings.oracle_lag_threshold * 1.3:
            score += 0.05

        # Good price bonus (+0.10) — lower price = higher EV
        if target_price <= 0.40:
            score += 0.10
        elif target_price <= 0.48:
            score += 0.06

        # Consistent trend bonus (+0.10)
        if tracker.trend_consistent:
            score += 0.10

        return min(score, 0.95)
