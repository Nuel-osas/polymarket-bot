from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


class BotState(enum.Enum):
    SCANNING = "SCANNING"
    SIGNAL = "SIGNAL"
    TRADING = "TRADING"
    WAITING = "WAITING"
    COMPOUNDING = "COMPOUNDING"
    COOLDOWN = "COOLDOWN"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class Side(enum.Enum):
    UP = "Up"
    DOWN = "Down"


@dataclass
class Signal:
    side: Side
    confidence: float
    momentum_pct: float
    oracle_lag_pct: float
    oracle_lag_seconds: float
    target_price: float
    binance_price: float
    window_elapsed_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class MarketInfo:
    condition_id: str
    question: str
    up_token_id: str
    down_token_id: str
    up_price: float
    down_price: float
    window_start: int  # epoch seconds (rounded to 300s boundary)
    window_end: int
    neg_risk: bool = False
    active: bool = True
    tick_size: str = "0.01"

    def token_id_for(self, side: Side) -> str:
        return self.up_token_id if side is Side.UP else self.down_token_id

    def price_for(self, side: Side) -> float:
        return self.up_price if side is Side.UP else self.down_price


@dataclass
class TradeResult:
    success: bool
    side: Side
    amount_usdc: float
    price: float
    confidence: float
    market_condition_id: str
    order_id: str = ""
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    dry_run: bool = False

    @property
    def expected_payout(self) -> float:
        if not self.success:
            return 0.0
        # shares = amount / price, payout = shares * 1.0 on win
        return self.amount_usdc / self.price if self.price > 0 else 0.0


@dataclass
class BotStats:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    current_balance: float = 0.0
    peak_balance: float = 0.0
    day_start_balance: float = 0.0
    total_signals: int = 0
    signals_traded: int = 0
