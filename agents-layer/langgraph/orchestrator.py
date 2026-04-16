from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from .agents import _build_chat_model
from .agent_prompts import incident_summary

ORCHESTRATOR_AGENT_PROMPT = """You are the Orchestrator Agent for a Kubernetes incident response system.
Your job is to answer operator questions about incident workflows, current remediation progress, and agent pipeline activity.
Only use the information provided in the workflow and incident context. If no workflow exists, explain that no active incident workflow is currently running.
Be concise, factual, and avoid fabricating steps.
"""


def _build_orchestrator_agent() -> Any:
    return create_react_agent(
        model=_build_chat_model(),
        tools=[],
        prompt=SystemMessage(content=ORCHESTRATOR_AGENT_PROMPT),
        name="OrchestratorAgent",
    )


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

    if workflow.get('started_at'):
        lines.append(f"Started at: {workflow.get('started_at')}")
    if workflow.get('finished_at'):
        lines.append(f"Finished at: {workflow.get('finished_at')}")

    result = workflow.get('result')
    if isinstance(result, dict):
        lines.append("")
        lines.append("Workflow stage outputs:")
        for stage, output in result.items():
            text = output.get('text') if isinstance(output, dict) else str(output)
            lines.append(f"- {stage}: {text.splitlines()[0] if text else 'no output'}")

    return "\n".join(lines)


def build_orchestrator_input(message: str, workflow: dict[str, Any] | None = None) -> str:
    context = _serialize_workflow_context(workflow)
    return "\n".join(
        [
            "Operator message:",
            message,
            "",
            "Current workflow context:",
            context,
            "",
            "Provide a clear response in the voice of the orchestrator."
        ]
    )


def orchestrator_chat(message: str, workflow: dict[str, Any] | None = None) -> dict[str, str]:
    prompt = build_orchestrator_input(message=message, workflow=workflow)
    agent = get_orchestrator_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    if isinstance(result, dict) and "messages" in result:
        content = "\n".join(
            [msg.get("content", "") for msg in result["messages"] if msg.get("role") == "assistant"]
        ).strip()
    else:
        content = str(result)

    return {
        "message": content,
    }
