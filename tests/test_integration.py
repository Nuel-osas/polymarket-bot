"""Integration dry-run test with mocked feeds."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.orchestrator import Orchestrator
from core.state_machine import StateMachine
from core.types import BotState, BotStats, MarketInfo, Side, Signal
from feeds.price_tracker import PriceTracker
from strategy.signal_detector import SignalDetector
from strategy.position_sizer import PositionSizer
from strategy.risk_manager import RiskManager


def _make_market() -> MarketInfo:
    now = int(time.time())
    ws = (now // 300) * 300
    return MarketInfo(
        condition_id="integration_test_cond",
        question="BTC up or down?",
        up_token_id="up_tok",
        down_token_id="down_tok",
        up_price=0.48,
        down_price=0.52,
        window_start=ws,
        window_end=ws + 300,
    )


class TestStateMachine:
    def test_valid_transitions(self):
        sm = StateMachine()
        assert sm.state == BotState.SCANNING
        assert sm.transition(BotState.SIGNAL)
        assert sm.state == BotState.SIGNAL
        assert sm.transition(BotState.TRADING)
        assert sm.state == BotState.TRADING
        assert sm.transition(BotState.WAITING)
        assert sm.state == BotState.WAITING
        assert sm.transition(BotState.COMPOUNDING)
        assert sm.state == BotState.COMPOUNDING
        assert sm.transition(BotState.SCANNING)
        assert sm.state == BotState.SCANNING

    def test_invalid_transition(self):
        sm = StateMachine()
        assert not sm.transition(BotState.COMPOUNDING)
        assert sm.state == BotState.SCANNING  # unchanged

    def test_stopped_is_terminal(self):
        sm = StateMachine()
        sm.transition(BotState.STOPPED)
        assert not sm.is_active()
        assert not sm.transition(BotState.SCANNING)


class TestRiskManager:
    def test_can_trade_normal(self):
        rm = RiskManager()
        stats = BotStats(current_balance=80.0, day_start_balance=100.0)
        ok, reason = rm.can_trade(stats)
        assert ok
        assert reason == "ok"

    def test_stop_loss(self):
        rm = RiskManager()
        stats = BotStats(current_balance=5.0, day_start_balance=20.0)
        ok, reason = rm.can_trade(stats)
        assert not ok
        assert reason == "stop_loss"

    def test_max_consecutive_losses(self):
        rm = RiskManager()
        stats = BotStats(
            current_balance=50.0,
            consecutive_losses=3,
            day_start_balance=100.0,
        )
        ok, reason = rm.can_trade(stats)
        assert not ok
        assert reason == "max_losses"

    def test_daily_drawdown(self):
        rm = RiskManager()
        stats = BotStats(current_balance=40.0, day_start_balance=100.0)
        ok, reason = rm.can_trade(stats)
        assert not ok
        assert reason == "daily_drawdown"

    def test_win_resets_streak(self):
        rm = RiskManager()
        stats = BotStats(
            current_balance=100.0,
            consecutive_losses=1,
            day_start_balance=100.0,
        )
        rm.record_win(stats)
        assert stats.consecutive_losses == 0
        assert stats.wins == 1


class TestEndToEndDryRun:
    """Simulate a complete signal→trade→resolution cycle."""

    def test_full_cycle_win(self):
        """Simulate: detect signal → size position → check risk → dry-run trade."""
        stats = BotStats(
            current_balance=20.0,
            peak_balance=20.0,
            day_start_balance=20.0,
        )

        # Build price data showing strong upward momentum
        tracker = PriceTracker(window_seconds=60)
        base_ts = int(time.time() * 1000)
        for i in range(20):
            price = 100_000.0 + i * 15  # strong up
            tracker.update(price, base_ts + i * 3000)
        tracker.update_oracle(100_000.0, base_ts)  # oracle stuck at start

        market = _make_market()
        # Adjust window so we're 60s in
        market.window_start = int(time.time()) - 60
        market.window_end = market.window_start + 300
        market.up_price = 0.45

        # Detect signal
        detector = SignalDetector()
        signal = detector.evaluate(tracker, market)
        assert signal is not None
        assert signal.side == Side.UP

        # Size position
        sizer = PositionSizer()
        amount = sizer.compute(stats)
        assert amount == 20.0

        # Risk check
        risk = RiskManager()
        ok, reason = risk.can_trade(stats)
        assert ok

        # Simulate win
        payout = amount / market.up_price  # shares bought
        profit = payout - amount
        stats.current_balance += profit
        risk.record_win(stats)

        assert stats.current_balance > 20.0
        assert stats.wins == 1
        assert stats.consecutive_losses == 0

    def test_full_cycle_loss(self):
        """Simulate a losing trade."""
        stats = BotStats(
            current_balance=20.0,
            peak_balance=20.0,
            day_start_balance=20.0,
        )

        amount = 20.0
        stats.current_balance -= amount

        risk = RiskManager()
        risk.record_loss(stats)

        assert stats.current_balance == 0.0
        assert stats.losses == 1
        assert stats.consecutive_losses == 1
