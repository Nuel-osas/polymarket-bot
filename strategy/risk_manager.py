"""Risk management: stop-loss, streak limits, drawdown protection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from config.settings import settings
from core.types import BotStats


@dataclass
class RiskState:
    cooldown_until: float = 0.0
    day_start_ts: float = field(default_factory=time.time)


class RiskManager:
    """Enforce risk rules before allowing a trade."""

    def __init__(self) -> None:
        self._state = RiskState()

    def can_trade(self, stats: BotStats) -> tuple[bool, str]:
        """Return (allowed, reason) for the current state.

        Rules checked in order:
        1. Target reached → STOP
        2. Balance below stop-loss → PAUSE
        3. Max consecutive losses → STOP
        4. Cooldown losses → COOLDOWN
        5. Daily drawdown → STOP
        """
        # Target reached
        if stats.current_balance >= settings.target_balance:
            return False, "target_reached"

        # Stop-loss
        if stats.current_balance < settings.stop_loss_balance:
            return False, "stop_loss"

        # Hard stop: max consecutive losses
        if stats.consecutive_losses >= settings.max_consecutive_losses:
            return False, "max_losses"

        # Cooldown after N consecutive losses
        if stats.consecutive_losses >= settings.cooldown_losses:
            now = time.time()
            if self._state.cooldown_until == 0:
                self._state.cooldown_until = (
                    now + settings.cooldown_minutes * 60
                )
            if now < self._state.cooldown_until:
                remaining = int(self._state.cooldown_until - now)
                return False, f"cooldown_{remaining}s"
            # Cooldown expired — reset
            self._state.cooldown_until = 0.0

        # Daily drawdown check
        self._maybe_reset_day(stats)
        if stats.day_start_balance > 0:
            drawdown = 1.0 - (stats.current_balance / stats.day_start_balance)
            if drawdown >= settings.daily_drawdown_limit:
                return False, "daily_drawdown"

        return True, "ok"

    def record_win(self, stats: BotStats) -> None:
        """Update stats after a winning trade."""
        stats.wins += 1
        stats.total_trades += 1
        stats.consecutive_losses = 0
        stats.peak_balance = max(stats.peak_balance, stats.current_balance)
        self._state.cooldown_until = 0.0

    def record_loss(self, stats: BotStats) -> None:
        """Update stats after a losing trade."""
        stats.losses += 1
        stats.total_trades += 1
        stats.consecutive_losses += 1

    def _maybe_reset_day(self, stats: BotStats) -> None:
        """Reset daily tracking at midnight."""
        now = time.time()
        # Simple 24h rolling window
        if now - self._state.day_start_ts > 86400:
            stats.day_start_balance = stats.current_balance
            self._state.day_start_ts = now
