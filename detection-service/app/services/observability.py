from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.config import settings


class ObservabilityService:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(10.0, connect=5.0)
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def query_logs(
        self,
        query: str,
        limit: int = 200,
        start: Optional[str] = None,
        end: Optional[str] = None,
        direction: str = "backward",
    ) -> Dict[str, Any]:
        end_ts = end or str(int(datetime.now(tz=timezone.utc).timestamp() * 1_000_000_000))
        start_ts = start or str(
            int((datetime.now(tz=timezone.utc) - timedelta(minutes=15)).timestamp() * 1_000_000_000)
        )
        response = await self._client.get(
            f"{settings.loki_url}/loki/api/v1/query_range",
            params={
                "query": query,
                "limit": limit,
                "start": start_ts,
                "end": end_ts,
                "direction": direction,
            },
        )
        response.raise_for_status()
        return response.json()
