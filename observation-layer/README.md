# Observation Layer

This folder provides a local observation stack for Project Lerna using:

- OpenTelemetry Collector (ingestion + routing)
- Prometheus (metrics storage/query)
- Loki (log storage/query)
- Jaeger (trace storage/query)

## Phase 1 (platform defaults)

The local collector config (`otel-collector-config.yaml`) now applies defaults and enrichment so users do not need to manually send every field.

### Minimum expected app fields

- `service.name`
- `message` (for logs)
- `severity` (for logs)
- `timestamp`

If `service.name` is missing, the collector falls back to `unknown-service`.

### Canonical normalization (implemented)

Collector pipelines now map source metadata into canonical fields:

- `lerna.source.service`
- `lerna.source.namespace`
- `lerna.source.environment`
- `lerna.telemetry.signal_owner`

Canonical schema reference: `normalization/canonical-schema.yaml`

## Start the stack

From this folder:

```powershell
docker compose up -d
```

## Endpoints

- OTLP gRPC ingest: `localhost:4317`
- OTLP HTTP ingest: `localhost:4318`
- Prometheus UI: `http://localhost:9090`
- Loki API: `http://localhost:3100`
- Jaeger UI: `http://localhost:16686`

## Data flow

Applications and agents send OTLP telemetry to the collector.

- Logs -> OTel Collector -> Loki
- Metrics -> OTel Collector -> Prometheus exporter (scraped by Prometheus)
- Traces -> OTel Collector -> Jaeger

## Phase 2 (k8s auto-enrichment with k8sattributes)

Use `otel-collector-k8s-config.yaml` when running in Kubernetes. This auto-adds fields like:

- `k8s.namespace.name`
- `k8s.pod.name`
- `k8s.deployment.name`
- `k8s.node.name`

### Kubernetes setup

```powershell
kubectl create namespace observability
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/loki-configmap.yaml
kubectl apply -f k8s/loki-deployment.yaml
kubectl apply -f k8s/jaeger-deployment.yaml
kubectl apply -f k8s/prometheus-configmap.yaml
kubectl apply -f k8s/prometheus-deployment.yaml
kubectl apply -f k8s/otel-collector-configmap.yaml
kubectl apply -f k8s/otel-collector-rbac.yaml
kubectl apply -f k8s/otel-collector-deployment.yaml
```

Without in-cluster RBAC, `k8sattributes` cannot enrich telemetry.

### Kubernetes events ingestion (implemented)

The k8s collector config now enables the `k8s_events` receiver and routes cluster events into the logs pipeline, so incident-relevant events (CrashLoopBackOff, scheduling failures, OOM-related warnings) are available for detection.

## Next steps

- Add Grafana dashboards for operator visibility.
