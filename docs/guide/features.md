# Features

- **Incident detection and filtering:** Validates events to identify real service-impacting incidents.
- **Orchestrated multi-agent workflows:** Coordinates specialized agents for diagnosis, planning, execution, and validation.
- **Diagnosis and root cause analysis:** Analyzes logs, metrics, and cluster state to pinpoint root causes.
- **Remediation planning:** Proposes one or more safe and effective remediation plans.
- **Sandbox-first execution and validation:** Applies candidate fixes in isolated `kind` environments and verifies success before production changes.
- **Historical incident matching:** Queries a knowledge base (Qdrant) for similar past incidents and resolutions.
- **Operator dashboard:** Live cluster and agent status, decision control, and approval or denial of agent actions.

See also [Tech stack](./tech-stack.md) and [Architecture](./architecture.md).
