"""Shared synchronous HTTP client for observability backends."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ._config import settings

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _client() -> httpx.Client:
    return httpx.Client(timeout=_TIMEOUT)


def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with _client() as client:
        response = client.get(url, params=params or {})
        response.raise_for_status()
        return response.json()
