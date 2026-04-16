# HackToFuture 4.0 — Template

Welcome to your official HackToFuture 4 repository.

## Kubernetes Quickstart (Lerna stack)

### Local cluster with kind (recommended)

Prerequisites: [Docker](https://docs.docker.com/get-docker/), [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation), [kubectl](https://kubernetes.io/docs/tasks/tools/).

From the repository root:

- **Windows (PowerShell):** `.\scripts\deploy-kind.ps1`
- **Linux / macOS:** `chmod +x scripts/deploy-kind.sh && ./scripts/deploy-kind.sh`

This creates a cluster named `lerna` (override with `KIND_CLUSTER_NAME`), installs ingress-nginx for kind, builds `lerna-backend:latest` and `lerna-dashboard:latest`, loads them into the cluster (`imagePullPolicy: Never`), applies the observation stack and app manifests, and waits for rollouts.

After a successful run:

- Open **http://localhost:8080** (ingress maps host port **8080** to the controller; see `kind/cluster-config.yaml`).
- Optional: add `127.0.0.1 lerna.local` to your hosts file and use **http://lerna.local:8080**.

To tear down: `kind delete cluster --name lerna`

### Manual `kubectl apply` (any cluster)

Deploy order:

1. Observation stack
   - `kubectl apply -f observation-layer/k8s/namespace.yaml`
   - `kubectl apply -f observation-layer/k8s/loki-configmap.yaml`
   - `kubectl apply -f observation-layer/k8s/loki-deployment.yaml`
   - `kubectl apply -f observation-layer/k8s/jaeger-deployment.yaml`
   - `kubectl apply -f observation-layer/k8s/prometheus-configmap.yaml`
   - `kubectl apply -f observation-layer/k8s/prometheus-deployment.yaml`
   - `kubectl apply -f observation-layer/k8s/otel-collector-configmap.yaml`
   - `kubectl apply -f observation-layer/k8s/otel-collector-rbac.yaml`
   - `kubectl apply -f observation-layer/k8s/otel-collector-deployment.yaml`

2. App namespaces and services
   - `kubectl apply -f k8s/namespace-lerna.yaml`
   - `kubectl apply -f k8s/redis-deployment.yaml`
   - `kubectl apply -f backend/k8s/backend-rbac.yaml`
   - `kubectl apply -f agents-layer/k8s/agents-deployment.yaml`
   - `kubectl apply -f detection-service/k8s/detection-deployment.yaml`
   - `kubectl apply -f backend/k8s/backend-deployment.yaml`
   - `kubectl apply -f dashboard/k8s/dashboard-deployment.yaml`
   - `kubectl apply -f k8s/lerna-ingress.yaml`

Notes:

- **Images:** For local kind, use the scripted deploy above so images are built and loaded into the cluster. Manifests reference tags such as `lerna-backend:latest`, `lerna-agents:latest`, `lerna-detection:latest`, and `lerna-dashboard:latest` with `imagePullPolicy: Never`. On other clusters, replace image names in `backend/k8s/backend-deployment.yaml`, `agents-layer/k8s/agents-deployment.yaml`, `detection-service/k8s/detection-deployment.yaml`, and `dashboard/k8s/dashboard-deployment.yaml`, push those images to your registry, and set `imagePullPolicy` and tags as needed.
- **Ingress:** Routes `/api` to the backend and `/` to the dashboard (`ingressClassName: nginx`), so the frontend can reach the API without extra CORS setup. For kind, hosts **localhost** and **lerna.local** are defined in `k8s/lerna-ingress.yaml`.

This repository template will be used for development, tracking progress, and final submission of your project. Ensure that all work is committed here within the allowed hackathon duration.

---

### Instructions for the teams:

- Fork the Repository and name the forked repo in this convention: hacktofuture4-A10

---

## Rules

- Work must be done ONLY in the forked repository
- Only Four Contributors are allowed.
- After 36 hours, Please make PR to the Main Repository. A Form will be sent to fill the required information.
- Do not copy code from other teams
- All commits must be from individual GitHub accounts
- Please provide meaningful commits for tracking.
- Do not share your repository with other teams
- Final submission must be pushed before the deadline
- Any violation may lead to disqualification

---

# The Final README Template 

## Problem Statement / Idea

Clearly describe the problem you are solving.

- What is the problem?
- Why is it important?
- Who are the target users?

---

## Proposed Solution

Explain your approach:

- What are you building?
- How does it solve the problem?
- What makes your solution unique?

---

## Features

List the core features of your project:

- Feature 1
- Feature 2
- Feature 3

---

## Tech Stack

Mention all technologies used:

- Frontend:
- Backend:
- Database:
- APIs / Services:
- Tools / Libraries:

---

## Project Setup Instructions

Provide clear steps to run your project:

```bash
# Clone the repository
git clone <repo-link>

# Install dependencies
...

# Run the project
...
```
