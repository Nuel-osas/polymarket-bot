"""Main async orchestrator wiring all bot components together."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Optional

import aiohttp

from config.settings import settings
from core.state_machine import StateMachine
from core.types import BotState, BotStats, MarketInfo, Side, Signal
from feeds.binance_ws import binance_btc_trades
from feeds.price_tracker import PriceTracker
from feeds.pyth_feed import fetch_pyth_price
from market.discovery import find_current_market, get_market_prices
from market.resolver import poll_resolution
from persistence.ledger import Ledger
from strategy.position_sizer import PositionSizer
from strategy.risk_manager import RiskManager
from strategy.signal_detector import SignalDetector
from trading.executor import execute_trade
from api.server import start_api_server

log = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the 5 async tasks: feed, discovery, main loop, heartbeat, logging."""

    def __init__(self) -> None:
        self.sm = StateMachine()
        self.stats = BotStats(
            current_balance=settings.initial_balance,
            peak_balance=settings.initial_balance,
            day_start_balance=settings.initial_balance,
        )
        self.tracker = PriceTracker(settings.price_window_seconds)
        self.detector = SignalDetector()
        self.sizer = PositionSizer()
        self.risk = RiskManager()
        self.ledger = Ledger()

        self._current_market: Optional[MarketInfo] = None
        self._pending_trade: Optional[dict] = None  # condition_id → trade info
        self._clob_client = None
        self._shutdown = asyncio.Event()
        self._start_time: float = time.time()

    async def run(self) -> None:
        """Start all tasks and run until shutdown."""
        logging.basicConfig(
            level=getattr(logging, settings.log_level),
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )

        log.info(
            "Starting polybot — DRY_RUN=%s balance=$%.2f",
            settings.dry_run,
            self.stats.current_balance,
        )

        # Initialize trading client (skip in dry-run if no key)
        if not settings.dry_run:
            from trading.auth import create_clob_client
            self._clob_client = create_clob_client()
        elif settings.poly_private_key:
            try:
                from trading.auth import create_clob_client
                self._clob_client = create_clob_client()
                log.info("CLOB client ready (dry-run mode, will read order books)")
            except Exception as exc:
                log.info("No CLOB client in dry-run: %s", exc)

        await self.ledger.init()
        await self.ledger.log_balance(self.stats.current_balance, "start")

        # Start API server
        api_runner = await start_api_server(self)
        log.info("API server started on http://0.0.0.0:8899")

        async with aiohttp.ClientSession() as session:
            tasks = [
                asyncio.create_task(self._feed_task(), name="feed"),
                asyncio.create_task(self._oracle_task(session), name="oracle"),
                asyncio.create_task(self._discovery_task(session), name="discovery"),
                asyncio.create_task(self._main_loop(session), name="main"),
                asyncio.create_task(self._heartbeat_task(), name="heartbeat"),
            ]

            try:
                await self._shutdown.wait()
            except (KeyboardInterrupt, asyncio.CancelledError):
                log.info("Shutdown requested")
            finally:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await api_runner.cleanup()
                await self.ledger.close()
                log.info("Bot stopped. Final balance: $%.2f", self.stats.current_balance)

    # ─── Async Tasks ───────────────────────────────────────────

    async def _feed_task(self) -> None:
        """Consume Binance WebSocket and update price tracker."""
        try:
            async for price, ts_ms in binance_btc_trades():
                self.tracker.update(price, ts_ms)
        except asyncio.CancelledError:
            return

    async def _oracle_task(self, session: aiohttp.ClientSession) -> None:
        """Poll Pyth Network for BTC/USD oracle price."""
        try:
            while not self._shutdown.is_set():
                result = await fetch_pyth_price(session)
                if result:
                    price, ts_ms = result
                    self.tracker.update_oracle(price, ts_ms)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return

    async def _discovery_task(self, session: aiohttp.ClientSession) -> None:
        """Continuously discover the current 5-min market."""
        try:
            while not self._shutdown.is_set():
                market = await find_current_market(session)
                if market:
                    if self._clob_client:
                        market = await get_market_prices(
                            session, market, self._clob_client
                        )
                    self._current_market = market
                await asyncio.sleep(settings.market_poll_interval)
        except asyncio.CancelledError:
            return

    async def _main_loop(self, session: aiohttp.ClientSession) -> None:
        """Core state-machine loop: detect signals, execute trades, resolve."""
        try:
            while not self._shutdown.is_set():
                await asyncio.sleep(0.5)

                if not self.sm.is_active():
                    if self.sm.state == BotState.STOPPED:
                        self._shutdown.set()
                        return
                    continue

                state = self.sm.state

                if state == BotState.SCANNING:
                    await self._handle_scanning()

                elif state == BotState.SIGNAL:
                    await self._handle_signal(session)

                elif state == BotState.WAITING:
                    await self._handle_waiting(session)

                elif state == BotState.COMPOUNDING:
                    await self._handle_compounding()

                elif state == BotState.COOLDOWN:
                    # Cooldown is handled by risk_manager.can_trade
                    allowed, reason = self.risk.can_trade(self.stats)
                    if allowed:
                        self.sm.transition(BotState.SCANNING)
                    elif "cooldown" not in reason:
                        self.sm.transition(BotState.STOPPED)
                        log.error("Stopped during cooldown: %s", reason)
                    else:
                        await asyncio.sleep(5)

        except asyncio.CancelledError:
            return

    async def _heartbeat_task(self) -> None:
        """Periodic status logging."""
        try:
            while not self._shutdown.is_set():
                await asyncio.sleep(settings.heartbeat_interval)
                win_rate = (
                    self.stats.wins / self.stats.total_trades * 100
                    if self.stats.total_trades
                    else 0
                )
                log.info(
                    "HEARTBEAT state=%s bal=$%.2f trades=%d W/L=%d/%d (%.0f%%) "
                    "signals=%d price=$%.2f pyth=$%.2f lag=%.1fs",
                    self.sm.state.value,
                    self.stats.current_balance,
                    self.stats.total_trades,
                    self.stats.wins,
                    self.stats.losses,
                    win_rate,
                    self.stats.total_signals,
                    self.tracker.latest_price,
                    self.tracker._oracle_price,
                    self.tracker.oracle_lag_seconds,
                )
        except asyncio.CancelledError:
            return

    # ─── State Handlers ────────────────────────────────────────

    async def _handle_scanning(self) -> None:
        """Look for a trade signal."""
        market = self._current_market
        if not market or not market.active:
            return
        if self.tracker.latest_price == 0:
            return

        # Check risk rules first
        allowed, reason = self.risk.can_trade(self.stats)
        if not allowed:
            if reason == "target_reached":
                log.info("TARGET REACHED! $%.2f", self.stats.current_balance)
                self.sm.transition(BotState.STOPPED)
            elif reason in ("stop_loss", "max_losses", "daily_drawdown"):
                log.warning("Risk stop: %s", reason)
                self.sm.transition(BotState.STOPPED)
            elif "cooldown" in reason:
                self.sm.transition(BotState.COOLDOWN)
            return

        signal = self.detector.evaluate(self.tracker, market)
        if signal:
            self.stats.total_signals += 1
            log.info(
                "SIGNAL: %s conf=%.2f mom=%.4f%% lag=%.4f%% price=%.3f elapsed=%.0fs",
                signal.side.value,
                signal.confidence,
                signal.momentum_pct * 100,
                signal.oracle_lag_pct * 100,
                signal.target_price,
                signal.window_elapsed_seconds,
            )
            self._pending_signal = signal
            self.sm.transition(BotState.SIGNAL)

    async def _handle_signal(self, session: aiohttp.ClientSession) -> None:
        """Execute trade for the detected signal."""
        signal = getattr(self, "_pending_signal", None)
        market = self._current_market

        if not signal or not market:
            self.sm.transition(BotState.SCANNING)
            return

        self.sm.transition(BotState.TRADING)

        # Size the position
        amount = self.sizer.compute(self.stats)
        if amount <= 0:
            log.warning("Position sizer returned 0, skipping")
            self.sm.transition(BotState.SCANNING)
            return

        # Execute
        result = await execute_trade(
            self._clob_client, market, signal, amount
        )
        await self.ledger.log_trade(result)
        self.stats.signals_traded += 1

        if result.success:
            self._pending_trade = {
                "condition_id": market.condition_id,
                "side": signal.side,
                "amount": amount,
                "expected_payout": result.expected_payout,
            }
            self.sm.transition(BotState.WAITING)
        else:
            log.warning("Trade failed: %s", result.error)
            self.sm.transition(BotState.SCANNING)

    async def _handle_waiting(self, session: aiohttp.ClientSession) -> None:
        """Wait for market resolution."""
        trade_info = self._pending_trade
        market = self._current_market

        if not trade_info or not market:
            self.sm.transition(BotState.SCANNING)
            return

        result = await poll_resolution(session, market)

        if not result.resolved:
            await asyncio.sleep(settings.resolution_poll_interval)
            return

        bet_side = trade_info["side"]
        amount = trade_info["amount"]
        payout = trade_info["expected_payout"]

        if result.winning_side == bet_side:
            # WIN
            profit = payout - amount
            self.stats.current_balance += profit
            self.risk.record_win(self.stats)
            await self.ledger.update_outcome(
                trade_info["condition_id"], "win", payout
            )
            await self.ledger.log_balance(self.stats.current_balance, "win")
            log.info(
                "WIN! %s — profit=$%.2f → balance=$%.2f",
                bet_side.value,
                profit,
                self.stats.current_balance,
            )
        else:
            # LOSS
            self.stats.current_balance -= amount
            self.risk.record_loss(self.stats)
            await self.ledger.update_outcome(
                trade_info["condition_id"], "loss", 0
            )
            await self.ledger.log_balance(self.stats.current_balance, "loss")
            log.warning(
                "LOSS %s — lost=$%.2f → balance=$%.2f",
                bet_side.value,
                amount,
                self.stats.current_balance,
            )

        self._pending_trade = None
        self.sm.transition(BotState.COMPOUNDING)

    async def _handle_compounding(self) -> None:
        """Post-trade: update stats and return to scanning."""
        ledger_stats = await self.ledger.get_stats()
        log.info(
            "Ledger: %d trades, %d wins, %d losses, %.0f%% win rate",
            ledger_stats["total_trades"],
            ledger_stats["wins"],
            ledger_stats["losses"],
            ledger_stats["win_rate"],
        )
        self.sm.transition(BotState.SCANNING)


def main() -> None:
    """Entry point."""
    bot = Orchestrator()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nShutdown.")


if __name__ == "__main__":
    main()
