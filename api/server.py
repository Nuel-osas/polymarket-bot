"""Lightweight aiohttp API server embedded in the bot's asyncio loop."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from aiohttp import web

from config.settings import settings

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator

routes = web.RouteTableDef()

# Store bot reference on the app
_APP_KEY = web.AppKey("bot", object)


def _bot(request: web.Request) -> Orchestrator:
    return request.app[_APP_KEY]  # type: ignore[return-value]


@routes.get("/api/status")
async def handle_status(request: web.Request) -> web.Response:
    bot = _bot(request)
    s = bot.stats
    win_rate = (s.wins / s.total_trades * 100) if s.total_trades else 0.0
    uptime = time.time() - bot._start_time
    return web.json_response({
        "state": bot.sm.state.value,
        "balance": s.current_balance,
        "peak_balance": s.peak_balance,
        "total_trades": s.total_trades,
        "wins": s.wins,
        "losses": s.losses,
        "consecutive_losses": s.consecutive_losses,
        "win_rate": round(win_rate, 1),
        "total_signals": s.total_signals,
        "signals_traded": s.signals_traded,
        "dry_run": settings.dry_run,
        "uptime_seconds": round(uptime, 0),
    })


@routes.get("/api/price")
async def handle_price(request: web.Request) -> web.Response:
    bot = _bot(request)
    t = bot.tracker
    market = bot._current_market

    # Build recent price history from tracker's deque, downsampled to ~1/sec
    now_ms = t.latest_ts_ms or int(time.time() * 1000)
    cutoff = now_ms - 60_000  # last 60s
    history: list[dict] = []
    last_bucket = -1
    for snap in t._prices:
        if snap.timestamp_ms < cutoff:
            continue
        bucket = snap.timestamp_ms // 1000  # 1-second buckets
        if bucket != last_bucket:
            history.append({"price": snap.price, "ts": snap.timestamp_ms})
            last_bucket = bucket

    window_remaining = 0
    if market:
        window_remaining = max(0, market.window_end - int(time.time()))

    return web.json_response({
        "btc_price": t.latest_price,
        "oracle_price": t._oracle_price,
        "momentum_pct": t.momentum_pct,
        "oracle_divergence_pct": t.oracle_divergence_pct,
        "oracle_lag_seconds": t.oracle_lag_seconds,
        "trend_consistent": t.trend_consistent,
        "window_size": t.window_size,
        "history": history,
        "market": {
            "question": market.question if market else None,
            "up_price": market.up_price if market else 0,
            "down_price": market.down_price if market else 0,
            "window_start": market.window_start if market else 0,
            "window_end": market.window_end if market else 0,
            "window_remaining": window_remaining,
            "active": market.active if market else False,
        },
    })


@routes.get("/api/trades")
async def handle_trades(request: web.Request) -> web.Response:
    bot = _bot(request)
    limit = int(request.query.get("limit", "10"))
    offset = int(request.query.get("offset", "0"))
    trades = await bot.ledger.get_trades(limit, offset)
    total = await bot.ledger.get_trade_count()
    return web.json_response({"trades": trades, "total": total})


@routes.get("/api/balance")
async def handle_balance(request: web.Request) -> web.Response:
    bot = _bot(request)
    since = float(request.query.get("since", "0"))
    history = await bot.ledger.get_balance_history(since)
    return web.json_response({
        "current": bot.stats.current_balance,
        "initial": settings.initial_balance,
        "peak": bot.stats.peak_balance,
        "history": history,
    })


@routes.get("/api/signal")
async def handle_signal(request: web.Request) -> web.Response:
    bot = _bot(request)
    t = bot.tracker
    market = bot._current_market

    now = time.time()
    elapsed = (now - market.window_start) if market else 0

    # Gate statuses
    timing_ok = settings.entry_min_seconds <= elapsed <= settings.entry_max_seconds if market else False
    momentum_ok = abs(t.momentum_pct) >= settings.momentum_threshold
    oracle_ok = (
        t.oracle_divergence_pct > settings.oracle_lag_threshold
        or t.oracle_lag_seconds > 2.0
    )
    target_price = 0.0
    price_ok = False
    if market:
        side = "Up" if t.momentum_pct > 0 else "Down"
        from core.types import Side
        target_price = market.price_for(Side.UP if t.momentum_pct > 0 else Side.DOWN)
        price_ok = target_price <= settings.max_entry_price

    # Confidence would be (approximate)
    confidence = 0.0
    if timing_ok and momentum_ok and oracle_ok and price_ok:
        signal = bot.detector.evaluate(t, market) if market else None
        if signal:
            confidence = signal.confidence

    # Active signal
    pending_signal = getattr(bot, "_pending_signal", None)
    active_signal = None
    if pending_signal and bot.sm.state.value in ("SIGNAL", "TRADING"):
        active_signal = {
            "side": pending_signal.side.value,
            "confidence": pending_signal.confidence,
            "momentum_pct": pending_signal.momentum_pct,
            "target_price": pending_signal.target_price,
            "binance_price": pending_signal.binance_price,
        }

    return web.json_response({
        "gates": {
            "timing": {
                "passed": timing_ok,
                "value": round(elapsed, 1),
                "min": settings.entry_min_seconds,
                "max": settings.entry_max_seconds,
            },
            "momentum": {
                "passed": momentum_ok,
                "value": round(t.momentum_pct * 100, 4),
                "threshold": round(settings.momentum_threshold * 100, 4),
            },
            "oracle_lag": {
                "passed": oracle_ok,
                "value": round(t.oracle_divergence_pct * 100, 4),
                "threshold": round(settings.oracle_lag_threshold * 100, 4),
                "lag_seconds": round(t.oracle_lag_seconds, 1),
            },
            "market_price": {
                "passed": price_ok,
                "value": round(target_price, 3),
                "threshold": settings.max_entry_price,
            },
            "confidence": {
                "passed": confidence >= settings.min_confidence,
                "value": round(confidence, 2),
                "threshold": settings.min_confidence,
            },
        },
        "active_signal": active_signal,
        "total_signals": bot.stats.total_signals,
        "signals_traded": bot.stats.signals_traded,
    })


@routes.get("/api/risk")
async def handle_risk(request: web.Request) -> web.Response:
    bot = _bot(request)
    s = bot.stats
    allowed, reason = bot.risk.can_trade(s)

    # Drawdown calculation
    drawdown = 0.0
    if s.day_start_balance > 0:
        drawdown = 1.0 - (s.current_balance / s.day_start_balance)

    # Cooldown info
    cooldown_remaining = 0
    if bot.risk._state.cooldown_until > 0:
        cooldown_remaining = max(0, int(bot.risk._state.cooldown_until - time.time()))

    # Position tier
    balance = s.current_balance
    tier_label = "$63K+ (60%)"
    for upper, frac in [(320, "< $320 (100%)"), (2200, "$320-$2.2K (90%)"),
                         (12800, "$2.2K-$12.8K (80%)"), (63000, "$12.8K-$63K (70%)")]:
        if balance < upper:
            tier_label = frac
            break

    next_bet = bot.sizer.compute(s)

    return web.json_response({
        "can_trade": allowed,
        "reason": reason,
        "drawdown": round(drawdown * 100, 1),
        "drawdown_limit": round(settings.daily_drawdown_limit * 100, 0),
        "consecutive_losses": s.consecutive_losses,
        "max_consecutive_losses": settings.max_consecutive_losses,
        "cooldown_remaining": cooldown_remaining,
        "cooldown_minutes": settings.cooldown_minutes,
        "position_tier": tier_label,
        "next_bet_size": next_bet,
        "stop_loss": settings.stop_loss_balance,
        "target_balance": settings.target_balance,
    })


@routes.get("/api/config")
async def handle_config(request: web.Request) -> web.Response:
    return web.json_response({
        "dry_run": settings.dry_run,
        "initial_balance": settings.initial_balance,
        "momentum_threshold": settings.momentum_threshold,
        "oracle_lag_threshold": settings.oracle_lag_threshold,
        "max_entry_price": settings.max_entry_price,
        "min_confidence": settings.min_confidence,
        "entry_min_seconds": settings.entry_min_seconds,
        "entry_max_seconds": settings.entry_max_seconds,
        "stop_loss_balance": settings.stop_loss_balance,
        "target_balance": settings.target_balance,
        "max_consecutive_losses": settings.max_consecutive_losses,
        "cooldown_losses": settings.cooldown_losses,
        "cooldown_minutes": settings.cooldown_minutes,
        "daily_drawdown_limit": settings.daily_drawdown_limit,
        "max_book_depth_fraction": settings.max_book_depth_fraction,
        "price_window_seconds": settings.price_window_seconds,
    })


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


async def create_app(bot: Orchestrator) -> web.Application:
    """Create the aiohttp app with all routes."""
    app = web.Application(middlewares=[cors_middleware])
    app[_APP_KEY] = bot
    app.router.add_routes(routes)
    return app


async def start_api_server(bot: Orchestrator) -> web.AppRunner:
    """Start the API server, returning the runner for cleanup."""
    app = await create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8899)
    await site.start()
    return runner
