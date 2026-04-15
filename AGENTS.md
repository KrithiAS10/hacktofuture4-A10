# Project Context: Clueless (Project Lerna)

## Overview
Project Lerna is an autonomous SRE system for Kubernetes clusters. It extends basic Kubernetes self-healing by using a multi-agent workflow that can detect incidents, diagnose root causes, plan remediation, execute fixes in a safe sandbox, and validate outcomes.

The goal is to reduce manual incident triage across logs, metrics, and traces while keeping a human operator in control through approval workflows.

## Problem Statement
- Modern Kubernetes microservice systems can fail in cascading ways.
- Native Kubernetes recovery is reactive and limited (restart/reschedule).
- Root cause analysis across observability tooling is manual and slow.
- Need: an intelligent, trace-aware system that can diagnose and restore stability safely.

## Solution Summary
- Multi-agent incident response pipeline from detection to validation.
- Sandbox-first execution model to test fixes away from production.
- Operator dashboard for configuration, monitoring, approvals, and overrides.
- Memory-driven incident matching via semantic retrieval of past incidents.

## Core Capabilities
- Risk-free sandboxing of remediation actions.
- Trace-driven diagnosis (OpenTelemetry-centric correlation).
- Real-time operator visibility and manual approval options.
- Least-privilege agent access to resources.
- Incident memory lookup for faster repeat resolution.

## High-Level Architecture
Lerna is organized as layers:

1) **Observation layer**
- Collects logs, traces, and metrics.
- Uses tools like OpenTelemetry, Loki, Prometheus, and Kubernetes events.

2) **Detection layer**
- Identifies meaningful incidents from telemetry and cluster events.
- Queries logs/metrics (e.g., PromQL/LogQL) to classify failures.

3) **Agents layer**
- Runs specialized agents coordinated by an orchestrator.
- Performs diagnosis, planning, execution, and validation workflows.

4) **Execution safety layer**
- Uses isolated `kind` environments as sandboxes.
- Allows testing fixes without risking production workloads.

5) **Operator interface**
- Dashboard for live cluster/agent status and decision control.
- Supports approve/deny, prompt steering, and optional autonomy.

## Agent Roles (Defined in Slides)
- **Filter Agent**: validates whether an event is a real service-impacting incident.
- **Orchestrator Agent**: routes tasks and coordinates agent workflow.
- **Incident Matcher Agent**: queries Qdrant for similar historical incidents/fixes.
- **Diagnosis Agent**: analyzes logs/metrics/cluster state for root cause.
- **Planning Agent**: proposes one or more remediation plans.
- **Executor Agent**: applies candidate fixes (sandbox-first).
- **Validation Agent**: checks whether remediation succeeded.

## Tech Stack (From Proposal)
- **Observability**: Prometheus, Grafana Loki, OpenTelemetry, Jaeger, Kubernetes API events.
- **Agent orchestration**: LangGraph.
- **LLM reasoning**: GPT-5.4 mini (proposal choice for cost/performance).
- **Cluster control interface**: MCP for standardized `kubectl` access.
- **Sandbox infrastructure**: `kind`.
- **Backend**: FastAPI, MongoDB (agent config), Qdrant (incident history), Redis (live status).
- **Frontend**: React / Next.js.
- **K8s clients**: Python/Node SDKs.

## Planned Implementation Phases
1. **Observability + Detection**: deploy test microservices in local Kubernetes (`kind`), wire telemetry and anomaly detection.
2. **Agents layer**: implement dynamically configurable specialized agents via LangGraph; enforce scoped permissions.
3. **Testing + Validation**: validate detection/remediation against failures such as pod crashes and misconfigurations.
4. **Dashboard**: build operator UX for reasoning visibility, incident history, chat controls, and fix approvals.

## Operating Principles
- Safety first: test remediation in sandbox before production changes.
- Human-in-the-loop by default: operators can review and approve actions.
- Trace correlation as primary debugging backbone.
- Role-based specialization: each agent has a narrow, explicit responsibility.
