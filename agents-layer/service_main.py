from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv_if_present() -> None:
    """Load agents-layer/.env (or project root .env) for local runs.
    In Kubernetes use Secret envFrom; .env is not in the image."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    # First try the agents-layer local .env, then fall back to the project-root .env.
    service_env = Path(__file__).resolve().parent / ".env"
    root_env = Path(__file__).resolve().parent.parent / ".env"
    for env_path in (service_env, root_env):
        if env_path.is_file():
            # Do not override real process env (e.g. K8s-injected secrets).
            load_dotenv(env_path, override=False)
            break


_load_dotenv_if_present()

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from lerna_shared.detection import AgentTriggerResponse, DetectionIncident

from lerna_agent.runtime import accept_incident
from lerna_agent.store import WorkflowStore
from multi_agents.runtime import accept_incident as accept_langgraph_incident
from multi_agents.orchestrator import orchestrator_chat

_pkg_log = logging.getLogger("lerna_agent")
_pkg_log.setLevel(logging.INFO)
if not _pkg_log.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _pkg_log.addHandler(_h)
    _pkg_log.propagate = False

workflow_store = WorkflowStore()
_WORKFLOW_ENGINE_RAW = os.getenv("LERNA_WORKFLOW_ENGINE", "single").strip().lower()
_USE_LANGGRAPH_ENGINE = _WORKFLOW_ENGINE_RAW in {"langgraph", "multi", "multi-agent", "multi_agents"}
# Pre-flight budget only; measured LLM spend is added when each workflow finishes.
_BUDGET_START_RESERVE_USD = float(os.getenv("LERNA_BUDGET_START_RESERVE_USD", "5.0"))


async def _accept_incident_with_config(payload: DetectionIncident) -> AgentTriggerResponse:
    if _USE_LANGGRAPH_ENGINE:
        return await accept_langgraph_incident(payload, workflow_store)
    return await accept_incident(payload, workflow_store)


class CostSettingsRequest(BaseModel):
    """Set daily cap in USD, or null / omit to remove the cap (unlimited)."""

    max_daily_cost: float | None = Field(default=None)

    @field_validator("max_daily_cost")
    @classmethod
    def _non_negative(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("max_daily_cost must be >= 0 when set")
        return v


class CostSettingsResponse(BaseModel):
    max_daily_cost: float | None
    spent_today: float
    remaining_today: float | None


AgentExecutionMode = Literal["autonomous", "advisory", "paused"]


class ExecutionModeResponse(BaseModel):
    mode: AgentExecutionMode


class ExecutionModePayload(BaseModel):
    mode: AgentExecutionMode


async def _cost_snapshot() -> CostSettingsResponse:
    max_daily_cost = await workflow_store.get_max_daily_cost()
    spent_today = await workflow_store.get_daily_spend()
    remaining_today = None if max_daily_cost is None else max(0.0, max_daily_cost - spent_today)
    return CostSettingsResponse(
        max_daily_cost=max_daily_cost,
        spent_today=spent_today,
        remaining_today=remaining_today,
    )


async def _ensure_budget_allows(cost: float) -> None:
    snapshot = await _cost_snapshot()
    max_daily_cost = snapshot.max_daily_cost
    if max_daily_cost is None:
        return
    projected_spend = snapshot.spent_today + cost
    if projected_spend <= max_daily_cost:
        return
    raise HTTPException(
        status_code=429,
        detail={
            "error": "DAILY_COST_LIMIT_REACHED",
            "message": "Daily max cost reached. Agents will not execute until the limit is increased or a new day starts.",
            "max_daily_cost": max_daily_cost,
            "spent_today": snapshot.spent_today,
            "start_reserve_usd": cost,
            "projected_spend": projected_spend,
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await workflow_store.close()


app = FastAPI(title="Lerna Agents Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/incidents", response_model=AgentTriggerResponse)
async def create_incident_workflow(payload: DetectionIncident) -> AgentTriggerResponse:
    try:
        existing = await workflow_store.get_workflow_for_incident(payload.incident_id)
        is_new_incident = existing is None
        if is_new_incident:
            await _ensure_budget_allows(_BUDGET_START_RESERVE_USD)
        response = await _accept_incident_with_config(payload)
        return response
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Failed to start incident workflow: {exc}") from exc


@app.post("/langgraph-incidents", response_model=AgentTriggerResponse)
async def create_langgraph_incident_workflow(payload: DetectionIncident) -> AgentTriggerResponse:
    try:
        existing = await workflow_store.get_workflow_for_incident(payload.incident_id)
        is_new_incident = existing is None
        if is_new_incident:
            await _ensure_budget_allows(_BUDGET_START_RESERVE_USD)
        response = await accept_langgraph_incident(payload, workflow_store)
        return response
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Failed to start LangGraph incident workflow: {exc}") from exc


@app.get("/cost-settings", response_model=CostSettingsResponse)
async def get_cost_settings() -> CostSettingsResponse:
    return await _cost_snapshot()


@app.put("/cost-settings", response_model=CostSettingsResponse)
async def update_cost_settings(payload: CostSettingsRequest) -> CostSettingsResponse:
    await workflow_store.set_max_daily_cost(payload.max_daily_cost)
    return await _cost_snapshot()


@app.get("/execution-mode", response_model=ExecutionModeResponse)
async def get_execution_mode() -> ExecutionModeResponse:
    m = await workflow_store.get_execution_mode()
    return ExecutionModeResponse(mode=m)  # type: ignore[arg-type]


@app.put("/execution-mode", response_model=ExecutionModeResponse)
async def put_execution_mode(payload: ExecutionModePayload) -> ExecutionModeResponse:
    m = await workflow_store.set_execution_mode(payload.mode)
    return ExecutionModeResponse(mode=m)  # type: ignore[arg-type]


@app.get("/workflows/latest")
async def get_latest_workflow():
    workflow = await workflow_store.get_last_workflow()
    if not workflow:
        raise HTTPException(status_code=404, detail="No workflow found")
    return workflow


@app.get("/workflows")
async def list_workflows(limit: int = Query(25, ge=1, le=200)):
    return {"workflows": await workflow_store.list_workflows(limit=limit)}


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    workflow = await workflow_store.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.post("/orchestrator/chat")
async def chat_with_orchestrator(payload: dict):
    try:
        workflow_id = payload.get("workflow_id")
        incident_id = payload.get("incident_id")
        history = payload.get("messages")
        workflow = None
        if workflow_id:
            workflow = await workflow_store.get_workflow(workflow_id)
        elif incident_id:
            workflow = await workflow_store.get_workflow_for_incident(incident_id)

        response = orchestrator_chat(
            payload.get("message", ""),
            workflow=workflow,
            history=history if isinstance(history, list) else None,
        )
        return response
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=502, detail=f"Orchestrator chat failed: {exc}") from exc
