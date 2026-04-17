# Introduction

## Problem statement

In today's complex cloud-native landscape, Kubernetes microservice systems are prone to cascading failures that overwhelm traditional incident response. Native Kubernetes recovery mechanisms are often reactive and limited, offering basic restarts or rescheduling rather than comprehensive solutions. This leads to slow, manual root cause analysis across disparate observability tools—a significant pain point for Site Reliability Engineers (SREs), DevOps teams, and platform operators.

Project Lerna addresses this by proposing an autonomous SRE system designed for Kubernetes clusters. The core idea is to extend basic Kubernetes self-healing with a multi-agent workflow that can detect incidents, diagnose root causes, plan remediation, execute fixes in a safe sandbox, and validate outcomes. The primary goal is to reduce manual incident triage across logs, metrics, and traces while keeping human oversight through approval workflows.

## Proposed solution

Project Lerna is an intelligent incident response system for Kubernetes. It uses a multi-agent pipeline that covers the incident lifecycle from detection through validation. A sandbox-first execution model allows remediation to be tested without risking production. The system automates diagnosis, planning, and execution to reduce mean time to resolution (MTTR).

What makes Lerna distinctive:

- **Human-in-the-loop control:** An operator dashboard provides visibility, configuration, and approval or override paths.
- **Proactive remediation:** Fixes are tested in isolated `kind` environments before broader rollout.
- **Incident memory:** Semantic retrieval of past incidents supports faster, more informed responses to repeats.
- **Trace-driven diagnosis:** OpenTelemetry-centric correlation supports deeper root cause analysis than surface symptoms alone.
- **Least-privilege agents:** Each agent operates with minimal necessary permissions.

Next: [Features](./features.md) or [Architecture](./architecture.md).
