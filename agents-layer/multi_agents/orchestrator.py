from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .agents import _build_chat_model
from .agent_prompts import incident_summary

ORCHESTRATOR_AGENT_PROMPT = """You are the Orchestrator Agent for a Kubernetes incident response system.
Your job is to answer operator questions about incident workflows, current remediation progress, and agent pipeline activity.
Only use the information provided in the workflow and incident context. If no workflow exists, explain that no active incident workflow is currently running.
Prefer direct answers. When the operator asks for status, summarize the workflow state, current stage, recent stage outputs, blockers, and next safe action.
If the requested information is missing, say exactly what is missing instead of guessing.
Be concise, factual, and avoid fabricating steps.
"""


def _build_orchestrator_agent() -> Any:
    model = _build_chat_model()

    class _OrchestratorAgent:
        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            messages = [SystemMessage(content=ORCHESTRATOR_AGENT_PROMPT)]
            for message in payload.get("messages", []):
                content = str(message.get("content", ""))
                role = str(message.get("role", "user"))
                if role == "assistant":
                    messages.append(AIMessage(content=content))
                elif role == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

            result = model.invoke(messages)
            return {
                "messages": [
                    *payload.get("messages", []),
                    {
                        "role": "assistant",
                        "content": result.content if isinstance(result.content, str) else str(result.content),
                    },
                ]
            }

    return _OrchestratorAgent()


@lru_cache(maxsize=None)
def get_orchestrator_agent() -> Any:
    return _build_orchestrator_agent()


def _serialize_workflow_context(workflow: dict[str, Any] | None) -> str:
    if not workflow:
        return "No active workflow context is available."

    lines: list[str] = [
        f"Workflow ID: {workflow.get('workflow_id')}",
        f"Incident ID: {workflow.get('incident_id')}",
        f"Status: {workflow.get('status')}",
        f"Accepted at: {workflow.get('accepted_at')}",
    ]

    if workflow.get("cost") is not None:
        lines.append(f"Estimated cost: {workflow.get('cost')}")
    if workflow.get("current_stage") is not None:
        lines.append(f"Current stage: {workflow.get('current_stage')}")

    if workflow.get('started_at'):
        lines.append(f"Started at: {workflow.get('started_at')}")
    if workflow.get('finished_at'):
        lines.append(f"Finished at: {workflow.get('finished_at')}")

    result = workflow.get('result')
    if isinstance(result, dict):
        lines.append("")
        lines.append("Workflow stage outputs:")
        for stage, output in result.items():
            if isinstance(output, dict):
                text = output.get('text')
                started_at = output.get("started_at")
                finished_at = output.get("finished_at")
                tool_calls = output.get("tool_calls")
                summary = text.splitlines()[0] if isinstance(text, str) and text else "no output"
                metadata: list[str] = []
                if started_at:
                    metadata.append(f"started={started_at}")
                if finished_at:
                    metadata.append(f"finished={finished_at}")
                if isinstance(tool_calls, list):
                    metadata.append(f"tool_calls={len(tool_calls)}")
                suffix = f" ({', '.join(metadata)})" if metadata else ""
                lines.append(f"- {stage}: {summary}{suffix}")
            else:
                lines.append(f"- {stage}: {output}")

    error = None
    if isinstance(result, dict):
        raw_error = result.get("error")
        if raw_error:
            error = str(raw_error)
    if error:
        lines.append("")
        lines.append(f"Workflow error: {error}")

    return "\n".join(lines)


def build_orchestrator_input(
    message: str,
    workflow: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str:
    context = _serialize_workflow_context(workflow)
    lines = [
        "Current workflow context:",
        context,
    ]
    if history:
        lines.extend(["", "Conversation history:"])
        for item in history[-8:]:
            role = str(item.get("role", "user")).upper()
            content = str(item.get("content", "")).strip()
            if content:
                lines.append(f"{role}: {content}")
    lines.extend(
        [
            "",
            "Latest operator message:",
            message,
            "",
            "Provide a clear response in the voice of the orchestrator.",
        ]
    )
    return "\n".join(lines)


def orchestrator_chat(
    message: str,
    workflow: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    prompt = build_orchestrator_input(message=message, workflow=workflow, history=history)
    agent = get_orchestrator_agent()
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        if isinstance(result, dict) and "messages" in result:
            content = "\n".join(
                [
                    msg.get("content", "")
                    for msg in result["messages"]
                    if msg.get("role") == "assistant"
                ]
            ).strip()
        else:
            content = str(result)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raw = str(exc)
        lower = raw.lower()
        if "rate limit" in lower or "free-models-per-day" in lower or "error code: 429" in lower:
            content = (
                "Orchestrator model rate limit reached (HTTP 429: free-models-per-day). "
                "Please wait until the daily limit resets, or configure `LERNA_AGENT_MODEL` "
                "to a non-free model / add credits, then try again."
            )
        elif "402" in lower or "credits" in lower or "insufficient" in lower:
            content = (
                "Orchestrator model credits are insufficient (HTTP 402). "
                "Add credits in OpenRouter (or reduce token usage by setting `LERNA_AGENT_MAX_TOKENS`) "
                "and try again."
            )
        elif "api key" in lower or "openrouter_api_key" in lower or "openrouter" in lower and "key" in lower:
            content = (
                "Orchestrator model API key is not configured. "
                "Set `OPENROUTER_API_KEY` (and `OPENROUTER_BASE_URL` if needed) and retry."
            )
        else:
            content = f"Orchestrator chat failed: {raw}"

    return {
        "message": content,
    }
