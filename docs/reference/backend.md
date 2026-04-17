# Backend (FastAPI)

The backend is the operator and dashboard adapter to the observation stack.

## Capabilities

- Query observability backends:
  - Prometheus: `/api/obs/metrics`
  - Loki: `/api/obs/logs`
  - Jaeger: `/api/obs/traces`
- Backend health: `/api/obs/health`
- Detection debug: `/api/detection/check` returns `has_error` and an evidence summary
- Agent prompts (Redis-backed):
  - `GET /api/agents/prompts`
  - `PUT /api/agents/prompts/{agent_id}`
  - `DELETE /api/agents/prompts/{agent_id}` (reset to built-in default in the UI)
- Kubernetes summaries for the dashboard:
  - `/api/cluster/summary`
  - `/api/cluster/health`

Autonomous incident polling and triggering live in the standalone `detection-service`.

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On Linux or macOS, activate the virtual environment with `source .venv/bin/activate` instead.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Port |
| `PROMETHEUS_URL` | `http://localhost:9090` | Metrics backend |
| `LOKI_URL` | `http://localhost:3100` | Logs backend |
| `JAEGER_URL` | `http://localhost:16686` | Traces backend |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis |
| `ENABLE_K8S_POLLER` | `true` | Enable cluster polling |
| `K8S_NAMESPACE_SCOPE` | _empty_ | Limit namespaces (empty means all) |
| `POLL_INTERVAL_SECONDS` | `15` | Poll interval |
| `POLL_TIMEOUT_SECONDS` | `20` | Poll timeout |

### Local development notes

- Dashboard against local backend: set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api`.
- Backend talking to in-cluster agents: port-forward the agents service and set `AGENTS_SERVICE_URL=http://localhost:8001`.

```powershell
kubectl port-forward -n lerna service/lerna-agents 8001:8000
```

- Backend inside Kubernetes: keep the default `/api` path or configure ingress accordingly.

## Behavior notes

- The Kubernetes poller uses in-cluster config first, then kubeconfig.
- If Kubernetes config is unavailable, cluster endpoints return `available: false` with a reason.

## Kubernetes manifests

Paths: `backend/k8s` — `backend-rbac.yaml`, `backend-deployment.yaml`. Replace registry image references before applying.
