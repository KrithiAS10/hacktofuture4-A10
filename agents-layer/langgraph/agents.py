from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

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
    VALIDATION_AGENT_TOOLS,
    build_toolset,
)

DEFAULT_MODEL_NAME = os.getenv("LERNA_AGENT_MODEL", "minimax/minimax-m2.5:free")
DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
DEFAULT_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")


def _build_chat_model(model_name: str | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model_name or DEFAULT_MODEL_NAME,
        temperature=0.0,
        api_key=DEFAULT_API_KEY,
        base_url=DEFAULT_BASE_URL,
    )


def _compile_agent(name: str, system_prompt: str, tool_names: list[str]) -> Any:
    model = _build_chat_model()
    return create_react_agent(
        model=model,
        tools=build_toolset(tool_names),
        prompt=SystemMessage(content=system_prompt),
        name=name,
    )


@lru_cache(maxsize=None)
def get_filter_agent() -> Any:
    return _compile_agent("FilterAgent", FILTER_AGENT_PROMPT, FILTER_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_incident_matcher_agent() -> Any:
    return _compile_agent(
        "IncidentMatcherAgent",
        MATCHER_AGENT_PROMPT,
        MATCHER_AGENT_TOOLS,
    )


@lru_cache(maxsize=None)
def get_diagnosis_agent() -> Any:
    return _compile_agent("DiagnosisAgent", DIAGNOSIS_AGENT_PROMPT, DIAGNOSIS_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_planning_agent() -> Any:
    return _compile_agent("PlanningAgent", PLANNING_AGENT_PROMPT, PLANNING_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_executor_agent() -> Any:
    return _compile_agent("ExecutorAgent", EXECUTOR_AGENT_PROMPT, EXECUTOR_AGENT_TOOLS)


@lru_cache(maxsize=None)
def get_validation_agent() -> Any:
    return _compile_agent("ValidationAgent", VALIDATION_AGENT_PROMPT, VALIDATION_AGENT_TOOLS)
