from __future__ import annotations

import json
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from tools._config import settings

WORKFLOW_KEY_PREFIX = "lerna:agents:workflow:"
INCIDENT_WORKFLOW_KEY_PREFIX = "lerna:agents:incident:"
LAST_WORKFLOW_KEY = "lerna:agents:workflow:last"


class WorkflowStore:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis = Redis.from_url(
            redis_url or getattr(settings, "redis_url", "redis://localhost:6379/0"),
            decode_responses=True,
        )

    async def close(self) -> None:
        await self._redis.aclose()

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        payload = await self._redis.get(f"{WORKFLOW_KEY_PREFIX}{workflow_id}")
        return json.loads(payload) if payload else None

    async def save_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        await self._redis.set(f"{WORKFLOW_KEY_PREFIX}{workflow_id}", json.dumps(data))
        await self._redis.set(LAST_WORKFLOW_KEY, workflow_id)

    async def get_last_workflow_id(self) -> Optional[str]:
        return await self._redis.get(LAST_WORKFLOW_KEY)

    async def get_last_workflow(self) -> Optional[Dict[str, Any]]:
        workflow_id = await self.get_last_workflow_id()
        if not workflow_id:
            return None
        return await self.get_workflow(workflow_id)

    async def get_workflow_for_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        workflow_id = await self._redis.get(f"{INCIDENT_WORKFLOW_KEY_PREFIX}{incident_id}")
        if not workflow_id:
            return None
        return await self.get_workflow(workflow_id)

    async def bind_incident(self, incident_id: str, workflow_id: str) -> None:
        await self._redis.set(f"{INCIDENT_WORKFLOW_KEY_PREFIX}{incident_id}", workflow_id)
