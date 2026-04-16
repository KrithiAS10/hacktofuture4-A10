from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings


class AgentsService:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

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

    async def orchestrator_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(f"{settings.agents_service_url}/orchestrator/chat", json=payload)
        response.raise_for_status()
        return response.json()
