# Clueless

## Problem Statement / Idea

In today's complex cloud-native landscape, Kubernetes microservice systems are prone to cascading failures that overwhelm traditional incident response. Native Kubernetes recovery mechanisms are often reactive and limited, offering basic restarts or rescheduling rather than comprehensive solutions. This leads to slow, manual root cause analysis across disparate observability tools – a significant pain point for Site Reliability Engineers (SREs), DevOps teams, and platform operators.

Project Lerna addresses this by proposing an autonomous SRE system designed for Kubernetes clusters. Our core idea is to extend basic Kubernetes self-healing with a sophisticated multi-agent workflow. This system can detect incidents, diagnose root causes, plan remediation, execute fixes in a safe sandbox, and validate outcomes. Our primary goal is to drastically reduce the burden of manual incident triage across logs, metrics, and traces, thereby empowering SREs and operators to maintain stability with greater efficiency, all while ensuring human oversight through approval workflows. This is crucial for maintaining the reliability and performance of critical applications, making it highly important for any organization operating at scale on Kubernetes.

---

## Proposed Solution

We are building Project Lerna, an intelligent incident response system for Kubernetes. Our solution leverages a sophisticated multi-agent pipeline that orchestrates the entire incident lifecycle, from initial detection through to validation. This robust system tackles the challenges of complex Kubernetes environments by offering a unique sandbox-first execution model, allowing for safe testing of remediation actions without risking production environments. Lerna solves the problem of slow, manual incident response by automating diagnosis, planning, and execution, significantly reducing mean time to resolution (MTTR).

What makes Lerna unique is its commitment to both autonomy and safety:
*   **Human-in-the-Loop Control:** An intuitive operator dashboard provides real-time visibility, configuration options, and critical approval/override mechanisms, ensuring operators retain ultimate control.
*   **Proactive Remediation:** Fixes are tested in isolated `kind` environments before deployment, guaranteeing risk-free operations.
*   **Intelligent Incident Memory:** The system utilizes memory-driven incident matching via semantic retrieval of past issues, enabling faster, more informed responses to recurring problems.
*   **Trace-Driven Diagnosis:** Leveraging OpenTelemetry-centric correlation, Lerna performs deep, trace-aware root cause analysis, moving beyond superficial symptoms.
*   **Least-Privilege Agent Access:** Each agent operates with minimal necessary permissions, enhancing security and system stability.

---

## Features

*   **Incident Detection & Filtering:** Validates events to identify real service-impacting incidents.
*   **Orchestrated Multi-Agent Workflows:** Coordinates specialized agents for diagnosis, planning, execution, and validation.
*   **Diagnosis & Root Cause Analysis:** Analyzes logs, metrics, and cluster state to pinpoint root causes.
*   **Remediation Planning:** Proposes one or more safe and effective remediation plans.
*   **Sandbox-First Execution & Validation:** Applies candidate fixes in isolated `kind` environments and verifies their success without risking production workloads.
*   **Historical Incident Matching:** Queries a knowledge base (Qdrant) for similar past incidents and their resolutions to inform current actions.
*   **Operator Dashboard:** Provides a user interface for live cluster/agent status, decision control, and approval/denial of agent actions.

---

## Tech Stack

*   **Frontend**: React, Next.js
*   **Backend**: FastAPI (Python)
*   **Database**: MongoDB (agent configuration), Qdrant (incident history), Redis (live status)
*   **APIs / Services**: OpenTelemetry, LangGraph (agent orchestration), LLM (GPT-5.4 mini for reasoning), Kubernetes API
*   **Observability**: Prometheus, Grafana Loki, Jaeger
*   **Sandbox Infrastructure**: `kind`
*   **Tools / Libraries**: MCP (for standardized `kubectl` access), Python SDKs, Node SDKs

---

## Project Setup Instructions

### System Requirements

To run Project Lerna locally using `kind` or deploy to another Kubernetes cluster, ensure your system meets the following requirements:

*   **Operating System:** Linux, macOS, or Windows (with WSL2 for optimal performance on Windows).
*   **Docker:** Required for building container images and running `kind` clusters. Ensure Docker Desktop (Windows/macOS) or Docker Engine (Linux) is installed and running.
*   **kind:** Kubernetes in Docker, used for local cluster deployment.
*   **kubectl:** The Kubernetes command-line tool for interacting with clusters.
*   **Python 3.x:** Recommended for running local development scripts and managing Python-based services outside of containers (e.g., development setup, testing).
*   **Node.js & npm/yarn:** Recommended for local development and build processes of the Dashboard frontend.

### Clone the Repository

```bash
git clone https://github.com/KrithiAS10/hacktofuture4-A10.git
cd hacktofuture4-A10
```

### Kubernetes Quickstart (Lerna stack with `kind` - Recommended)

From the repository root, run the deployment script:

*   **Windows (PowerShell):**
    ```powershell
    .\scripts\deploy-kind.ps1
    ```
*   **Linux / macOS:**
    ```bash
    chmod +x scripts/deploy-kind.sh
    ./scripts/deploy-kind.sh
    ```

This script will:
*   Create a `kind` cluster named `lerna`.
*   Install `ingress-nginx`.
*   Build and load `lerna-backend:latest`, `lerna-dashboard:latest`, `lerna-agents:latest`, and `lerna-detection:latest` images into the cluster.
*   Apply the observation stack and application manifests.
*   Wait for all rollouts to complete.

After a successful run:

*   Open your browser to **http://localhost:8080** (ingress maps host port **8080** to the controller).
*   Optional: Add `127.0.0.1 lerna.local` to your hosts file and use **http://lerna.local:8080**.

To tear down the `kind` cluster:
```bash
kind delete cluster --name lerna
```

### Manual `kubectl apply` (for any Kubernetes cluster)

This approach requires building and pushing Docker images to a registry accessible by your Kubernetes cluster and updating image references in the deployment manifests.

**Deploy Order:**

1.  **Observation Stack**
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

2.  **App Namespaces and Services**
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

**Important Notes for Manual Deployment:**

*   **Docker Images:** You will need to build and push the Docker images for `lerna-backend`, `lerna-agents`, `lerna-detection`, and `lerna-dashboard` to your preferred container registry.
    *   Update image names and `imagePullPolicy` in `backend/k8s/backend-deployment.yaml`, `agents-layer/k8s/agents-deployment.yaml`, `detection-service/k8s/detection-deployment.yaml`, and `dashboard/k8s/dashboard-deployment.yaml` to point to your registry. Set `imagePullPolicy` to `Always` or `IfNotPresent` as appropriate.
*   **Ingress:** The ingress is configured to route `/api` to the backend and `/` to the dashboard, allowing frontend-backend communication without CORS issues. For `kind` specific hosts (`localhost`, `lerna.local`), these are defined in `k8s/lerna-ingress.yaml`. You may need to adjust this for your cluster's ingress setup.