"""State machine for bot lifecycle management."""

from __future__ import annotations

import logging
from typing import Optional

from core.types import BotState

log = logging.getLogger(__name__)

# Valid state transitions
_TRANSITIONS: dict[BotState, set[BotState]] = {
    BotState.SCANNING: {BotState.SIGNAL, BotState.PAUSED, BotState.STOPPED},
    BotState.SIGNAL: {BotState.TRADING, BotState.SCANNING, BotState.COOLDOWN},
    BotState.TRADING: {BotState.WAITING, BotState.SCANNING, BotState.PAUSED},
    BotState.WAITING: {BotState.COMPOUNDING, BotState.SCANNING, BotState.COOLDOWN, BotState.STOPPED},
    BotState.COMPOUNDING: {BotState.SCANNING, BotState.PAUSED, BotState.STOPPED},
    BotState.COOLDOWN: {BotState.SCANNING, BotState.STOPPED},
    BotState.PAUSED: {BotState.SCANNING, BotState.STOPPED},
    BotState.STOPPED: set(),
}


class StateMachine:
    """Manages bot state transitions with validation."""

    def __init__(self, initial: BotState = BotState.SCANNING) -> None:
        self._state = initial

    @property
    def state(self) -> BotState:
        return self._state

    def transition(self, target: BotState) -> bool:
        """Attempt to transition to target state.

        Returns True if transition was valid and applied.
        """
        allowed = _TRANSITIONS.get(self._state, set())
        if target not in allowed:
            log.warning(
                "Invalid transition %s → %s (allowed: %s)",
                self._state.value,
                target.value,
                [s.value for s in allowed],
            )
            return False

        log.info("State: %s → %s", self._state.value, target.value)
        self._state = target
        return True

    def is_active(self) -> bool:
        """Return True if bot is in an active (non-terminal) state."""
        return self._state not in (BotState.STOPPED, BotState.PAUSED)

    def reset(self) -> None:
        """Reset to SCANNING state."""
        self._state = BotState.SCANNING
