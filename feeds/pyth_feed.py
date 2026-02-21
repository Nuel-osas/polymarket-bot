"""Fetch BTC/USD price from Pyth Network via Hermes API."""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)

# Pyth BTC/USD price feed ID
BTC_USD_FEED_ID = (
    "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"
)

HERMES_URL = "https://hermes.pyth.network/v2/updates/price/latest"


async def fetch_pyth_price(
    session: aiohttp.ClientSession,
) -> Optional[tuple[float, int]]:
    """Fetch latest BTC/USD price from Pyth Hermes.

    Returns (price, timestamp_ms) or None on failure.
    """
    try:
        params = {"ids[]": BTC_USD_FEED_ID, "parsed": "true"}
        async with session.get(HERMES_URL, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status != 200:
                log.warning("Pyth Hermes returned %d", resp.status)
                return None
            data = await resp.json()

        parsed = data.get("parsed", [])
        if not parsed:
            return None

        price_data = parsed[0].get("price", {})
        raw_price = int(price_data["price"])
        expo = int(price_data["expo"])
        publish_time = int(price_data["publish_time"])

        price = raw_price * (10 ** expo)
        ts_ms = publish_time * 1000

        return (price, ts_ms)

    except Exception as exc:
        log.warning("Pyth fetch failed: %s", exc)
        return None
