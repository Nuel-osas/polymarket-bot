"""Discover current Polymarket 5-min BTC Up/Down markets via Gamma API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

import aiohttp

from config.settings import settings
from core.types import MarketInfo

log = logging.getLogger(__name__)


def _current_slug() -> str:
    """Compute the deterministic slug for the current 5-min window."""
    ts = (int(time.time()) // settings.window_seconds) * settings.window_seconds
    return f"btc-updown-5m-{ts}"


async def find_current_market(
    session: aiohttp.ClientSession,
) -> Optional[MarketInfo]:
    """Find the active 5-min BTC Up/Down market for the current window."""
    slug = _current_slug()

    try:
        # Method 1: Direct slug lookup via events endpoint
        async with session.get(
            f"{settings.gamma_host}/events",
            params={"slug": slug},
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data:
                    event = data[0] if isinstance(data, list) else data
                    markets = event.get("markets", [])
                    if markets:
                        info = _parse_market(markets[0])
                        if info:
                            return info

        # Method 2: Fallback to slug_contains search on markets endpoint
        async with session.get(
            f"{settings.gamma_host}/markets",
            params={
                "active": "true",
                "closed": "false",
                "slug_contains": "btc-updown-5m",
                "limit": "5",
                "order": "endDate",
                "ascending": "false",
            },
        ) as resp:
            if resp.status != 200:
                log.warning("Gamma API returned %d", resp.status)
                return None
            markets = await resp.json()

        if not markets:
            log.debug("No active 5-min BTC markets found")
            return None

        now = int(time.time())
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
        up_price_resp = await asyncio.to_thread(
            clob_client.get_price, market.up_token_id, "BUY"
        )
        down_price_resp = await asyncio.to_thread(
            clob_client.get_price, market.down_token_id, "BUY"
        )

        market.up_price = _parse_price(up_price_resp)
        market.down_price = _parse_price(down_price_resp)

        tick_resp = await asyncio.to_thread(
            clob_client.get_tick_size, market.up_token_id
        )
        market.tick_size = str(tick_resp) if tick_resp else "0.01"

    except Exception as exc:
        log.warning("Failed to refresh prices: %s", exc)

    return market


def _parse_price(resp) -> float:
    """Extract a float price from the SDK's get_price() response."""
    if isinstance(resp, dict):
        return float(resp.get("price", 0.50))
    return float(resp)


def _parse_market(data: dict) -> Optional[MarketInfo]:
    """Parse a Gamma API market response into MarketInfo."""
    try:
        # Extract token IDs — try tokens array first, then clobTokenIds
        tokens = data.get("tokens", [])
        clob_ids = data.get("clobTokenIds", [])

        # clobTokenIds might be a JSON string
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except (json.JSONDecodeError, TypeError):
                clob_ids = []

        if len(tokens) >= 2:
            up_tok = None
            down_tok = None
            for tok in tokens:
                outcome = tok.get("outcome", "").lower()
                if "up" in outcome or "yes" in outcome:
                    up_tok = tok
                elif "down" in outcome or "no" in outcome:
                    down_tok = tok

            if not up_tok or not down_tok:
                up_tok = tokens[0]
                down_tok = tokens[1]

            up_token = up_tok.get("token_id", up_tok.get("tokenId", ""))
            down_token = down_tok.get("token_id", down_tok.get("tokenId", ""))
            up_price = float(up_tok.get("price", 0.50))
            down_price = float(down_tok.get("price", 0.50))
        elif len(clob_ids) >= 2:
            up_token = str(clob_ids[0])
            down_token = str(clob_ids[1])
            # Try to get prices from outcomePrices field
            outcome_prices = data.get("outcomePrices", "")
            if isinstance(outcome_prices, str) and outcome_prices:
                try:
                    prices = json.loads(outcome_prices)
                    up_price = float(prices[0]) if len(prices) > 0 else 0.50
                    down_price = float(prices[1]) if len(prices) > 1 else 0.50
                except (json.JSONDecodeError, TypeError, IndexError):
                    up_price = 0.50
                    down_price = 0.50
            elif isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                up_price = float(outcome_prices[0])
                down_price = float(outcome_prices[1])
            else:
                up_price = 0.50
                down_price = 0.50
        else:
            return None

        # Parse timing from endDate or slug
        end_date = data.get("endDate", "")
        condition_id = data.get("conditionId", data.get("condition_id", ""))

        end_epoch = 0
        if end_date:
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_epoch = int(dt.timestamp())
            except (ValueError, TypeError):
                pass

        # Try parsing timestamp from slug (btc-updown-5m-{ts})
        if end_epoch == 0:
            slug = data.get("slug", "")
            parts = slug.rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                end_epoch = int(parts[1]) + settings.window_seconds

        if end_epoch == 0:
            now = int(time.time())
            end_epoch = ((now // settings.window_seconds) + 1) * settings.window_seconds

        window_start = end_epoch - settings.window_seconds
        window_end = end_epoch

        neg_risk = bool(data.get("negRisk", False))
        tick_size = str(data.get("minimumTickSize", data.get("orderPriceMinTickSize", "0.01")))

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
