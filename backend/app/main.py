from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AgentCostSettingsResponse,
    AgentCostSettingsUpdateRequest,
    AgentExecutionModeResponse,
    AgentExecutionModeUpdateRequest,
    AgentPromptEntry,
    AgentPromptResetResponse,
    AgentPromptsResponse,
    AgentPromptUpdateRequest,
    AgentWorkflowListResponse,
    AgentWorkflowResponse,
    OrchestratorChatRequest,
    OrchestratorChatResponse,
    ClusterSummary,
    DetectionCheckResponse,
    HealthResponse,
)
from app.services.agents_service import AgentsService
from app.services.cluster_poller import ClusterPoller
from app.services.detection import DetectionService
from app.services.observability import ObservabilityService
from app.services.platform_settings import PlatformSettingsStore
from app.services.prompt_store import PromptStoreService
from app.config import settings as app_settings

obs_service = ObservabilityService()
cluster_poller = ClusterPoller(obs_service=obs_service)
detection_service = DetectionService(obs_service)
prompt_store = PromptStoreService()
platform_settings_store = PlatformSettingsStore(app_settings.platform_settings_db_path)
agents_service = AgentsService(platform_settings=platform_settings_store)
logger = logging.getLogger(__name__)


def _upstream_error_detail(body: Any, fallback: str) -> str:
    """FastAPI may return `detail` as str, list of validation dicts, or nested objects."""
    if not isinstance(body, dict):
        return fallback
    detail = body.get("detail")
    if detail is None:
        msg = body.get("message")
        return str(msg) if msg is not None else fallback
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                msg = item.get("msg", item)
                parts.append(f"{loc}: {msg}" if loc else str(msg))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else fallback
    return str(detail)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await cluster_poller.start()
    try:
        try:
            await agents_service.get_cost_settings()
        except Exception:  # pylint: disable=broad-except
            logger.warning("Could not sync daily cost cap to agents on startup (agents or Redis may be down).")
        try:
            await agents_service.sync_execution_mode_on_startup()
        except Exception:  # pylint: disable=broad-except
            logger.warning("Could not sync execution mode to agents on startup (agents or Redis may be down).")
        yield
    finally:
        await cluster_poller.stop()
        await obs_service.close()
        await prompt_store.close()
        await agents_service.close()


