# Architecture

Project Lerna (Clueless) is organized in layers that flow from telemetry to operator control.

## Layers

1. **Observation layer** — Collects logs, traces, and metrics using OpenTelemetry, Loki, Prometheus, and Kubernetes events.
2. **Detection layer** — Identifies meaningful incidents from telemetry and cluster events; uses PromQL, LogQL, and similar queries to classify failures.
3. **Agents layer** — Specialized agents coordinated by an orchestrator perform diagnosis, planning, execution, and validation.
4. **Execution safety layer** — Isolated `kind` environments sandbox remediation before production changes.
5. **Operator interface** — Dashboard for cluster and agent status, approvals, prompt steering, and optional autonomy.

## Agent roles

- **Filter agent:** Confirms whether an event is a real service-impacting incident.
- **Orchestrator agent:** Routes tasks and coordinates the workflow.
- **Incident matcher agent:** Queries Qdrant for similar historical incidents and fixes.
- **Diagnosis agent:** Analyzes logs, metrics, and cluster state for root cause.
- **Planning agent:** Proposes remediation plans.
- **Executor agent:** Applies candidate fixes (sandbox-first).
- **Validation agent:** Checks whether remediation succeeded.

## Operating principles

- Safety first: sandbox remediation before production.
- Human-in-the-loop by default: review and approve actions.
- Trace correlation as the primary debugging backbone.
- Narrow, explicit responsibilities per agent.

## Implementation phases (roadmap)

1. Observability and detection in local Kubernetes (`kind`), with telemetry and anomaly detection.
2. Agents layer with configurable specialists (for example LangGraph) and scoped permissions.
3. Testing and validation against failures such as pod crashes and misconfigurations.
4. Dashboard UX for reasoning visibility, incident history, chat controls, and fix approvals.
