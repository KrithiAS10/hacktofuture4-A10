#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${TESTAPP_NAMESPACE:-default}"
COLLECTOR_ENDPOINT="${OTEL_COLLECTOR_ENDPOINT:-http://otel-collector.observability.svc.cluster.local:4318}"
COLLECTOR_PROTOCOL="${OTEL_COLLECTOR_PROTOCOL:-http/protobuf}"

DEPLOYMENTS=(
  api-gateway
  inventory-service
  notification-service
  order-service
  payment-service
  product-service
  user-service
)

echo "Patching TestApp deployments in namespace '${NAMESPACE}'..."
echo "Collector endpoint: ${COLLECTOR_ENDPOINT}"
echo "Collector protocol: ${COLLECTOR_PROTOCOL}"

for name in "${DEPLOYMENTS[@]}"; do
  if ! kubectl get "deployment/${name}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    echo "Skipping missing deployment: ${name}"
    continue
  fi

  kubectl set env "deployment/${name}" -n "${NAMESPACE}" \
    OTEL_EXPORTER_OTLP_ENDPOINT="${COLLECTOR_ENDPOINT}" \
    OTEL_EXPORTER_OTLP_PROTOCOL="${COLLECTOR_PROTOCOL}" \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=otlp \
    OTEL_LOGS_EXPORTER=otlp \
    OTEL_SERVICE_NAME="${name}"
done

echo ""
echo "Waiting for rollout to complete..."
for name in "${DEPLOYMENTS[@]}"; do
  if ! kubectl get "deployment/${name}" -n "${NAMESPACE}" >/dev/null 2>&1; then
    continue
  fi
  kubectl rollout status "deployment/${name}" -n "${NAMESPACE}" --timeout=120s
done

echo ""
echo "Done. TestApp OTEL routing now targets the observation-layer collector."
