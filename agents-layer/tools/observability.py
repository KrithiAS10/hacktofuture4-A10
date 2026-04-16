"""HTTP-backed observability tools (Prometheus, Loki, Jaeger)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from ._config import settings
from ._http import get_json

_HTTP = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))


def prometheus_query(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Run a PromQL instant query against Prometheus (`/api/v1/query`)."""
    params: Dict[str, Any] = {"query": query}
    if time:
        params["time"] = time
    return get_json(f"{settings.prometheus_url}/api/v1/query", params=params)


def loki_query_range(
    query: str,
    limit: int = 200,
    start: Optional[str] = None,
    end: Optional[str] = None,
    direction: str = "backward",
) -> Dict[str, Any]:
    """Run a LogQL range query against Loki (`/loki/api/v1/query_range`). Times are epoch nanoseconds as strings."""
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
    return get_json(f"{settings.loki_url}/loki/api/v1/query_range", params=params)


def jaeger_search_traces(
    service: Optional[str] = None,
    limit: int = 20,
    lookback_minutes: int = 60,
) -> Dict[str, Any]:
    """Search traces via Jaeger query API (`/api/traces`)."""
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
    return get_json(f"{settings.jaeger_url}/api/traces", params=params)


def check_observability_backends() -> Dict[str, Any]:
    """Lightweight readiness probe for Prometheus, Loki, and Jaeger (mirrors backend `/api/obs/health` intent)."""
    out: Dict[str, Any] = {"prometheus": {}, "loki": {}, "jaeger": {}, "overall_ok": False}

    def probe(primary: str, fallback: str) -> Dict[str, Any]:
        try:
            r = _HTTP.get(primary)
            if r.status_code < 400:
                return {"ok": True, "endpoint": primary}
        except Exception as exc_primary:  # pylint: disable=broad-except
            try:
                r2 = _HTTP.get(fallback)
                if r2.status_code < 400:
                    return {"ok": True, "endpoint": fallback, "detail": f"fallback; primary err: {exc_primary!s}"}
            except Exception as exc_fb:  # pylint: disable=broad-except
                return {"ok": False, "endpoint": primary, "detail": f"{exc_primary!s}; fallback: {exc_fb!s}"}
            return {"ok": False, "endpoint": primary, "detail": str(exc_primary)}
        try:
            r2 = _HTTP.get(fallback)
            if r2.status_code < 400:
                return {"ok": True, "endpoint": fallback, "detail": f"fallback; primary status={r.status_code}"}
        except Exception as exc_fb:  # pylint: disable=broad-except
            return {"ok": False, "endpoint": primary, "detail": f"primary {r.status_code}; fallback err: {exc_fb!s}"}
        return {"ok": False, "endpoint": primary, "detail": f"primary {r.status_code}; fallback not ok"}

    out["prometheus"] = probe(
        f"{settings.prometheus_url}/-/ready",
        f"{settings.prometheus_url}/api/v1/status/config",
    )
    out["loki"] = probe(
        f"{settings.loki_url}/ready",
        f"{settings.loki_url}/loki/api/v1/labels",
    )
    out["jaeger"] = probe(
        f"{settings.jaeger_url}/api/services",
        f"{settings.jaeger_url}/",
    )
    out["overall_ok"] = bool(
        out["prometheus"].get("ok") and out["loki"].get("ok") and out["jaeger"].get("ok")
    )
    return out
