"""Single OpenAI chat agent with tool access to `tools.*`."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .tool_registry import dispatch_tool, openai_tools, tool_result_to_json_content

DEFAULT_MODEL = os.getenv("LERNA_AGENT_MODEL", "gpt-4.1-nano-2025-04-14")
DEFAULT_MAX_TOOL_ROUNDS = int(os.getenv("LERNA_AGENT_MAX_TOOL_ROUNDS", "24"))

SYSTEM_PROMPT = """You are Lerna, an SRE assistant for Kubernetes and observability.
You have tools to query Prometheus, Loki, Jaeger, Qdrant incident memory, and the Kubernetes API.
Rules:
- Prefer read-only tools (metrics, logs, traces, cluster snapshot) before suggesting changes.
- Mutating tools (scale, delete pod, apply manifests, cordon nodes) can impact production; only use them when the user clearly intends remediation and you have enough context.
- Summarize tool outputs clearly; cite namespaces and resource names.
- If a tool returns ok=false or an error field, explain it and propose next steps."""


def _assistant_message_dict(msg: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"role": "assistant", "content": msg.content}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = [
            {
                "id": tc.id,
                "type": getattr(tc, "type", "function") or "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in msg.tool_calls
        ]
    return out


class LernaAgent:
    """OpenAI Chat Completions agent with function tools (single-turn or multi-step tool loops)."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = system_prompt
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set (pass api_key= or set the env var).")
        kwargs: Dict[str, Any] = {"api_key": key}
        if base_url or os.getenv("OPENROUTER_BASE_URL"):
            kwargs["base_url"] = base_url or os.getenv("OPENROUTER_BASE_URL")
        self._client = OpenAI(**kwargs)
        self._tools = openai_tools()

    def run(
        self,
        user_message: str,
        *,
        conversation: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Send a user message and return the model's final natural-language reply after any tool calls.
        """
        messages: List[Dict[str, Any]] = list(conversation) if conversation else []
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_message})

        rounds = 0
        while rounds < self.max_tool_rounds:
            rounds += 1
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._tools,
                tool_choice="auto",
                temperature=0.2,
            )
            choice = response.choices[0]
            msg = choice.message

            if not getattr(msg, "tool_calls", None) or not msg.tool_calls:
                return (msg.content or "").strip()

            messages.append(_assistant_message_dict(msg))

            for tc in msg.tool_calls:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                result = dispatch_tool(name, raw_args)
                content = tool_result_to_json_content(result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content,
                    }
                )

        return "Stopped: max tool rounds exceeded. Increase LERNA_AGENT_MAX_TOOL_ROUNDS or narrow the task."


def run_agent(user_message: str, **kwargs: Any) -> str:
    """Convenience: one-shot `LernaAgent().run(user_message)`."""
    return LernaAgent(**kwargs).run(user_message)
