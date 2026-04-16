"""CLI for manual testing: `python -m lerna_agent.cli "your question"` (PYTHONPATH must include agents-layer)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Sequence

from .runtime import execute_incident_workflow, manual_incident_from_message
from .store import WorkflowStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Lerna OpenAI tool agent once.")
    parser.add_argument("message", nargs="?", default=None, help="User message")
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Override model (default: env LERNA_AGENT_MODEL or minimax/minimax-m2.5:free)",
    )
    args = parser.parse_args(argv)
    text = args.message
    if not text:
        text = sys.stdin.read().strip()
    if not text:
        parser.error("Provide a message argument or pipe stdin")
    incident = manual_incident_from_message(text)
    store = WorkflowStore()
    workflow_id = f"cli-{incident.incident_id}"
    result = asyncio.run(execute_incident_workflow(incident, store, workflow_id=workflow_id, model=args.model))
    asyncio.run(store.close())
    print(result["result"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
