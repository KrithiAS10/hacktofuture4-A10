from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from app.models import ClusterSummary, HealthResponse
from app.services.cluster_poller import ClusterPoller
from app.services.observability import ObservabilityService

obs_service = ObservabilityService()
cluster_poller = ClusterPoller()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await cluster_poller.start()
    try:
        yield
    finally:
        await cluster_poller.stop()
        await obs_service.close()


app = FastAPI(title="Lerna Observation Backend", version="0.1.0", lifespan=lifespan)


@app.get("/api/obs/health", response_model=HealthResponse)
async def get_obs_health() -> HealthResponse:
    return await obs_service.check_health()


@app.get("/api/obs/metrics")
async def get_metrics(
    query: str = Query(..., description="PromQL query"),
    time: Optional[str] = Query(None, description="RFC3339 timestamp"),
):
    try:
        return await obs_service.query_metrics(query=query, time=time)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Metrics query failed: {exc}") from exc


@app.get("/api/obs/logs")
async def get_logs(
    query: str = Query(..., description="LogQL query"),
    limit: int = Query(200, ge=1, le=1000),
    start: Optional[str] = Query(None, description="Start time in epoch nanoseconds"),
    end: Optional[str] = Query(None, description="End time in epoch nanoseconds"),
    direction: str = Query("backward", pattern="^(forward|backward)$"),
):
    try:
        return await obs_service.query_logs(query=query, limit=limit, start=start, end=end, direction=direction)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Logs query failed: {exc}") from exc


@app.get("/api/obs/traces")
async def get_traces(
    service: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    lookback_minutes: int = Query(60, ge=1, le=1440),
):
    try:
        return await obs_service.query_traces(service=service, limit=limit, lookback_minutes=lookback_minutes)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Traces query failed: {exc}") from exc


@app.get("/api/cluster/summary", response_model=ClusterSummary)
async def get_cluster_summary() -> ClusterSummary:
    return ClusterSummary(**cluster_poller.get_snapshot())


@app.get("/api/cluster/health")
async def get_cluster_health():
    snapshot = cluster_poller.get_snapshot()
    if not snapshot.get("available"):
        return {"ok": False, "reason": snapshot.get("reason")}

    nodes = snapshot.get("nodes", {})
    deployments = snapshot.get("deployments", {})
    services = snapshot.get("services", {})
    degraded = (
        (nodes.get("total", 0) - nodes.get("ready", 0))
        + deployments.get("degraded_count", 0)
        + services.get("without_ready_endpoints_count", 0)
    )
    return {
        "ok": degraded == 0,
        "score_hint": max(0, 100 - degraded * 5),
        "nodes": nodes,
        "deployments": deployments,
        "services": services,
        "last_updated": snapshot.get("last_updated"),
    }
