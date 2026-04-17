# Getting started

## System requirements

To run Project Lerna locally with `kind` or deploy to another Kubernetes cluster:

- **Operating system:** Linux, macOS, or Windows (WSL2 recommended on Windows for best experience).
- **Docker:** For images and `kind` clusters. Docker Desktop (Windows or macOS) or Docker Engine (Linux), running.
- **kind:** Local Kubernetes clusters.
- **kubectl:** Cluster interaction.
- **Python 3.x:** Local scripts and Python services outside containers.
- **Node.js and a package manager:** Dashboard local development and builds.

## Clone the repository

```bash
git clone https://github.com/KrithiAS10/hacktofuture4-A10.git
cd hacktofuture4-A10
```

## Kubernetes quickstart (recommended)

From the repository root:

**Windows (PowerShell):**

```powershell
.\scripts\deploy-kind.ps1
```

**Linux or macOS:**

```bash
chmod +x scripts/deploy-kind.sh
./scripts/deploy-kind.sh
```

The script:

- Creates a `kind` cluster named `lerna`.
- Installs `ingress-nginx`.
- Builds and loads `lerna-backend:latest`, `lerna-dashboard:latest`, `lerna-agents:latest`, and `lerna-detection:latest` into the cluster.
- Applies the observation stack and application manifests.
- Waits for rollouts.

After a successful run:

- Open **http://localhost:8080** (ingress maps host port **8080** to the controller).
- Optionally add `127.0.0.1 lerna.local` to your hosts file and use **http://lerna.local:8080**.

Tear down:

```bash
kind delete cluster --name lerna
```

## Manual `kubectl apply` (any cluster)

Build and push images to a registry your cluster can reach, then update image references in the deployment manifests.

### Deploy order

**1. Observation stack**

```bash
kubectl apply -f observation-layer/k8s/namespace.yaml
kubectl apply -f observation-layer/k8s/loki-configmap.yaml
kubectl apply -f observation-layer/k8s/loki-deployment.yaml
kubectl apply -f observation-layer/k8s/jaeger-deployment.yaml
kubectl apply -f observation-layer/k8s/prometheus-configmap.yaml
kubectl apply -f observation-layer/k8s/prometheus-deployment.yaml
kubectl apply -f observation-layer/k8s/otel-collector-configmap.yaml
kubectl apply -f observation-layer/k8s/otel-collector-rbac.yaml
kubectl apply -f observation-layer/k8s/otel-collector-deployment.yaml
```

**2. Application namespaces and services**

```bash
kubectl apply -f k8s/namespace-lerna.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f backend/k8s/backend-rbac.yaml
kubectl apply -f agents-layer/k8s/agents-deployment.yaml
kubectl apply -f detection-service/k8s/detection-deployment.yaml
kubectl apply -f backend/k8s/backend-deployment.yaml
kubectl apply -f dashboard/k8s/dashboard-deployment.yaml
kubectl apply -f k8s/lerna-ingress.yaml
```

### Notes

- **Images:** Build and push `lerna-backend`, `lerna-agents`, `lerna-detection`, and `lerna-dashboard`. Update image names and `imagePullPolicy` in `backend/k8s/backend-deployment.yaml`, `agents-layer/k8s/agents-deployment.yaml`, `detection-service/k8s/detection-deployment.yaml`, and `dashboard/k8s/dashboard-deployment.yaml`.
- **Ingress:** Routes `/api` to the backend and `/` to the dashboard. `kind` hosts (`localhost`, `lerna.local`) are defined in `k8s/lerna-ingress.yaml`; adjust for your environment.

## Documentation site

From the `docs` folder in this repository:

```bash
cd docs
npm install
npm run dev
```

Then open the local URL printed in the terminal (typically **http://localhost:5173**).
