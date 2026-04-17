"""Post-workflow incident report: LLM summary + Qdrant vector upsert for incident memory."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

from openai import OpenAI

from lerna_shared.detection import DetectionIncident
from lerna_shared.usage_pricing import extract_usage_from_openai_completion, usd_cost_for_token_usage

from tools.qdrant_memory import qdrant_upsert_incident_memory

logger = logging.getLogger(__name__)

WORKFLOW_CONTEXT_MAX = 100_000

REPORTER_SYSTEM = """You are an incident documentation specialist for Kubernetes and observability.
Write a concise operational incident report in Markdown.

Required sections (use these headings):
## Summary
## Symptoms and impact
## Likely root cause
## Actions taken (investigation and any remediation discussed)
## Validation or outcome
## Follow-ups and monitoring

Rules:
- Base the report only on the incident metadata and workflow outputs provided by the user.
- If something is unknown or not present in the inputs, say so explicitly.
- Do not invent metrics, log lines, or commands that do not appear in the workflow text.
- Prefer clarity over length."""


def _reporter_enabled() -> bool:
    raw = os.getenv("LERNA_INCIDENT_REPORT_TO_QDRANT", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _default_reporter_model() -> str:
    return (
        os.getenv("LERNA_REPORTER_MODEL", "").strip()
        or os.getenv("LERNA_AGENT_MODEL", "").strip()
        or "gpt-4.1-nano-2025-04-14"
    )


def _openai_client() -> OpenAI:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set; required for incident report generation")
    kwargs: Dict[str, Any] = {"api_key": key}
    base = os.getenv("OPENROUTER_BASE_URL", "").strip()
    if base:
        kwargs["base_url"] = base
    return OpenAI(**kwargs)


def format_workflow_transcript(incident: DetectionIncident, workflow_result: Any) -> str:
    """Flatten incident + workflow outputs into one user message for the reporter model."""
    lines = [
        "### Incident metadata",
        f"- incident_id: {incident.incident_id}",
        f"- service: {incident.service}",
        f"- namespace: {incident.namespace}",
        f"- severity: {incident.severity}",
        f"- incident_class: {incident.incident_class}",
        f"- summary: {incident.summary}",
        f"- dominant_signature: {incident.dominant_signature}",
        "",
        "### Workflow output",
    ]
    if isinstance(workflow_result, str):
        lines.append(workflow_result)
    elif isinstance(workflow_result, dict):
        for key in ("filter", "matcher", "diagnosis", "planning", "executor", "validation"):
            if key not in workflow_result:
                continue
            stage = workflow_result[key]
            text = stage.get("text", "") if isinstance(stage, dict) else str(stage)
            lines.append(f"\n#### {key}\n\n{text}")
    else:
        lines.append(str(workflow_result))
    out = "\n".join(lines)
    if len(out) > WORKFLOW_CONTEXT_MAX:
        return out[:WORKFLOW_CONTEXT_MAX] + "\n\n[... truncated ...]"
    return out


def generate_incident_report_markdown(
    incident: DetectionIncident,
    workflow_result: Any,
    *,
    model: Optional[str] = None,
) -> tuple[str, Dict[str, Any]]:
    user_content = format_workflow_transcript(incident, workflow_result)
    client = _openai_client()
    use_model = model or _default_reporter_model()
    response = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": REPORTER_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Incident reporter returned empty content")
    pt, ct, mid = extract_usage_from_openai_completion(response)
    model_id = mid or use_model
    cost_usd = usd_cost_for_token_usage(model_id, pt, ct)
    usage = {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "model": model_id,
        "cost_usd": round(cost_usd, 6),
    }
    return text, usage


def save_report_to_qdrant(
    incident: DetectionIncident,
    workflow_id: str,
    workflow_engine: str,
    report_markdown: str,
) -> Dict[str, Any]:
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"lerna:{workflow_id}"))
    payload: Dict[str, Any] = {
        "incident_id": incident.incident_id,
        "workflow_id": workflow_id,
        "workflow_engine": workflow_engine,
        "service": incident.service,
        "namespace": incident.namespace,
        "severity": incident.severity,
        "incident_class": incident.incident_class,
        "summary": incident.summary[:4000],
        "report_markdown": report_markdown[:50000],
    }
    embedding_text = "\n".join(
        [
            incident.summary,
            incident.incident_class,
            incident.namespace,
            incident.service,
            report_markdown[:12000],
        ]
    )
    return qdrant_upsert_incident_memory(embedding_text, payload, point_id)


def maybe_generate_and_store_incident_report(
    incident: DetectionIncident,
    workflow_id: str,
    workflow_engine: str,
    workflow_result: Any,
    *,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    If enabled, synthesize a Markdown report and upsert it into Qdrant for similar-incident search.
    Returns None when disabled; otherwise a dict with report and/or error keys (never raises).
    """
    if not _reporter_enabled():
        return None
    try:
        report, report_usage = generate_incident_report_markdown(incident, workflow_result, model=model)
        qdr = save_report_to_qdrant(incident, workflow_id, workflow_engine, report)
        if not qdr.get("ok"):
            logger.warning("Incident report generated but Qdrant upsert failed: %s", qdr.get("error"))
        return {"report_markdown": report, "qdrant": qdr, "api_usage": report_usage}
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Incident report generation or storage failed")
        return {"error": str(exc)}
