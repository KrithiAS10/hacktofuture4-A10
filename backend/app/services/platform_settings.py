"""SQLite-backed operator settings (daily agent budget, etc.)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_TABLE = "lerna_platform_settings"
_KEY_AGENTS_MAX_DAILY = "agents_max_daily_cost_usd"
_KEY_AGENTS_EXECUTION_MODE = "agents_execution_mode"
_VALID_EXECUTION_MODES = frozenset({"autonomous", "advisory", "paused"})


def _schema_sql() -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {_TABLE} (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    """


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(_schema_sql())
        conn.commit()


def _db_get(db_path: Path, key: str) -> Optional[str]:
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute(f"SELECT value FROM {_TABLE} WHERE key = ?", (key,))
        row = cur.fetchone()
        return str(row[0]) if row and row[0] is not None else None


def _db_set(db_path: Path, key: str, value: str) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            f"""
            INSERT INTO {_TABLE}(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        conn.commit()


def _db_delete(db_path: Path, key: str) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(f"DELETE FROM {_TABLE} WHERE key = ?", (key,))
        conn.commit()


class PlatformSettingsStore:
    """Persists settings locally; used as source of truth for daily LLM budget."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ready = False
        self._lock = asyncio.Lock()

    async def _ensure(self) -> None:
        async with self._lock:
            if self._ready:
                return
            await asyncio.to_thread(_init_db, self._db_path)
            self._ready = True

    async def get_stored_agents_max_daily_cost_usd(self) -> Optional[float]:
        """Return value from DB only (no env fallback). None if unset."""
        await self._ensure()
        raw = await asyncio.to_thread(_db_get, self._db_path, _KEY_AGENTS_MAX_DAILY)
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            logger.warning("Invalid agents_max_daily_cost_usd in DB: %r", raw)
            return None

    async def set_agents_max_daily_cost_usd(self, amount: float) -> None:
        await self._ensure()
        await asyncio.to_thread(_db_set, self._db_path, _KEY_AGENTS_MAX_DAILY, str(amount))

    async def clear_agents_max_daily_cost_usd(self) -> None:
        await self._ensure()
        await asyncio.to_thread(_db_delete, self._db_path, _KEY_AGENTS_MAX_DAILY)

    async def get_stored_agents_execution_mode(self) -> str | None:
        """Return stored mode or None if unset (caller defaults to autonomous)."""
        await self._ensure()
        raw = await asyncio.to_thread(_db_get, self._db_path, _KEY_AGENTS_EXECUTION_MODE)
        if raw is None or raw == "":
            return None
        m = str(raw).strip().lower()
        if m not in _VALID_EXECUTION_MODES:
            logger.warning("Invalid agents_execution_mode in DB: %r", raw)
            return None
        return m

    async def set_agents_execution_mode(self, mode: str) -> str:
        m = str(mode).strip().lower()
        if m not in _VALID_EXECUTION_MODES:
            m = "autonomous"
        await self._ensure()
        await asyncio.to_thread(_db_set, self._db_path, _KEY_AGENTS_EXECUTION_MODE, m)
        return m
