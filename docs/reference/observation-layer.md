# Observation layer

Local observation stack for Project Lerna:

- OpenTelemetry Collector (ingestion and routing)
- Prometheus (metrics)
- Loki (logs)
- Jaeger (traces)

## Phase 1: platform defaults

The local collector config (`otel-collector-config.yaml`) applies defaults and enrichment so applications do not need to send every field manually.

### Minimum application fields

- `service.name`
- `message` (logs)
- `severity` (logs)
- `timestamp`

If `service.name` is missing, the collector falls back to `unknown-service`.

### Canonical normalization

Collector pipelines map source metadata into:

- `lerna.source.service`
- `lerna.source.namespace`
- `lerna.source.environment`
- `lerna.telemetry.signal_owner`

Schema reference in the repo: `observation-layer/normalization/canonical-schema.yaml`.

## Start the stack locally

From `observation-layer`:

```powershell
docker compose up -d
```

## Endpoints

- OTLP gRPC: `localhost:4317`
- OTLP HTTP: `localhost:4318`
- Prometheus UI: `http://localhost:9090`
- Loki API: `http://localhost:3100`
- Jaeger UI: `http://localhost:16686`

## Data flow

Applications and agents send OTLP to the collector.

- Logs: OTel Collector → Loki
- Metrics: OTel Collector → Prometheus exporter (scraped by Prometheus)
- Traces: OTel Collector → Jaeger

## Phase 2: Kubernetes enrichment

Use `otel-collector-k8s-config.yaml` in Kubernetes for `k8sattributes` enrichment, for example:

- `k8s.namespace.name`
- `k8s.pod.name`
- `k8s.deployment.name`
- `k8s.node.name`

### Apply manifests

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

Paths above are relative to `observation-layer` in the repository. Without in-cluster RBAC, `k8sattributes` cannot enrich telemetry.

### Kubernetes events

The Kubernetes collector config enables the `k8s_events` receiver and routes cluster events into the logs pipeline (for example CrashLoopBackOff, scheduling failures, OOM-related warnings).

## Next steps

- Grafana dashboards for operator visibility (planned).