app = FastAPI(title="Lerna Observation Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    except Exception:  # pylint: disable=broad-except
        logger.exception("Metrics query failed")
        raise HTTPException(status_code=502, detail="Metrics query failed")


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
    except Exception:  # pylint: disable=broad-except
        logger.exception("Logs query failed")
        raise HTTPException(status_code=502, detail="Logs query failed")


@app.get("/api/obs/traces")
async def get_traces(
    service: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    lookback_minutes: int = Query(60, ge=1, le=1440),
):
    try:
        return await obs_service.query_traces(service=service, limit=limit, lookback_minutes=lookback_minutes)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Traces query failed")
        raise HTTPException(status_code=502, detail="Traces query failed")


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


@app.get("/api/detection/check", response_model=DetectionCheckResponse)
async def run_detection_check(
    log_query: str = Query("{}", description="LogQL query used for detection scan"),
    log_limit: int = Query(150, ge=10, le=1000),
):
    try:
        snapshot = cluster_poller.get_snapshot()
        return await detection_service.run_check(
            cluster_snapshot=snapshot,
            log_query=log_query,
            log_limit=log_limit,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Detection check failed")
        raise HTTPException(
            status_code=502,
            detail="Detection check failed due to an internal error.",
        ) from exc


@app.get("/api/agents/prompts", response_model=AgentPromptsResponse)
async def get_agent_prompts(ids: Optional[str] = Query(None, description="Comma-separated agent IDs")):
    try:
        agent_ids = [item.strip() for item in ids.split(",")] if ids else []
        agent_ids = [item for item in agent_ids if item]
        prompts = await prompt_store.get_prompts(agent_ids if agent_ids else None)
        return AgentPromptsResponse(
            prompts=[AgentPromptEntry(agent_id=agent_id, prompt=prompt) for agent_id, prompt in prompts.items()]
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Failed to load prompts from Redis: {exc}") from exc


@app.get("/api/agents/workflows/latest", response_model=AgentWorkflowResponse)
async def get_latest_agent_workflow():
    try:
        return await agents_service.get_latest_workflow()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="No active workflow found") from exc
        logger.exception("Failed to query latest workflow")
        raise HTTPException(status_code=502, detail="Failed to query latest workflow") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to query latest workflow")
        raise HTTPException(status_code=502, detail=f"Failed to query latest workflow: {exc}") from exc


@app.get("/api/agents/workflows", response_model=AgentWorkflowListResponse)
async def list_agent_workflows(limit: int = Query(25, ge=1, le=200)):
    try:
        return await agents_service.list_workflows(limit=limit)
    except httpx.HTTPStatusError as exc:
        logger.exception("Failed to query workflow list")
        raise HTTPException(status_code=502, detail="Failed to query workflow list") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to query workflow list")
        raise HTTPException(status_code=502, detail=f"Failed to query workflow list: {exc}") from exc


@app.get("/api/agents/workflows/{workflow_id}", response_model=AgentWorkflowResponse)
async def get_agent_workflow(workflow_id: str):
    try:
        return await agents_service.get_workflow(workflow_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Workflow not found") from exc
        logger.exception("Failed to query workflow %s", workflow_id)
        raise HTTPException(status_code=502, detail="Failed to query workflow") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to query workflow %s", workflow_id)
        raise HTTPException(status_code=502, detail=f"Failed to query workflow: {exc}") from exc


@app.post("/api/agents/orchestrator/chat", response_model=OrchestratorChatResponse)
async def orchestrator_chat(payload: OrchestratorChatRequest):
    try:
        return await agents_service.orchestrator_chat(payload.dict(exclude_none=True))
    except httpx.HTTPStatusError as exc:
        logger.exception("Orchestrator chat failed")
        fallback = "Orchestrator chat failed"
        try:
            body = exc.response.json()
            detail = _upstream_error_detail(body, fallback)
        except Exception:  # pylint: disable=broad-exception-caught
            try:
                detail = (exc.response.text or "").strip() or fallback
            except Exception:  # pylint: disable=broad-exception-caught
                detail = fallback
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.ReadTimeout as exc:
        logger.exception("Orchestrator chat timed out")
        raise HTTPException(
            status_code=504,
            detail=(
                "Orchestrator chat timed out waiting for the agents service (LLM). "
                "Set AGENTS_ORCHESTRATOR_TIMEOUT_SECONDS on the backend deployment if needed, "
                "or ensure OPENROUTER_API_KEY is set on lerna-agents."
            ),
        ) from exc
    except httpx.ConnectError as exc:
        logger.exception("Orchestrator chat upstream unreachable")
        req = getattr(exc, "request", None)
        url = req.url if req is not None else "agents service"
        raise HTTPException(
            status_code=502,
            detail=f"Cannot reach agents service ({url}): {exc}",
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Orchestrator chat failed")
        raise HTTPException(status_code=502, detail=f"Orchestrator chat failed: {exc}") from exc


@app.get("/api/agents/cost-settings", response_model=AgentCostSettingsResponse)
async def get_agent_cost_settings():
    try:
        return await agents_service.get_cost_settings()
    except httpx.HTTPStatusError as exc:
        logger.exception("Failed to query agent cost settings")
        raise HTTPException(status_code=502, detail="Failed to query cost settings") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to query agent cost settings")
        raise HTTPException(status_code=502, detail=f"Failed to query cost settings: {exc}") from exc


@app.put("/api/agents/cost-settings", response_model=AgentCostSettingsResponse)
async def update_agent_cost_settings(payload: AgentCostSettingsUpdateRequest):
    try:
        return await agents_service.update_cost_settings(payload.max_daily_cost)
    except httpx.HTTPStatusError as exc:
        logger.exception("Failed to update agent cost settings")
        raise HTTPException(status_code=502, detail="Failed to update cost settings") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to update agent cost settings")
        raise HTTPException(status_code=502, detail=f"Failed to update cost settings: {exc}") from exc


@app.get("/api/agents/execution-mode", response_model=AgentExecutionModeResponse)
async def get_agent_execution_mode():
    try:
        data = await agents_service.get_execution_mode()
        return AgentExecutionModeResponse(mode=data["mode"])  # type: ignore[arg-type]
    except httpx.HTTPStatusError as exc:
        logger.exception("Failed to query execution mode")
        raise HTTPException(status_code=502, detail="Failed to query execution mode") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to query execution mode")
        raise HTTPException(status_code=502, detail=f"Failed to query execution mode: {exc}") from exc


@app.put("/api/agents/execution-mode", response_model=AgentExecutionModeResponse)
async def update_agent_execution_mode(payload: AgentExecutionModeUpdateRequest):
    try:
        data = await agents_service.update_execution_mode(payload.mode)
        return AgentExecutionModeResponse(mode=data["mode"])  # type: ignore[arg-type]
    except httpx.HTTPStatusError as exc:
        logger.exception("Failed to update execution mode")
        raise HTTPException(status_code=502, detail="Failed to update execution mode") from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to update execution mode")
        raise HTTPException(status_code=502, detail=f"Failed to update execution mode: {exc}") from exc


@app.put("/api/agents/prompts/{agent_id}", response_model=AgentPromptEntry)
async def update_agent_prompt(agent_id: str, payload: AgentPromptUpdateRequest):
    try:
        prompt = payload.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        await prompt_store.set_prompt(agent_id=agent_id, prompt=prompt)
        return AgentPromptEntry(agent_id=agent_id, prompt=prompt)
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Failed to save prompt to Redis: {exc}") from exc


@app.delete("/api/agents/prompts/{agent_id}", response_model=AgentPromptResetResponse)
async def reset_agent_prompt(agent_id: str):
    try:
        await prompt_store.delete_prompt(agent_id=agent_id)
        return AgentPromptResetResponse(agent_id=agent_id, reset=True)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Failed to reset prompt in Redis: {exc}") from exc
