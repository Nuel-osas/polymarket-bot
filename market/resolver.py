"""Poll Polymarket for market resolution status."""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from config.settings import settings
from core.types import MarketInfo, Side

log = logging.getLogger(__name__)


class ResolutionResult:
    __slots__ = ("resolved", "winning_side", "condition_id")

    def __init__(
        self,
        resolved: bool,
        winning_side: Optional[Side],
        condition_id: str,
    ):
        self.resolved = resolved
        self.winning_side = winning_side
        self.condition_id = condition_id


async def poll_resolution(
    session: aiohttp.ClientSession,
    market: MarketInfo,
) -> ResolutionResult:
    """Check if a market has resolved and which side won."""
    try:
        params = {"conditionId": market.condition_id}
        async with session.get(
            f"{settings.gamma_host}/markets", params=params
        ) as resp:
            if resp.status != 200:
                return ResolutionResult(False, None, market.condition_id)
            data = await resp.json()

        if not data:
            return ResolutionResult(False, None, market.condition_id)

        mkt = data[0] if isinstance(data, list) else data
        closed = mkt.get("closed", False)

        if not closed:
            return ResolutionResult(False, None, market.condition_id)

        # Primary: use explicit resolution/resolved fields from Gamma API
        winning_side = _resolve_from_fields(mkt)

        # Fallback: infer from token prices if resolution fields absent
        if winning_side is None:
            winning_side = _resolve_from_prices(mkt)

        return ResolutionResult(True, winning_side, market.condition_id)

    except Exception as exc:
        log.warning("Resolution poll error: %s", exc)
        return ResolutionResult(False, None, market.condition_id)


def _resolve_from_fields(mkt: dict) -> Optional[Side]:
    """Try to determine winner from Gamma API resolution fields."""
    # Some Gamma responses include "resolution" or "resolved_by"
    resolution = mkt.get("resolution", "")
    if resolution:
        res_lower = resolution.lower()
        if "up" in res_lower or "yes" in res_lower:
            return Side.UP
        if "down" in res_lower or "no" in res_lower:
            return Side.DOWN

    # Check per-token winner field
    tokens = mkt.get("tokens", [])
    for tok in tokens:
        winner = tok.get("winner", None)
        if winner is True or winner == "true":
            outcome = tok.get("outcome", "").lower()
            if "up" in outcome or "yes" in outcome:
                return Side.UP
            if "down" in outcome or "no" in outcome:
                return Side.DOWN

    return None


def _resolve_from_prices(mkt: dict) -> Optional[Side]:
    """Fallback: infer winner from final token prices (1.0 = winner, 0.0 = loser)."""
    tokens = mkt.get("tokens", [])
    for tok in tokens:
        price = float(tok.get("price", 0))
        outcome = tok.get("outcome", "").lower()
        if price >= 0.95:
            if "up" in outcome or "yes" in outcome:
                return Side.UP
            if "down" in outcome or "no" in outcome:
                return Side.DOWN
    return None
