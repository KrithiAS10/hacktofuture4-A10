"""Agent loop tests without calling OpenAI (tools may still hit local HTTP/k8s during dispatch)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from lerna_agent.agent import LernaAgent


def test_agent_tool_loop_finishes_after_second_completion():
    tool_msg = MagicMock()
    tool_msg.content = None
    tc = MagicMock()
    tc.id = "call_1"
    tc.type = "function"
    tc.function.name = "check_observability_backends"
    tc.function.arguments = "{}"
    tool_msg.tool_calls = [tc]

    final_msg = MagicMock()
    final_msg.content = "Backends are unhealthy."
    final_msg.tool_calls = None

    mock_create = MagicMock()
    mock_create.side_effect = [
        MagicMock(choices=[MagicMock(message=tool_msg)]),
        MagicMock(choices=[MagicMock(message=final_msg)]),
    ]

    agent = LernaAgent(api_key="sk-test")
    with patch.object(agent._client.chat.completions, "create", mock_create):
        reply = agent.run("Check observability health.")

    assert "unhealthy" in reply.lower() or "Backends" in reply
    assert mock_create.call_count == 2


def test_agent_requires_api_key():
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            LernaAgent(api_key=None)
