# Observation Backend (FastAPI)

This service provides the backend adapter between the dashboard and the observation stack.

## Features

- Query observability backends:
  - Prometheus (`/api/obs/metrics`)
  - Loki (`/api/obs/logs`)
  - Jaeger (`/api/obs/traces`)
- Backend health view (`/api/obs/health`)
- Kubernetes cluster poller for dashboard-friendly summaries:
  - `/api/cluster/summary`
  - `/api/cluster/health`

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
- `ENABLE_K8S_POLLER` (default: `true`)
- `K8S_NAMESPACE_SCOPE` (default: empty, meaning all namespaces)
- `POLL_INTERVAL_SECONDS` (default: `15`)
- `POLL_TIMEOUT_SECONDS` (default: `20`)

## Notes

- The Kubernetes poller auto-loads in-cluster config first, then kubeconfig.
- If Kubernetes config is unavailable, cluster endpoints return `available: false` with a reason.

## Kubernetes deployment

Backend manifests are in `backend/k8s`:

- `backend-rbac.yaml`
- `backend-deployment.yaml`

Before applying, replace `your-registry/lerna-backend:latest` with your image.
