"""SQLite trade ledger and balance history."""

from __future__ import annotations

import time

import aiosqlite

from core.types import BotStats, Side, TradeResult

_DB_PATH = "polybot.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    side TEXT NOT NULL,
    amount_usdc REAL NOT NULL,
    price REAL NOT NULL,
    confidence REAL NOT NULL,
    condition_id TEXT NOT NULL,
    order_id TEXT,
    success INTEGER NOT NULL,
    dry_run INTEGER NOT NULL,
    outcome TEXT DEFAULT 'pending',
    payout REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS balance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    balance REAL NOT NULL,
    event TEXT NOT NULL
);
"""


class Ledger:
    """Async SQLite ledger for trade and balance logging."""

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_INIT_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def log_trade(self, trade: TradeResult) -> None:
        assert self._db is not None
        await self._db.execute(
            """INSERT INTO trades
               (timestamp, side, amount_usdc, price, confidence,
                condition_id, order_id, success, dry_run)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trade.timestamp,
                trade.side.value,
                trade.amount_usdc,
                trade.price,
                trade.confidence,
                trade.market_condition_id,
                trade.order_id,
                int(trade.success),
                int(trade.dry_run),
            ),
        )
        await self._db.commit()

    async def update_outcome(
        self, condition_id: str, outcome: str, payout: float
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            "UPDATE trades SET outcome=?, payout=? WHERE condition_id=? AND outcome='pending'",
            (outcome, payout, condition_id),
        )
        await self._db.commit()

    async def log_balance(self, balance: float, event: str = "update") -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO balance_history (timestamp, balance, event) VALUES (?, ?, ?)",
            (time.time(), balance, event),
        )
        await self._db.commit()

    async def get_trades(self, limit: int = 10, offset: int = 0) -> list[dict]:
        """Return recent trades as dicts."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT id, timestamp, side, amount_usdc, price, confidence, "
            "condition_id, order_id, success, dry_run, outcome, payout "
            "FROM trades ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "side": r[2],
                "amount_usdc": r[3],
                "price": r[4],
                "confidence": r[5],
                "condition_id": r[6],
                "order_id": r[7],
                "success": bool(r[8]),
                "dry_run": bool(r[9]),
                "outcome": r[10],
                "payout": r[11],
            }
            for r in rows
        ]

    async def get_trade_count(self) -> int:
        """Return total number of trades."""
        assert self._db is not None
        async with self._db.execute("SELECT COUNT(*) FROM trades") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def get_balance_history(self, since: float = 0) -> list[dict]:
        """Return balance history entries since a given timestamp."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT timestamp, balance, event FROM balance_history "
            "WHERE timestamp > ? ORDER BY id ASC",
            (since,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {"timestamp": r[0], "balance": r[1], "event": r[2]}
            for r in rows
        ]

    async def get_stats(self) -> dict:
        """Return summary stats from the ledger."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT COUNT(*), SUM(CASE WHEN outcome='win' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN outcome='loss' THEN 1 ELSE 0 END) FROM trades"
        ) as cur:
            row = await cur.fetchone()
            total, wins, losses = row if row else (0, 0, 0)

        async with self._db.execute(
            "SELECT balance FROM balance_history ORDER BY id DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
            last_balance = row[0] if row else 0.0

        return {
            "total_trades": total or 0,
            "wins": wins or 0,
            "losses": losses or 0,
            "last_balance": last_balance,
            "win_rate": (wins / total * 100) if total else 0,
        }
