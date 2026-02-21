from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _float(key: str, default: float) -> float:
    return float(_env(key, str(default)))


def _int(key: str, default: int) -> int:
    return int(_env(key, str(default)))


def _bool(key: str, default: bool) -> bool:
    return _env(key, str(default)).lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class Settings:
    # Polymarket
    poly_private_key: str = field(default_factory=lambda: _env("POLY_PRIVATE_KEY"))
    poly_funder: str = field(default_factory=lambda: _env("POLY_FUNDER"))
    clob_host: str = "https://clob.polymarket.com"
    gamma_host: str = "https://gamma-api.polymarket.com"
    chain_id: int = 137

    # Mode
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", True))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # Binance
    binance_ws_url: str = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    price_window_seconds: int = 60

    # Strategy thresholds
    momentum_threshold: float = field(
        default_factory=lambda: _float("MOMENTUM_THRESHOLD", 0.0008)
    )
    oracle_lag_threshold: float = field(
        default_factory=lambda: _float("ORACLE_LAG_THRESHOLD", 0.0003)
    )
    max_entry_price: float = field(
        default_factory=lambda: _float("MAX_ENTRY_PRICE", 0.55)
    )
    min_confidence: float = field(
        default_factory=lambda: _float("MIN_CONFIDENCE", 0.70)
    )

    # Timing window (seconds into the 5-min period)
    window_seconds: int = 300
    entry_min_seconds: int = 30
    entry_max_seconds: int = 180

    # Risk management
    initial_balance: float = field(
        default_factory=lambda: _float("INITIAL_BALANCE", 20.0)
    )
    stop_loss_balance: float = field(
        default_factory=lambda: _float("STOP_LOSS_BALANCE", 10.0)
    )
    max_consecutive_losses: int = field(
        default_factory=lambda: _int("MAX_CONSECUTIVE_LOSSES", 3)
    )
    cooldown_losses: int = field(
        default_factory=lambda: _int("COOLDOWN_LOSSES", 2)
    )
    cooldown_minutes: int = field(
        default_factory=lambda: _int("COOLDOWN_MINUTES", 30)
    )
    daily_drawdown_limit: float = field(
        default_factory=lambda: _float("DAILY_DRAWDOWN_LIMIT", 0.50)
    )
    target_balance: float = field(
        default_factory=lambda: _float("TARGET_BALANCE", 100_000.0)
    )

    # Position sizing
    max_book_depth_fraction: float = 0.30

    # Polling intervals (seconds)
    market_poll_interval: float = 5.0
    resolution_poll_interval: float = 3.0
    heartbeat_interval: float = 10.0


settings = Settings()
