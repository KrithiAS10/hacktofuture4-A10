from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings


def _orchestrator_timeout() -> httpx.Timeout:
    sec = settings.agents_orchestrator_timeout_seconds
    return httpx.Timeout(sec, connect=10.0)


class AgentsService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

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

    async def get_cost_settings(self) -> Dict[str, Any]:
        response = await self._client.get(f"{settings.agents_service_url}/cost-settings")
        response.raise_for_status()
        return response.json()

    async def update_cost_settings(self, max_daily_cost: float) -> Dict[str, Any]:
        response = await self._client.put(
            f"{settings.agents_service_url}/cost-settings",
            json={"max_daily_cost": max_daily_cost},
        )
        response.raise_for_status()
        return response.json()
