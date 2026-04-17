from __future__ import annotations

from typing import Any

from lerna_shared.detection import DetectionIncident

FILTER_AGENT_PROMPT = """You are the Filter Agent for a Kubernetes incident response system.
Your task is to decide whether the incident is worth pursuing with the rest of the workflow.
Respond clearly, explain whether the incident appears service-impacting, and identify any evidence that supports your judgment.
Do not take remediation actions yet.
"""

MATCHER_AGENT_PROMPT = """You are the Incident Matcher Agent.
Your task is to search for past incidents that are similar to the current one and summarize the most relevant findings.
Focus on cluster symptoms, service impact, error patterns, and remediation actions taken before.
"""

DIAGNOSIS_AGENT_PROMPT = """You are the Diagnosis Agent.
Analyze the incident details, logs, metrics, traces, and cluster snapshot to identify the most likely root cause.
List the top findings and explain why they point to a specific failure mode.
"""

PLANNING_AGENT_PROMPT = """You are the Planning Agent.
Propose one or more safe remediation plans for the diagnosed root cause.
Prefer sandbox-first approaches and show the expected impact and risks for each plan.
"""

EXECUTOR_AGENT_PROMPT = """You are the Executor Agent.
Translate the chosen remediation plan into concrete Kubernetes or observability actions.
If sandbox execution is available, describe the sandbox step first before any production change.
Do not run anything automatically without explicit operator approval unless the workflow is configured for safe automation.
"""

VALIDATION_AGENT_PROMPT = """You are the Validation Agent.
After remediation, verify whether the incident has been resolved.
Use metrics, logs, events, and cluster state to confirm recovery and identify any remaining symptoms.
"""

# Max chars per upstream handoff in the user prompt (full evidence stays under "Incident").
_HANDOFF_MAX_CHARS = 3200

_PIPELINE_STAGES: list[tuple[str, str]] = [
    ("Filter", "Decide whether the incident warrants the rest of the pipeline."),
    ("Incident Matching", "Retrieve similar past incidents and summarize relevant prior fixes."),
    ("Diagnosis", "Determine likely root cause using evidence, logs, metrics, and tools."),
    ("Planning", "Propose safe remediation plans (prefer sandbox-first)."),
    ("Execution", "Describe concrete actions to apply the chosen plan."),
    ("Validation", "Verify recovery and remaining risk after execution guidance."),
]


def _stage_meta(stage_name: str) -> tuple[int, int, str]:
    total = len(_PIPELINE_STAGES)
    for idx, (name, desc) in enumerate(_PIPELINE_STAGES, start=1):
        if name == stage_name:
            return idx, total, desc
    return 0, total, "Execute your specialist role for this incident."


def _truncate_handoff(text: str) -> str:
    t = text.strip()
    if len(t) <= _HANDOFF_MAX_CHARS:
        return t
    return t[: _HANDOFF_MAX_CHARS] + "\n…(truncated for handoff)"


def incident_summary(incident: DetectionIncident) -> str:
    evidence_lines = [
        f"- [{item.severity}] {item.source}: {item.message}"
        for item in incident.evidence[:8]
    ]
    return "\n".join(
        [
            f"Incident ID: {incident.incident_id}",
            f"Service: {incident.service}",
            f"Namespace: {incident.namespace}",
            f"Severity: {incident.severity}",
            f"Summary: {incident.summary}",
            f"Incident class: {incident.incident_class}",
            "Evidence:",
            *evidence_lines,
        ]
    )


def build_agent_input(
    incident: DetectionIncident,
    stage_name: str,
    previous_outputs: dict[str, Any] | None = None,
) -> str:
    step_no, total, role_line = _stage_meta(stage_name)
    header = (
        f"You are working in a multi-agent incident pipeline.\n"
        f"Current stage: {stage_name} (step {step_no} of {total} if applicable).\n"
        f"Your focus: {role_line}\n"
        f"You receive concise handoffs from upstream agents — not their full tool logs. "
        f"Use your tools when you need fresh cluster or observability data.\n"
        f"Do not repeat upstream work; build on their conclusions."
    )

    lines = [header, "", "## Incident (authoritative context)", incident_summary(incident)]

    if previous_outputs:
        lines.append("")
        lines.append("## Upstream handoffs (summarized conclusions only)")
        for step_name, output in previous_outputs.items():
            lines.append(f"### From {step_name} agent")
            if isinstance(output, dict) and "messages" in output:
                body = _messages_to_text(output["messages"])
            else:
                body = str(output)
            lines.append(_truncate_handoff(body))
            lines.append("")

    lines.append("## Your task")
    lines.append("Complete your stage using the incident context and upstream handoffs. Be specific and actionable.")
    return "\n".join(lines)


def _messages_to_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"{message.get('role', 'unknown')}: {message.get('content', '')}"
            for message in messages
        ]
    )
