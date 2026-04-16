from __future__ import annotations

from typing import Any, Dict

import httpx

from app.config import settings


class AgentsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def trigger_incident(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(f"{settings.agents_service_url}/incidents", json=payload)
        response.raise_for_status()
        return response.json()
