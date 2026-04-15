from __future__ import annotations

import logging
from typing import Dict, Iterable

from redis.asyncio import Redis

from app.config import settings


PROMPT_HASH_KEY = "lerna:agent_prompts"
logger = logging.getLogger(__name__)


class PromptStoreService:
    def __init__(self) -> None:
        # Keep Redis operations snappy so API endpoints don't hang when Redis is down.
        self._redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self._fallback_prompts: Dict[str, str] = {}

    async def close(self) -> None:
        try:
            await self._redis.aclose()
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to close Redis client")

    async def get_prompts(self, agent_ids: Iterable[str] | None = None) -> Dict[str, str]:
        if agent_ids:
            ids = list(agent_ids)
            if not ids:
                return {}
            try:
                values = await self._redis.hmget(PROMPT_HASH_KEY, ids)
                return {agent_id: value for agent_id, value in zip(ids, values) if value is not None}
            except Exception:  # pylint: disable=broad-except
                logger.warning("Redis unavailable while reading prompts; using in-memory fallback")
                return {agent_id: self._fallback_prompts[agent_id] for agent_id in ids if agent_id in self._fallback_prompts}

        try:
            prompts = await self._redis.hgetall(PROMPT_HASH_KEY)
            return prompts or {}
        except Exception:  # pylint: disable=broad-except
            logger.warning("Redis unavailable while reading all prompts; using in-memory fallback")
            return dict(self._fallback_prompts)

    async def set_prompt(self, agent_id: str, prompt: str) -> None:
        self._fallback_prompts[agent_id] = prompt
        try:
            await self._redis.hset(PROMPT_HASH_KEY, agent_id, prompt)
        except Exception:  # pylint: disable=broad-except
            logger.warning("Redis unavailable while saving prompt for %s; kept in memory", agent_id)

    async def get_prompt(self, agent_id: str) -> str | None:
        try:
            value = await self._redis.hget(PROMPT_HASH_KEY, agent_id)
            if value is not None:
                return value
        except Exception:  # pylint: disable=broad-except
            logger.warning("Redis unavailable while reading prompt for %s; using in-memory fallback", agent_id)
        return self._fallback_prompts.get(agent_id)

    async def delete_prompt(self, agent_id: str) -> int:
        self._fallback_prompts.pop(agent_id, None)
        try:
            return int(await self._redis.hdel(PROMPT_HASH_KEY, agent_id))
        except Exception:  # pylint: disable=broad-except
            logger.warning("Redis unavailable while deleting prompt for %s; removed from in-memory fallback", agent_id)
            return 1
