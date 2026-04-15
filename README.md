# HackToFuture 4.0 — Template

Welcome to your official HackToFuture 4 repository.

## Kubernetes Quickstart (Lerna stack)

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
   - `kubectl apply -f backend/k8s/backend-rbac.yaml`
   - `kubectl apply -f backend/k8s/backend-deployment.yaml`
   - `kubectl apply -f dashboard/k8s/dashboard-deployment.yaml`
   - `kubectl apply -f k8s/lerna-ingress.yaml`

Notes:

- Replace image placeholders in `backend/k8s/backend-deployment.yaml` and `dashboard/k8s/dashboard-deployment.yaml`.
- Ingress routes `/api` to backend and `/` to dashboard, so frontend can access backend without CORS setup.

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
