from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict
from uuid import uuid4

logger = logging.getLogger(__name__)

from lerna_shared.detection import AgentTriggerResponse, DetectionIncident

from .agent import LernaAgent
from .incident_report import maybe_generate_and_store_incident_report
from .store import WorkflowStore


def _incident_prompt(incident: DetectionIncident) -> str:
    evidence_lines = [
        f"- [{item.severity}] {item.source}: {item.message}"
        for item in incident.evidence[:8]
    ]
    return "\n".join(
        [
            "Investigate this detected Kubernetes incident and propose the next remediation steps.",
            f"Incident ID: {incident.incident_id}",
            f"Service: {incident.service}",
            f"Namespace: {incident.namespace}",
            f"Severity: {incident.severity}",
            f"Summary: {incident.summary}",
            f"Incident class: {incident.incident_class}",
            "Evidence:",
            *evidence_lines,
        ]
    )


async def execute_incident_workflow(
    incident: DetectionIncident,
    store: WorkflowStore,
    *,
    workflow_id: str,
    model: str | None = None,
) -> Dict[str, Any]:
    started_at = datetime.now(tz=timezone.utc).isoformat()
    workflow = {
        "workflow_id": workflow_id,
        "incident_id": incident.incident_id,
        "cost": incident.cost,
        "status": "running",
        "accepted_at": started_at,
        "started_at": started_at,
        "finished_at": None,
        "result": None,
    }
    await store.save_workflow(workflow_id, workflow)
    logger.info(
        "Agents: workflow %s running for incident %s (%s/%s)",
        workflow_id,
        incident.incident_id,
        incident.namespace,
        incident.service,
    )
    try:
        agent = LernaAgent(model=model)
        outcome = await asyncio.to_thread(agent.run, _incident_prompt(incident))
        workflow["status"] = "completed"
        workflow["result"] = outcome.text
        total_usd = float(outcome.cost_usd)
        workflow["api_usage"] = {
            "workflow": {
                "prompt_tokens": outcome.prompt_tokens,
                "completion_tokens": outcome.completion_tokens,
                "model": outcome.model,
                "cost_usd": round(outcome.cost_usd, 6),
            },
        }
        report_bundle = await asyncio.to_thread(
            partial(
                maybe_generate_and_store_incident_report,
                incident,
                workflow_id,
                "single",
                outcome.text,
                model=model,
            ),
        )
        if report_bundle is not None:
            workflow["incident_report"] = report_bundle
            reporter_u = report_bundle.get("api_usage") or {}
            total_usd += float(reporter_u.get("cost_usd") or 0)
            workflow["api_usage"]["reporter"] = reporter_u
        workflow["api_cost_usd"] = round(total_usd, 6)
        # Keep legacy `cost` aligned with measured spend (was incident.cost hint only).
        workflow["cost"] = workflow["api_cost_usd"]
        if total_usd > 0:
            await store.add_daily_spend(total_usd)
        logger.info("Agents: workflow %s completed (incident %s)", workflow_id, incident.incident_id)
    except Exception as exc:  # pylint: disable=broad-except
        workflow["status"] = "failed"
        # Keep `result` as a dict so API response validation stays stable.
        workflow["result"] = {"error": str(exc)}
        logger.warning(
            "Agents: workflow %s failed for incident %s: %s",
            workflow_id,
            incident.incident_id,
            exc,
            exc_info=True,
        )
    workflow["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    await store.save_workflow(workflow_id, workflow)
    return workflow


async def accept_incident(
    incident: DetectionIncident,
    store: WorkflowStore,
) -> AgentTriggerResponse:
    existing = await store.get_workflow_for_incident(incident.incident_id)
    if existing:
        logger.info(
            "Agents: duplicate incident %s — existing workflow %s status=%s",
            incident.incident_id,
            existing["workflow_id"],
            existing["status"],
        )
        return AgentTriggerResponse(
            accepted=True,
            workflow_id=existing["workflow_id"],
            status=existing["status"],
        )

    workflow_id = f"wf-{uuid4().hex[:12]}"
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
    await store.bind_incident(incident.incident_id, workflow_id)
    await store.save_workflow(workflow_id, initial)
    logger.info(
        "Agents: accepted incident %s workflow=%s class=%s",
        incident.incident_id,
        workflow_id,
        incident.incident_class,
    )
    asyncio.create_task(execute_incident_workflow(incident, store, workflow_id=workflow_id))
    return AgentTriggerResponse(accepted=True, workflow_id=workflow_id, status="accepted")


def manual_incident_from_message(message: str) -> DetectionIncident:
    now = datetime.now(tz=timezone.utc).isoformat()
    return DetectionIncident(
        incident_id=f"manual-{uuid4().hex[:12]}",
        fingerprint=uuid4().hex,
        detected_at=now,
        service="manual-input",
        namespace="default",
        severity="warning",
        summary=message,
        evidence=[],
        cluster_snapshot=None,
        incident_class="manual-investigation",
        dominant_signature=message[:160],
        correlation={},
    )
