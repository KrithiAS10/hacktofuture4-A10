from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from tools._config import settings

WORKFLOW_KEY_PREFIX = "lerna:agents:workflow:"
INCIDENT_WORKFLOW_KEY_PREFIX = "lerna:agents:incident:"
LAST_WORKFLOW_KEY = "lerna:agents:workflow:last"
COST_SETTINGS_KEY = "lerna:agents:cost:settings"
DAILY_COST_KEY_PREFIX = "lerna:agents:cost:daily:"
PROMPT_HASH_KEY = "lerna:agent_prompts"


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
        if not payload:
            return None
        workflow = json.loads(payload)
        if isinstance(workflow, dict):
            # Historical workflows may have stored `result` as a stringified exception.
            # Normalize it into a dict to keep API response validation stable.
            result = workflow.get("result")
            if isinstance(result, str):
                workflow["result"] = {"error": result}
        return workflow

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

    async def list_workflows(self, limit: int = 25) -> list[Dict[str, Any]]:
        workflows: list[Dict[str, Any]] = []
        async for key in self._redis.scan_iter(match=f"{WORKFLOW_KEY_PREFIX}*"):
            payload = await self._redis.get(key)
            if not payload:
                continue
            try:
                workflow = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(workflow, dict):
                result = workflow.get("result")
                if isinstance(result, str):
                    workflow["result"] = {"error": result}
                workflows.append(workflow)

        workflows.sort(key=lambda item: str(item.get("accepted_at") or ""), reverse=True)
        return workflows[:limit]

    async def get_workflow_for_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        workflow_id = await self._redis.get(f"{INCIDENT_WORKFLOW_KEY_PREFIX}{incident_id}")
        if not workflow_id:
            return None
        return await self.get_workflow(workflow_id)

    async def bind_incident(self, incident_id: str, workflow_id: str) -> None:
        await self._redis.set(f"{INCIDENT_WORKFLOW_KEY_PREFIX}{incident_id}", workflow_id)

    async def get_max_daily_cost(self) -> Optional[float]:
        raw = await self._redis.hget(COST_SETTINGS_KEY, "max_daily_cost")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def set_max_daily_cost(self, amount: float) -> None:
        await self._redis.hset(COST_SETTINGS_KEY, mapping={"max_daily_cost": amount})

    @staticmethod
    def _daily_cost_key(day: Optional[str] = None) -> str:
        date_key = day or datetime.now(tz=timezone.utc).date().isoformat()
        return f"{DAILY_COST_KEY_PREFIX}{date_key}"

    async def get_daily_spend(self, day: Optional[str] = None) -> float:
        raw = await self._redis.get(self._daily_cost_key(day))
        if raw is None:
            return 0.0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    async def add_daily_spend(self, amount: float, day: Optional[str] = None) -> float:
        key = self._daily_cost_key(day)
        current = await self.get_daily_spend(day)
        total = current + amount
        await self._redis.set(key, total)
        return total

    async def get_agent_prompt(self, agent_id: str) -> Optional[str]:
        prompt = await self._redis.hget(PROMPT_HASH_KEY, agent_id)
        if prompt is None:
            return None
        return str(prompt)

    async def get_agent_prompts(self, agent_ids: list[str]) -> Dict[str, str]:
        if not agent_ids:
            return {}
        values = await self._redis.hmget(PROMPT_HASH_KEY, agent_ids)
        return {
            agent_id: str(value)
            for agent_id, value in zip(agent_ids, values)
            if value is not None
        }
