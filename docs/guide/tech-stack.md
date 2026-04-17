# Tech stack

- **Frontend:** React, Next.js
- **Backend:** FastAPI (Python)
- **Data:** MongoDB (agent configuration), Qdrant (incident history), Redis (live status)
- **APIs and orchestration:** OpenTelemetry, LangGraph (agent orchestration), LLM reasoning, Kubernetes API
- **Observability:** Prometheus, Grafana Loki, Jaeger
- **Sandbox:** `kind`
- **Tooling:** MCP for standardized `kubectl` access, Python and Node Kubernetes SDKs

Component-specific details:

- [Backend API reference](../reference/backend.md)
- [Observation layer reference](../reference/observation-layer.md)
