#!/usr/bin/env bash
# Deploy observation stack, Redis, Lerna backend + dashboard to a local kind cluster.
# Prerequisites: docker, kind, kubectl
# Usage: from repo root: ./scripts/deploy-kind.sh
set -euo pipefail

CLUSTER_NAME="${KIND_CLUSTER_NAME:-lerna}"
LERNA_NAMESPACE="${LERNA_NAMESPACE:-lerna}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
need docker
need kind
need kubectl

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "Creating kind cluster '$CLUSTER_NAME'..."
  kind create cluster --name "$CLUSTER_NAME" --config "$ROOT/kind/cluster-config.yaml"
else
  echo "Using existing kind cluster '$CLUSTER_NAME'"
fi
kubectl config use-context "kind-${CLUSTER_NAME}"

echo "Installing ingress-nginx (kind provider)..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s

echo "Building and loading app images..."
# Backend Dockerfile copies `lerna_shared` + `backend`; build context must be repo root.
docker build -t lerna-backend:latest -f backend/Dockerfile "$ROOT"
docker build -t lerna-dashboard:latest -f dashboard/Dockerfile dashboard
docker build -t lerna-agents:latest -f agents-layer/Dockerfile "$ROOT"
docker build -t lerna-detection:latest -f detection-service/Dockerfile "$ROOT"
kind load docker-image lerna-backend:latest --name "$CLUSTER_NAME"
kind load docker-image lerna-dashboard:latest --name "$CLUSTER_NAME"
kind load docker-image lerna-agents:latest --name "$CLUSTER_NAME"
kind load docker-image lerna-detection:latest --name "$CLUSTER_NAME"

echo "Applying observation layer..."
kubectl apply -f observation-layer/k8s/namespace.yaml
kubectl apply -f observation-layer/k8s/loki-configmap.yaml
kubectl apply -f observation-layer/k8s/loki-deployment.yaml
kubectl apply -f observation-layer/k8s/jaeger-deployment.yaml
kubectl apply -f observation-layer/k8s/prometheus-configmap.yaml
kubectl apply -f observation-layer/k8s/prometheus-deployment.yaml
kubectl apply -f observation-layer/k8s/otel-collector-configmap.yaml
kubectl apply -f observation-layer/k8s/otel-collector-rbac.yaml
kubectl apply -f observation-layer/k8s/otel-collector-deployment.yaml

echo "Applying Lerna app stack (namespace: ${LERNA_NAMESPACE})..."
kubectl create namespace "${LERNA_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
KUSTOM="k8s/lerna-stack/kustomization.yaml"
cp "${KUSTOM}" "${KUSTOM}.bak"
sed "s/^namespace: .*/namespace: ${LERNA_NAMESPACE}/" "${KUSTOM}.bak" > "${KUSTOM}"
if ! kubectl kustomize k8s/lerna-stack --load-restrictor=LoadRestrictionsNone | kubectl apply -f -; then
  mv "${KUSTOM}.bak" "${KUSTOM}"
  exit 1
fi
mv "${KUSTOM}.bak" "${KUSTOM}"

kubectl rollout status deployment/prometheus -n observability --timeout=120s
kubectl rollout status deployment/loki -n observability --timeout=120s
kubectl rollout status deployment/jaeger -n observability --timeout=120s
kubectl rollout status deployment/otel-collector -n observability --timeout=300s
kubectl rollout status deployment/redis -n "${LERNA_NAMESPACE}" --timeout=120s
kubectl rollout status deployment/qdrant -n "${LERNA_NAMESPACE}" --timeout=120s
kubectl rollout status deployment/lerna-backend -n "${LERNA_NAMESPACE}" --timeout=120s
kubectl rollout status deployment/lerna-dashboard -n "${LERNA_NAMESPACE}" --timeout=120s
kubectl rollout status deployment/lerna-agents -n "${LERNA_NAMESPACE}" --timeout=120s
kubectl rollout status deployment/lerna-detection -n "${LERNA_NAMESPACE}" --timeout=120s

echo ""
echo "Done. Open: http://localhost:8080"
echo "Optional hosts entry: 127.0.0.1 lerna.local  ->  http://lerna.local:8080"
echo "Context: kind-${CLUSTER_NAME}"
echo "Lerna namespace: ${LERNA_NAMESPACE}"
