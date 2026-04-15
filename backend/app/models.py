from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class BackendStatus(BaseModel):
    ok: bool
    endpoint: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    prometheus: BackendStatus
    loki: BackendStatus
    jaeger: BackendStatus
    overall_ok: bool


class ClusterSummary(BaseModel):
    available: bool
    last_updated: Optional[str] = None
    reason: Optional[str] = None
    namespace_scope: Optional[str] = None
    nodes: Dict[str, Any] = {}
    deployments: Dict[str, Any] = {}
    services: Dict[str, Any] = {}
    pods: Dict[str, Any] = {}
    recent_events: List[Dict[str, Any]] = []
