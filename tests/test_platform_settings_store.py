"""SQLite platform settings (daily budget persistence)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.platform_settings import PlatformSettingsStore  # noqa: E402


def test_agents_max_daily_cost_roundtrip(tmp_path: Path) -> None:
    async def _run() -> None:
        db = tmp_path / "settings.db"
        store = PlatformSettingsStore(db)
        assert await store.get_stored_agents_max_daily_cost_usd() is None
        await store.set_agents_max_daily_cost_usd(42.5)
        assert await store.get_stored_agents_max_daily_cost_usd() == 42.5
        await store.clear_agents_max_daily_cost_usd()
        assert await store.get_stored_agents_max_daily_cost_usd() is None

    asyncio.run(_run())
