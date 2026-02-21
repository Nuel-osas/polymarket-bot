"""Binance WebSocket feed for BTC/USDT trades."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosedError

from config.settings import settings

log = logging.getLogger(__name__)


async def binance_btc_trades(
    url: str = settings.binance_ws_url,
    max_retries: int = 10,
) -> AsyncIterator[tuple[float, int]]:
    """Yield (price, timestamp_ms) from Binance btcusdt@trade stream.

    Reconnects automatically on disconnect with exponential backoff.
    """
    retry = 0
    while retry < max_retries:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                log.info("Connected to Binance WS")
                retry = 0
                async for raw in ws:
                    msg = json.loads(raw)
                    price = float(msg["p"])
                    ts_ms = int(msg["T"])
                    yield (price, ts_ms)
        except (ConnectionClosedError, asyncio.CancelledError):
            raise
        except Exception as exc:
            retry += 1
            wait = min(2**retry, 30)
            log.warning("Binance WS error (%s), reconnect in %ds", exc, wait)
            await asyncio.sleep(wait)

    log.error("Binance WS max retries reached")
