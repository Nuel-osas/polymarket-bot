"""Discover current Polymarket 5-min BTC Up/Down markets via Gamma API."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from config.settings import settings
from core.types import MarketInfo

log = logging.getLogger(__name__)

# Gamma API returns markets matching this slug pattern
_SLUG_PREFIX = "will-the-price-of-bitcoin-be-up-or-down-5-minutes-from"


async def find_current_market(
    session: aiohttp.ClientSession,
) -> Optional[MarketInfo]:
    """Find the active 5-min BTC Up/Down market for the current window."""
    now = int(time.time())
    # Current 5-min window boundary
    window_start = (now // settings.window_seconds) * settings.window_seconds
    window_end = window_start + settings.window_seconds

    try:
        params = {
            "active": "true",
            "closed": "false",
            "slug_contains": "will-the-price-of-bitcoin-be-up-or-down-5-minutes",
            "limit": "5",
            "order": "endDate",
            "ascending": "false",
        }
        async with session.get(
            f"{settings.gamma_host}/markets", params=params
        ) as resp:
            if resp.status != 200:
                log.warning("Gamma API returned %d", resp.status)
                return None
            markets = await resp.json()

        if not markets:
            log.debug("No active 5-min BTC markets found")
            return None

        # Find the market whose window we're currently in
        for mkt in markets:
            info = _parse_market(mkt)
            if info and info.window_start <= now < info.window_end:
                return info

        # Fallback: return the most recent active market
        for mkt in markets:
            info = _parse_market(mkt)
            if info and info.active:
                return info

        return None

    except Exception as exc:
        log.error("Market discovery failed: %s", exc)
        return None


async def get_market_prices(
    session: aiohttp.ClientSession,
    market: MarketInfo,
    clob_client=None,
) -> MarketInfo:
    """Refresh order book prices and tick size for a market using CLOB client."""
    if clob_client is None:
        return market

    try:
        # get_price() returns a dict like {"price": "0.52"} or a string
        # Run in thread to avoid blocking the event loop
        up_price_resp = await asyncio.to_thread(
            clob_client.get_price, market.up_token_id, "BUY"
        )
        down_price_resp = await asyncio.to_thread(
            clob_client.get_price, market.down_token_id, "BUY"
        )

        market.up_price = _parse_price(up_price_resp)
        market.down_price = _parse_price(down_price_resp)

        # Fetch tick size for this market's token
        tick_resp = await asyncio.to_thread(
            clob_client.get_tick_size, market.up_token_id
        )
        market.tick_size = str(tick_resp) if tick_resp else "0.01"

    except Exception as exc:
        log.warning("Failed to refresh prices: %s", exc)

    return market


def _parse_price(resp) -> float:
    """Extract a float price from the SDK's get_price() response.

    The response may be a dict like {"price": "0.52"}, a string "0.52",
    or a float 0.52 depending on the SDK version.
    """
    if isinstance(resp, dict):
        return float(resp.get("price", 0.50))
    return float(resp)


def _parse_market(data: dict) -> Optional[MarketInfo]:
    """Parse a Gamma API market response into MarketInfo."""
    try:
        tokens = data.get("tokens", [])
        if len(tokens) < 2:
            # Try clobTokenIds if tokens aren't embedded
            clob_ids = data.get("clobTokenIds", [])
            if len(clob_ids) < 2:
                return None
            up_token = clob_ids[0]
            down_token = clob_ids[1]
            up_price = 0.50
            down_price = 0.50
        else:
            # Identify Up vs Down tokens
            up_tok = None
            down_tok = None
            for tok in tokens:
                outcome = tok.get("outcome", "").lower()
                if "up" in outcome or "yes" in outcome:
                    up_tok = tok
                elif "down" in outcome or "no" in outcome:
                    down_tok = tok

            if not up_tok or not down_tok:
                # Fallback: first = Up, second = Down
                up_tok = tokens[0]
                down_tok = tokens[1]

            up_token = up_tok.get("token_id", up_tok.get("tokenId", ""))
            down_token = down_tok.get("token_id", down_tok.get("tokenId", ""))
            up_price = float(up_tok.get("price", 0.50))
            down_price = float(down_tok.get("price", 0.50))

        # Parse timing from endDate or slug
        end_date = data.get("endDate", "")
        condition_id = data.get("conditionId", data.get("condition_id", ""))

        # Estimate window from end date (end = window_start + 300)
        end_epoch = 0
        if end_date:
            from datetime import datetime, timezone

            try:
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_epoch = int(dt.timestamp())
            except (ValueError, TypeError):
                pass

        if end_epoch == 0:
            now = int(time.time())
            end_epoch = ((now // 300) + 1) * 300

        window_start = end_epoch - 300
        window_end = end_epoch

        # neg_risk from Gamma API (defaults False if absent)
        neg_risk = bool(data.get("negRisk", False))

        # tick_size from Gamma API if available (refined later by CLOB client)
        tick_size = str(data.get("minimumTickSize", "0.01"))

        return MarketInfo(
            condition_id=condition_id,
            question=data.get("question", ""),
            up_token_id=up_token,
            down_token_id=down_token,
            up_price=up_price,
            down_price=down_price,
            window_start=window_start,
            window_end=window_end,
            neg_risk=neg_risk,
            active=data.get("active", True),
            tick_size=tick_size,
        )
    except Exception as exc:
        log.debug("Failed to parse market: %s", exc)
        return None
