from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.services.platform_settings import PlatformSettingsStore

logger = logging.getLogger(__name__)


def _orchestrator_timeout() -> httpx.Timeout:
    sec = settings.agents_orchestrator_timeout_seconds
    return httpx.Timeout(sec, connect=10.0)


def _float_neq(a: Optional[float], b: Any) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    try:
        return abs(float(a) - float(b)) > 1e-6
    except (TypeError, ValueError):
        return True


class AgentsService:
    def __init__(self, platform_settings: PlatformSettingsStore) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        self._platform = platform_settings

    async def close(self) -> None:
        await self._client.aclose()

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        response = await self._client.get(f"{settings.agents_service_url}/workflows/{workflow_id}")
        response.raise_for_status()
        return response.json()

    async def get_latest_workflow(self) -> Dict[str, Any]:
        response = await self._client.get(f"{settings.agents_service_url}/workflows/latest")
        response.raise_for_status()
        return response.json()

    async def list_workflows(self, limit: int = 25) -> Dict[str, Any]:
        response = await self._client.get(f"{settings.agents_service_url}/workflows", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    async def orchestrator_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{settings.agents_service_url}/orchestrator/chat",
            json=payload,
            timeout=_orchestrator_timeout(),
        )
        response.raise_for_status()
        return response.json()

    async def _effective_max_daily_cost(self) -> Optional[float]:
        stored = await self._platform.get_stored_agents_max_daily_cost_usd()
        if stored is not None:
            return stored
        return settings.default_max_daily_agent_cost_usd

    async def _sync_agents_max_if_needed(self, effective: Optional[float]) -> None:
        try:
            await self._client.put(
                f"{settings.agents_service_url}/cost-settings",
                json={"max_daily_cost": effective},
            )
        except httpx.HTTPError as exc:
            logger.warning("Could not sync max_daily_cost to agents service: %s", exc)

    async def get_cost_settings(self) -> Dict[str, Any]:
        """
        Daily cap comes from platform SQLite (or env default); spent_today from agents Redis.
        Pushes cap to agents when it differs so enforcement stays aligned.
        """
        effective = await self._effective_max_daily_cost()
        response = await self._client.get(f"{settings.agents_service_url}/cost-settings")
        response.raise_for_status()
        data = response.json()
        spent = float(data.get("spent_today") or 0.0)
        agents_max = data.get("max_daily_cost")
        if agents_max is not None:
            try:
                agents_max = float(agents_max)
            except (TypeError, ValueError):
                agents_max = None

        if _float_neq(effective, agents_max):
            await self._sync_agents_max_if_needed(effective)

        remaining = None if effective is None else max(0.0, effective - spent)
        return {
            "max_daily_cost": effective,
            "spent_today": spent,
            "remaining_today": remaining,
        }

    async def update_cost_settings(self, max_daily_cost: float) -> Dict[str, Any]:
        await self._platform.set_agents_max_daily_cost_usd(max_daily_cost)
        await self._sync_agents_max_if_needed(max_daily_cost)
        return await self.get_cost_settings()

    async def get_execution_mode(self) -> Dict[str, str]:
        stored = await self._platform.get_stored_agents_execution_mode()
        return {"mode": stored or "autonomous"}

    async def update_execution_mode(self, mode: str) -> Dict[str, Any]:
        stored = await self._platform.set_agents_execution_mode(mode)
        response = await self._client.put(
            f"{settings.agents_service_url}/execution-mode",
            json={"mode": stored},
        )
        response.raise_for_status()
        return {"mode": stored}

    async def sync_execution_mode_on_startup(self) -> None:
        stored = await self._platform.get_stored_agents_execution_mode()
        mode = stored or "autonomous"
        try:
            await self._client.put(
                f"{settings.agents_service_url}/execution-mode",
                json={"mode": mode},
            )
        except httpx.HTTPError as exc:
            logger.warning("Could not sync execution mode to agents on startup: %s", exc)
