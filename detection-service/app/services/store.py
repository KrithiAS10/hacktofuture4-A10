from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from app.config import settings

FINGERPRINT_PREFIX = "lerna:detection:fingerprint:"
RETRY_KEY = "lerna:detection:retries"
RETRY_ITEM_PREFIX = "lerna:detection:retry:"


class DetectionStateStore:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        await self._redis.aclose()

    async def should_emit(self, fingerprint: str, summary_hash: str) -> bool:
        key = f"{FINGERPRINT_PREFIX}{fingerprint}"
        current = await self._redis.hgetall(key)
        if not current:
            return True
        return current.get("summary_hash") != summary_hash

    async def mark_emitted(self, fingerprint: str, summary_hash: str, status: str) -> None:
        key = f"{FINGERPRINT_PREFIX}{fingerprint}"
        await self._redis.hset(
            key,
            mapping={
                "summary_hash": summary_hash,
                "status": status,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        await self._redis.expire(key, settings.dedupe_ttl_seconds)

    async def enqueue_retry(self, incident_id: str, payload: Dict[str, Any], error: str) -> None:
        retry_at = datetime.now(tz=timezone.utc) + timedelta(seconds=settings.retry_delay_seconds)
        item_key = f"{RETRY_ITEM_PREFIX}{incident_id}"
        existing_attempts = await self._redis.hget(item_key, "attempts")
        attempts = int(existing_attempts or "0") + 1
        await self._redis.hset(
            item_key,
            mapping={
                "incident_id": incident_id,
                "payload": json.dumps(payload),
                "error": error,
                "attempts": attempts,
                "retry_at": retry_at.isoformat(),
            },
        )
        await self._redis.zadd(RETRY_KEY, {incident_id: retry_at.timestamp()})

    async def due_retries(self) -> List[Dict[str, Any]]:
        now = datetime.now(tz=timezone.utc).timestamp()
        incident_ids = await self._redis.zrangebyscore(RETRY_KEY, min=0, max=now)
        output: List[Dict[str, Any]] = []
        for incident_id in incident_ids:
            raw = await self._redis.hgetall(f"{RETRY_ITEM_PREFIX}{incident_id}")
            if raw:
                output.append(
                    {
                        "incident_id": incident_id,
                        "payload": json.loads(raw["payload"]),
                        "attempts": int(raw.get("attempts", "0")),
                        "error": raw.get("error"),
                    }
                )
        return output

    async def clear_retry(self, incident_id: str) -> None:
        await self._redis.zrem(RETRY_KEY, incident_id)
        await self._redis.delete(f"{RETRY_ITEM_PREFIX}{incident_id}")
