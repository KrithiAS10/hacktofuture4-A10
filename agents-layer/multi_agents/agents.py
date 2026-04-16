from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from .agent_prompts import (
    DIAGNOSIS_AGENT_PROMPT,
    EXECUTOR_AGENT_PROMPT,
    FILTER_AGENT_PROMPT,
    MATCHER_AGENT_PROMPT,
    PLANNING_AGENT_PROMPT,
    VALIDATION_AGENT_PROMPT,
)
from .toolset import (
    DIAGNOSIS_AGENT_TOOLS,
    EXECUTOR_AGENT_TOOLS,
    FILTER_AGENT_TOOLS,
    MATCHER_AGENT_TOOLS,
    PLANNING_AGENT_TOOLS,
    TOOL_CALLABLES,
    VALIDATION_AGENT_TOOLS,
    build_toolset,
)

DEFAULT_MODEL_NAME = os.getenv("LERNA_AGENT_MODEL", "gpt-4.1-nano-2025-04-14")
DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
DEFAULT_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
DEFAULT_MAX_TOOL_ROUNDS = int(os.getenv("LERNA_AGENT_MAX_TOOL_ROUNDS", "12"))


def _build_chat_model(model_name: str | None = None) -> ChatOpenAI:
    if not DEFAULT_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set (pass api_key= or set the env var).")
    max_tokens = int(os.getenv("LERNA_AGENT_MAX_TOKENS", "2048"))
    return ChatOpenAI(
        model=model_name or DEFAULT_MODEL_NAME,
        temperature=0.0,
        max_tokens=max_tokens,
        api_key=DEFAULT_API_KEY,
        base_url=DEFAULT_BASE_URL,
    )


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _to_json_text(value: Any) -> str:
    try:
        return json.dumps(value, default=str)
    except TypeError:
        return str(value)


def _execute_tool_call(name: str, arguments: Any) -> Any:
    if name not in TOOL_CALLABLES:
        return {"ok": False, "error": f"unknown tool {name!r}"}
    if not isinstance(arguments, dict):
        return {"ok": False, "error": "tool arguments must be an object"}
    try:
        return TOOL_CALLABLES[name](**arguments)
    except TypeError as exc:
        return {"ok": False, "error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:  # pylint: disable=broad-except
        return {"ok": False, "error": str(exc)}


def _compile_agent(name: str, system_prompt: str, tool_names: list[str]) -> Any:
    _ = name
    bound_model = _build_chat_model().bind_tools(build_toolset(tool_names))

    class _LangChainAgent:
        def __init__(self, prompt: str) -> None:
            self._prompt = prompt

        def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
            messages = [SystemMessage(content=self._prompt)]
            transcript: list[dict[str, Any]] = list(payload.get("messages", []))
            for message in payload.get("messages", []):
                role = message.get("role", "user")
                content = str(message.get("content", ""))
                if role == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

            for round_index in range(DEFAULT_MAX_TOOL_ROUNDS):
                result = bound_model.invoke(messages)
                tool_calls = getattr(result, "tool_calls", None) or []
                transcript.append(
                    {
                        "role": "assistant",
                        "content": _content_to_text(result.content),
                        "tool_calls": tool_calls,
                    }
                )
                messages.append(result)

                if not tool_calls:
                    break

                for call_index, call in enumerate(tool_calls):
                    call_id = str(call.get("id") or f"call_{round_index}_{call_index}")
                    call_name = str(call.get("name", "unknown_tool"))
                    call_args = call.get("args", {})
                    tool_result = _execute_tool_call(call_name, call_args)
                    tool_result_text = _to_json_text(tool_result)
                    transcript.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": call_name,
                            "content": tool_result_text,
                        }
                    )
                    messages.append(ToolMessage(content=tool_result_text, tool_call_id=call_id))

            return {"messages": transcript}

    return _LangChainAgent(system_prompt)


@lru_cache(maxsize=None)
def get_filter_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent("FilterAgent", system_prompt or FILTER_AGENT_PROMPT, FILTER_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_incident_matcher_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent(
        "IncidentMatcherAgent",
        system_prompt or MATCHER_AGENT_PROMPT,
        MATCHER_AGENT_TOOLS,
    )


@lru_cache(maxsize=None)
def get_diagnosis_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent("DiagnosisAgent", system_prompt or DIAGNOSIS_AGENT_PROMPT, DIAGNOSIS_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_planning_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent("PlanningAgent", system_prompt or PLANNING_AGENT_PROMPT, PLANNING_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_executor_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent("ExecutorAgent", system_prompt or EXECUTOR_AGENT_PROMPT, EXECUTOR_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_validation_agent(system_prompt: str | None = None) -> Any:
    return _compile_agent("ValidationAgent", system_prompt or VALIDATION_AGENT_PROMPT, VALIDATION_AGENT_TOOLS)
