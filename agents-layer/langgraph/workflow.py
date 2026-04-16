from __future__ import annotations

from typing import Any

from lerna_shared.detection import DetectionIncident

from .agent_prompts import build_agent_input
from .agents import (
    get_diagnosis_agent,
    get_executor_agent,
    get_filter_agent,
    get_incident_matcher_agent,
    get_planning_agent,
    get_validation_agent,
)


def _extract_text_from_agent_output(output: Any) -> str:
    if isinstance(output, dict) and "messages" in output:
        parts = []
        for message in output["messages"]:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)
    return str(output)


def _run_agent(agent: Any, prompt: str) -> dict[str, Any]:
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return {
        "raw": result,
        "text": _extract_text_from_agent_output(result),
    }


def run_langgraph_workflow(incident: DetectionIncident) -> dict[str, Any]:
    outputs: dict[str, Any] = {}

    filter_prompt = build_agent_input(incident, stage_name="Filter", previous_outputs=None)
    outputs["filter"] = _run_agent(get_filter_agent(), filter_prompt)

    matcher_prompt = build_agent_input(
        incident,
        stage_name="Incident Matching",
        previous_outputs={"filter": outputs["filter"]["text"]},
    )
    outputs["matcher"] = _run_agent(get_incident_matcher_agent(), matcher_prompt)

    diagnosis_prompt = build_agent_input(
        incident,
        stage_name="Diagnosis",
        previous_outputs={
            "filter": outputs["filter"]["text"],
            "matcher": outputs["matcher"]["text"],
        },
    )
    outputs["diagnosis"] = _run_agent(get_diagnosis_agent(), diagnosis_prompt)

    planning_prompt = build_agent_input(
        incident,
        stage_name="Planning",
        previous_outputs={
            "filter": outputs["filter"]["text"],
            "matcher": outputs["matcher"]["text"],
            "diagnosis": outputs["diagnosis"]["text"],
        },
    )
    outputs["planning"] = _run_agent(get_planning_agent(), planning_prompt)

    executor_prompt = build_agent_input(
        incident,
        stage_name="Execution",
        previous_outputs={
            "planning": outputs["planning"]["text"],
        },
    )
    outputs["executor"] = _run_agent(get_executor_agent(), executor_prompt)

    validation_prompt = build_agent_input(
        incident,
        stage_name="Validation",
        previous_outputs={
            "executor": outputs["executor"]["text"],
        },
    )
    outputs["validation"] = _run_agent(get_validation_agent(), validation_prompt)

    return outputs
