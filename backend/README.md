# Observation Backend (FastAPI)

This service provides the operator/dashboard backend adapter between the dashboard and the observation stack.

## Features

- Query observability backends:
  - Prometheus (`/api/obs/metrics`)
  - Loki (`/api/obs/logs`)
  - Jaeger (`/api/obs/traces`)
- Backend health view (`/api/obs/health`)
- Detection debug check (`/api/detection/check`) returning `has_error` + evidence summary
- Agent prompt APIs (Redis-backed):
  - `GET /api/agents/prompts`
  - `PUT /api/agents/prompts/{agent_id}`
  - `DELETE /api/agents/prompts/{agent_id}` (reset to built-in default in UI)
- Kubernetes cluster poller for dashboard-friendly summaries:
  - `/api/cluster/summary`
  - `/api/cluster/health`
- Autonomous incident polling/triggering now lives in the standalone `detection-service`

## Run locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration (env vars)

- `HOST` (default: `0.0.0.0`)
- `PORT` (default: `8000`)
- `PROMETHEUS_URL` (default: `http://localhost:9090`)
- `LOKI_URL` (default: `http://localhost:3100`)
- `JAEGER_URL` (default: `http://localhost:16686`)
- `REDIS_URL` (default: `redis://localhost:6379/0`)
- `ENABLE_K8S_POLLER` (default: `true`)
- `K8S_NAMESPACE_SCOPE` (default: empty, meaning all namespaces)
- `POLL_INTERVAL_SECONDS` (default: `15`)
- `POLL_TIMEOUT_SECONDS` (default: `20`)

### Local development notes

- When running `dashboard` locally with the backend on `http://localhost:8000`, set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api`.
- When using a local backend with a cluster-deployed agents service, port-forward the agents service and set `AGENTS_SERVICE_URL=http://localhost:8001`.
  ```powershell
  kubectl port-forward -n lerna service/lerna-agents 8001:8000
  ```
- If running the backend inside Kubernetes, keep the default `'/api'` path or configure an ingress proxy.

## Notes

- The Kubernetes poller auto-loads in-cluster config first, then kubeconfig.
- If Kubernetes config is unavailable, cluster endpoints return `available: false` with a reason.

## Kubernetes deployment

Backend manifests are in `backend/k8s`:

- `backend-rbac.yaml`
- `backend-deployment.yaml`

Before applying, replace `your-registry/lerna-backend:latest` with your image.
