from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.models import BackendStatus, HealthResponse


class ObservabilityService:
    def __init__(self) -> None:
        self._timeout = httpx.Timeout(10.0, connect=5.0)

    async def check_health(self) -> HealthResponse:
        prometheus = await self._check_endpoint(
            f"{settings.prometheus_url}/-/ready",
            fallback=f"{settings.prometheus_url}/api/v1/status/config",
        )
        loki = await self._check_endpoint(
            f"{settings.loki_url}/ready",
            fallback=f"{settings.loki_url}/loki/api/v1/labels",
        )
        jaeger = await self._check_endpoint(
            f"{settings.jaeger_url}/api/services",
            fallback=f"{settings.jaeger_url}/",
        )
        return HealthResponse(
            prometheus=prometheus,
            loki=loki,
            jaeger=jaeger,
            overall_ok=prometheus.ok and loki.ok and jaeger.ok,
        )

    async def query_metrics(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"query": query}
        if time:
            params["time"] = time
        return await self._get_json(f"{settings.prometheus_url}/api/v1/query", params=params)

    async def query_logs(
        self,
        query: str,
        limit: int = 200,
        start: Optional[str] = None,
        end: Optional[str] = None,
        direction: str = "backward",
    ) -> Dict[str, Any]:
        end_ts = end or str(int(datetime.now(tz=timezone.utc).timestamp() * 1_000_000_000))
        if start:
            start_ts = start
        else:
            start_ts = str(
                int((datetime.now(tz=timezone.utc) - timedelta(minutes=15)).timestamp() * 1_000_000_000)
            )
        params = {
            "query": query,
            "limit": limit,
            "start": start_ts,
            "end": end_ts,
            "direction": direction,
        }
        return await self._get_json(f"{settings.loki_url}/loki/api/v1/query_range", params=params)

    async def query_traces(
        self,
        service: Optional[str] = None,
        limit: int = 20,
        lookback_minutes: int = 60,
    ) -> Dict[str, Any]:
        end_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        start_ms = int((datetime.now(tz=timezone.utc) - timedelta(minutes=lookback_minutes)).timestamp() * 1000)
        params: Dict[str, Any] = {
            "limit": limit,
            "lookback": f"{lookback_minutes}m",
            "start": start_ms,
            "end": end_ms,
        }
        if service:
            params["service"] = service
        return await self._get_json(f"{settings.jaeger_url}/api/traces", params=params)

    async def _check_endpoint(self, endpoint: str, fallback: str) -> BackendStatus:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(endpoint)
                if response.status_code < 400:
                    return BackendStatus(ok=True, endpoint=endpoint)
                fallback_response = await client.get(fallback)
                if fallback_response.status_code < 400:
                    return BackendStatus(ok=True, endpoint=fallback, detail=f"fallback used; {response.status_code}")
                return BackendStatus(
                    ok=False,
                    endpoint=endpoint,
                    detail=f"primary={response.status_code}, fallback={fallback_response.status_code}",
                )
        except Exception as exc:  # pylint: disable=broad-except
            return BackendStatus(ok=False, endpoint=endpoint, detail=str(exc))

    async def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
