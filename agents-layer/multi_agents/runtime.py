from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial
from uuid import uuid4

from lerna_shared.detection import AgentTriggerResponse, DetectionIncident
from lerna_agent.incident_report import maybe_generate_and_store_incident_report
from lerna_agent.store import WorkflowStore

from .workflow import run_langgraph_workflow


def _workflow_payload(workflow_id: str, incident: DetectionIncident) -> dict[str, object | None]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return {
        "workflow_id": workflow_id,
        "incident_id": incident.incident_id,
        "cost": incident.cost,
        "status": "running",
        "accepted_at": now,
        "started_at": now,
        "finished_at": None,
        "result": None,
    }


async def execute_incident_workflow(
    incident: DetectionIncident,
    store: WorkflowStore,
    *,
    workflow_id: str,
) -> dict[str, object | None]:
    workflow = _workflow_payload(workflow_id, incident)
    workflow["result"] = {}
    workflow["current_stage"] = None
    await store.save_workflow(workflow_id, workflow)
    try:
        loop = asyncio.get_running_loop()
        prompt_overrides = await store.get_agent_prompts(
            ["filter", "matcher", "diagnosis", "planning", "executor", "validation"]
        )

        async def _save_stage(stage_name: str, stage_output: dict[str, object | None]) -> None:
            current_result = workflow.get("result")
            if not isinstance(current_result, dict):
                current_result = {}
                workflow["result"] = current_result
            current_result[stage_name] = stage_output
            workflow["current_stage"] = stage_name
            await store.save_workflow(workflow_id, workflow)

        def _on_stage_complete(stage_name: str, stage_output: dict[str, object | None]) -> None:
            future = asyncio.run_coroutine_threadsafe(_save_stage(stage_name, stage_output), loop)
            future.result(timeout=15)

        execution_mode = await store.get_execution_mode()
        result = await asyncio.to_thread(
            run_langgraph_workflow,
            incident,
            _on_stage_complete,
            prompt_overrides,
            execution_mode=execution_mode,
        )
        workflow["status"] = "completed"
        workflow["result"] = result
        workflow["current_stage"] = "completed"
        report_bundle = await asyncio.to_thread(
            partial(
                maybe_generate_and_store_incident_report,
                incident,
                workflow_id,
                "langgraph",
                result,
            ),
        )
        if report_bundle is not None:
            workflow["incident_report"] = report_bundle
        lg_usage = result.get("api_usage") if isinstance(result, dict) else {}
        if not isinstance(lg_usage, dict):
            lg_usage = {}
        total_usd = float(lg_usage.get("cost_usd") or 0)
        if report_bundle:
            ru = report_bundle.get("api_usage") or {}
            total_usd += float(ru.get("cost_usd") or 0)
        workflow["api_usage"] = {
            "langgraph": lg_usage,
            "reporter": (report_bundle or {}).get("api_usage"),
        }
        workflow["api_cost_usd"] = round(total_usd, 6)
        workflow["cost"] = workflow["api_cost_usd"]
        if total_usd > 0:
            await store.add_daily_spend(total_usd)
    except Exception as exc:  # pylint: disable=broad-except
        workflow["status"] = "failed"
        # Keep `result` as a dict so the backend response schema remains valid.
        workflow["result"] = {"error": str(exc)}
        workflow["current_stage"] = "failed"
    workflow["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    await store.save_workflow(workflow_id, workflow)
    return workflow


async def accept_incident(
    incident: DetectionIncident,
    store: WorkflowStore,
) -> AgentTriggerResponse:
    existing = await store.get_workflow_for_incident(incident.incident_id)
    if existing:
        return AgentTriggerResponse(
            accepted=True,
            workflow_id=existing["workflow_id"],
            status=existing["status"],
        )

    workflow_id = f"lg-{uuid4().hex[:12]}"
    await store.bind_incident(incident.incident_id, workflow_id)
    initial = {
        "workflow_id": workflow_id,
        "incident_id": incident.incident_id,
        "cost": incident.cost,
        "status": "accepted",
        "accepted_at": datetime.now(tz=timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
    }
    await store.save_workflow(workflow_id, initial)
    asyncio.create_task(execute_incident_workflow(incident, store, workflow_id=workflow_id))
    return AgentTriggerResponse(accepted=True, workflow_id=workflow_id, status="accepted")
