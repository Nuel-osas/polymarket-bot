"""Execute trades on Polymarket CLOB."""

from __future__ import annotations

import asyncio
import logging

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

from config.settings import settings
from core.types import MarketInfo, Side, Signal, TradeResult

log = logging.getLogger(__name__)

# Maximum slippage above the target price we'll tolerate
_SLIPPAGE_MARGIN = 0.05


async def execute_trade(
    client: ClobClient,
    market: MarketInfo,
    signal: Signal,
    amount_usdc: float,
) -> TradeResult:
    """Place a FOK market buy order for the signal's side.

    Returns TradeResult with success/failure info.
    """
    token_id = market.token_id_for(signal.side)
    price = market.price_for(signal.side)

    if settings.dry_run:
        log.info(
            "[DRY RUN] Would buy $%.2f of %s at %.4f (conf=%.2f)",
            amount_usdc,
            signal.side.value,
            price,
            signal.confidence,
        )
        return TradeResult(
            success=True,
            side=signal.side,
            amount_usdc=amount_usdc,
            price=price,
            confidence=signal.confidence,
            market_condition_id=market.condition_id,
            order_id="dry_run",
            dry_run=True,
        )

    try:
        # Slippage protection: worst price we'll accept
        max_price = min(price + _SLIPPAGE_MARGIN, 0.99)

        order_args = MarketOrderArgs(
            token_id=token_id,
            amount=amount_usdc,
            side=BUY,
            price=max_price,
        )

        # tick_size and neg_risk are required in order options
        order_options = {
            "tick_size": market.tick_size,
            "neg_risk": market.neg_risk,
        }

        # py_clob_client methods are synchronous — run in thread
        # to avoid blocking the asyncio event loop
        signed_order = await asyncio.to_thread(
            client.create_market_order, order_args, order_options
        )
        resp = await asyncio.to_thread(
            client.post_order, signed_order, OrderType.FOK
        )

        order_id = ""
        success = False

        if isinstance(resp, dict):
            order_id = resp.get("orderID", resp.get("id", ""))
            status = resp.get("status", "")
            success = status in ("matched", "filled", "live")
            if not success:
                log.warning("Order status: %s — %s", status, resp)
        else:
            order_id = str(resp)
            success = True

        log.info(
            "Trade %s: %s $%.2f at %.4f (max=%.4f) — order=%s",
            "OK" if success else "FAIL",
            signal.side.value,
            amount_usdc,
            price,
            max_price,
            order_id,
        )

        return TradeResult(
            success=success,
            side=signal.side,
            amount_usdc=amount_usdc,
            price=price,
            confidence=signal.confidence,
            market_condition_id=market.condition_id,
            order_id=order_id,
        )

    except Exception as exc:
        log.error("Trade execution failed: %s", exc)
        return TradeResult(
            success=False,
            side=signal.side,
            amount_usdc=amount_usdc,
            price=price,
            confidence=signal.confidence,
            market_condition_id=market.condition_id,
            error=str(exc),
        )
