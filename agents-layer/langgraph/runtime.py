from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from lerna_shared.detection import AgentTriggerResponse, DetectionIncident
from lerna_agent.store import WorkflowStore

from .workflow import run_langgraph_workflow


def _workflow_payload(workflow_id: str, incident: DetectionIncident) -> dict[str, object | None]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return {
        "workflow_id": workflow_id,
        "incident_id": incident.incident_id,
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
    await store.save_workflow(workflow_id, workflow)
    try:
        result = await asyncio.to_thread(run_langgraph_workflow, incident)
        workflow["status"] = "completed"
        workflow["result"] = result
    except Exception as exc:  # pylint: disable=broad-except
        workflow["status"] = "failed"
        workflow["result"] = str(exc)
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
        "status": "accepted",
        "accepted_at": datetime.now(tz=timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
    }
    await store.save_workflow(workflow_id, initial)
    asyncio.create_task(execute_incident_workflow(incident, store, workflow_id=workflow_id))
    return AgentTriggerResponse(accepted=True, workflow_id=workflow_id, status="accepted")
