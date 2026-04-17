from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from lerna_shared.detection import DetectionIncident

# Cap stored transcript size in Redis / API payloads
_MAX_TRANSCRIPT_CHARS = 14_000

from .agent_prompts import build_agent_input
from .agents import (
    get_diagnosis_agent,
    get_executor_agent,
    get_filter_agent,
    get_incident_matcher_agent,
    get_planning_agent,
    get_validation_agent,
)


def _assistant_content_from_message(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(str(item["text"]))
                elif "text" in item:
                    parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content).strip()


def _final_assistant_summary(messages: Any) -> str:
    """Last assistant message with non-empty text — the model's final narrative after tools."""
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        text = _assistant_content_from_message(message)
        if text:
            return text
    return ""


def _extract_text_from_agent_output(output: Any) -> str:
    if isinstance(output, dict) and "messages" in output:
        parts = []
        for message in output["messages"]:
            if hasattr(message, "get"):
                role = message.get("role", "unknown")
                content = message.get("content", "")
            else:
                role = getattr(message, "role", "unknown")
                content = getattr(message, "content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)
    return str(output)


def _extract_tool_calls(output: Any) -> list[dict[str, str]]:
    if not isinstance(output, dict):
        return []
    raw_messages = output.get("messages")
    if not isinstance(raw_messages, list):
        return []

    tool_results_by_id: dict[str, str] = {}
    for message in raw_messages:
        if hasattr(message, "get"):
            role = message.get("role")
            tool_call_id = message.get("tool_call_id")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", None)
            tool_call_id = getattr(message, "tool_call_id", None)
            content = getattr(message, "content", "")
        if role == "tool" and tool_call_id:
            tool_results_by_id[str(tool_call_id)] = str(content)

    calls: list[dict[str, str]] = []
    for message in raw_messages:
        if hasattr(message, "get"):
            role = message.get("role")
            tool_calls = message.get("tool_calls")
        else:
            role = getattr(message, "role", None)
            tool_calls = getattr(message, "tool_calls", None)
        if role != "assistant" or not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            if hasattr(call, "get"):
                call_id = str(call.get("id", ""))
                fn = call.get("function", {}) if isinstance(call.get("function"), dict) else None
                if isinstance(fn, dict):
                    name = str(fn.get("name", "unknown_tool"))
                    arguments = str(fn.get("arguments", ""))
                else:
                    name = str(call.get("name", "unknown_tool"))
                    args = call.get("args", call.get("arguments", ""))
                    if isinstance(args, (dict, list)):
                        arguments = json.dumps(args, default=str)
                    else:
                        arguments = str(args)
            else:
                call_id = str(getattr(call, "id", ""))
                function_data = getattr(call, "function", None)
                if function_data is not None:
                    name = str(getattr(function_data, "name", "unknown_tool"))
                    arguments = str(getattr(function_data, "arguments", ""))
                else:
                    name = str(getattr(call, "name", "unknown_tool"))
                    args = getattr(call, "args", getattr(call, "arguments", ""))
                    if isinstance(args, (dict, list)):
                        arguments = json.dumps(args, default=str)
                    else:
                        arguments = str(args)
            calls.append(
                {
                    "id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "result": tool_results_by_id.get(call_id, ""),
                }
            )
    return calls


def _run_agent(agent: Any, prompt: str) -> dict[str, Any]:
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    usage = result.get("usage") if isinstance(result, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    full_transcript = _extract_text_from_agent_output(result)
    messages = result.get("messages") if isinstance(result, dict) else None
    summary = _final_assistant_summary(messages) if isinstance(messages, list) else ""
    if not summary.strip():
        summary = full_transcript.strip()[:4000]
    transcript = full_transcript.strip()
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:_MAX_TRANSCRIPT_CHARS] + "\n…(truncated)"
    return {
        "text": summary.strip(),
        "transcript": transcript,
        "tool_calls": _extract_tool_calls(result),
        "usage": usage,
    }


def _aggregate_langgraph_api_usage(outputs: dict[str, Any]) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    cost_usd = 0.0
    model = ""
    for key in ("filter", "matcher", "diagnosis", "planning", "executor", "validation"):
        stage = outputs.get(key)
        if not isinstance(stage, dict):
            continue
        u = stage.get("usage") or {}
        prompt_tokens += int(u.get("prompt_tokens") or 0)
        completion_tokens += int(u.get("completion_tokens") or 0)
        cost_usd += float(u.get("cost_usd") or 0.0)
        if u.get("model"):
            model = str(u["model"])
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": round(cost_usd, 6),
        "model": model,
    }


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def run_langgraph_workflow(
    incident: DetectionIncident,
    on_stage_complete: Any | None = None,
    prompt_overrides: dict[str, str] | None = None,
    *,
    execution_mode: str = "autonomous",
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    prompt_overrides = prompt_overrides or {}
    mode = (execution_mode or "autonomous").strip().lower()
    if mode not in ("autonomous", "advisory", "paused"):
        mode = "autonomous"
    # "paused" only blocks automatic detection; manual runs use full executor unless advisory.
    executor_mode = "advisory" if mode == "advisory" else "autonomous"

    filter_prompt = build_agent_input(incident, stage_name="Filter", previous_outputs=None)
    filter_started = _utc_now_iso()
    filter_output = _run_agent(get_filter_agent(prompt_overrides.get("filter")), filter_prompt)
    outputs["filter"] = {
        **filter_output,
        "stage": "filter",
        "started_at": filter_started,
        "finished_at": _utc_now_iso(),
    }
    if on_stage_complete:
        on_stage_complete("filter", outputs["filter"])

    # Graph-style branching:
    # - After Filter, Orchestrator runs Incident Matcher and Diagnosis in parallel.
    # - Planning then consumes both outputs.
    filter_text = outputs["filter"]["text"]

    matcher_prompt = build_agent_input(
        incident,
        stage_name="Incident Matching",
        previous_outputs={"filter": filter_text},
    )
    diagnosis_prompt = build_agent_input(
        incident,
        stage_name="Diagnosis",
        previous_outputs={"filter": filter_text},
    )

    matcher_started = _utc_now_iso()
    diagnosis_started = _utc_now_iso()

    def _run_matcher() -> dict[str, Any]:
        return _run_agent(get_incident_matcher_agent(prompt_overrides.get("matcher")), matcher_prompt)

    def _run_diagnosis() -> dict[str, Any]:
        return _run_agent(get_diagnosis_agent(prompt_overrides.get("diagnosis")), diagnosis_prompt)

    with ThreadPoolExecutor(max_workers=2) as executor:
        matcher_future = executor.submit(_run_matcher)
        diagnosis_future = executor.submit(_run_diagnosis)

        matcher_output = matcher_future.result()
        outputs["matcher"] = {
            **matcher_output,
            "stage": "matcher",
            "started_at": matcher_started,
            "finished_at": _utc_now_iso(),
        }
        if on_stage_complete:
            on_stage_complete("matcher", outputs["matcher"])

        diagnosis_output = diagnosis_future.result()
        outputs["diagnosis"] = {
            **diagnosis_output,
            "stage": "diagnosis",
            "started_at": diagnosis_started,
            "finished_at": _utc_now_iso(),
        }
        if on_stage_complete:
            on_stage_complete("diagnosis", outputs["diagnosis"])

    planning_prompt = build_agent_input(
        incident,
        stage_name="Planning",
        previous_outputs={
            "filter": outputs["filter"]["text"],
            "matcher": outputs["matcher"]["text"],
            "diagnosis": outputs["diagnosis"]["text"],
        },
    )
    planning_started = _utc_now_iso()
    planning_output = _run_agent(get_planning_agent(prompt_overrides.get("planning")), planning_prompt)
    outputs["planning"] = {
        **planning_output,
        "stage": "planning",
        "started_at": planning_started,
        "finished_at": _utc_now_iso(),
    }
    if on_stage_complete:
        on_stage_complete("planning", outputs["planning"])

    executor_prompt = build_agent_input(
        incident,
        stage_name="Execution",
        previous_outputs={
            "planning": outputs["planning"]["text"],
        },
    )
    executor_started = _utc_now_iso()
    executor_output = _run_agent(
        get_executor_agent(prompt_overrides.get("executor"), executor_mode),
        executor_prompt,
    )
    outputs["executor"] = {
        **executor_output,
        "stage": "executor",
        "started_at": executor_started,
        "finished_at": _utc_now_iso(),
    }
    if on_stage_complete:
        on_stage_complete("executor", outputs["executor"])

    validation_prompt = build_agent_input(
        incident,
        stage_name="Validation",
        previous_outputs={
            "executor": outputs["executor"]["text"],
        },
    )
    validation_started = _utc_now_iso()
    validation_output = _run_agent(get_validation_agent(prompt_overrides.get("validation")), validation_prompt)
    outputs["validation"] = {
        **validation_output,
        "stage": "validation",
        "started_at": validation_started,
        "finished_at": _utc_now_iso(),
    }
    if on_stage_complete:
        on_stage_complete("validation", outputs["validation"])

    outputs["api_usage"] = _aggregate_langgraph_api_usage(outputs)
    return outputs
