# Deploy Lerna on `kind-testapp`

This runbook assumes:

- `kubectl` is pointed at the `kind-testapp` cluster
- Docker Desktop is running
- `kind` is installed

## 1. Verify cluster context

```powershell
kubectl config current-context
kind get clusters
```

Expected:

- context: `kind-testapp`
- cluster: `testapp`

> If Docker is not running, `kind get clusters` will fail with a Docker pipe error. Start Docker Desktop / Docker daemon before continuing.

## 2. Build local images

Run these from the repo root:

```powershell
docker build -f backend/Dockerfile -t lerna-backend:latest .
docker build -f agents-layer/Dockerfile -t lerna-agents:latest .
docker build -f detection-service/Dockerfile -t lerna-detection:latest .
docker build -f dashboard/Dockerfile -t lerna-dashboard:latest dashboard
```

## 3. Load images into the `kind` cluster

```powershell
kind load docker-image lerna-backend:latest lerna-agents:latest lerna-detection:latest lerna-dashboard:latest --name testapp
```

## 4. Deploy observability layer

```powershell
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

If the collector image tag in the manifest fails, pin it to the known working version:

```powershell
kubectl set image deployment/otel-collector -n observability otel-collector=otel/opentelemetry-collector-contrib:0.113.0
```

## 5. Deploy app namespaces and services

```powershell
kubectl apply -f k8s/namespace-lerna.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f backend/k8s/backend-rbac.yaml
kubectl apply -f backend/k8s/backend-deployment.yaml
kubectl apply -f agents-layer/k8s/agents-deployment.yaml
kubectl apply -f detection-service/k8s/detection-deployment.yaml
kubectl apply -f dashboard/k8s/dashboard-deployment.yaml
kubectl apply -f k8s/lerna-ingress.yaml
```

## 6. Optional: deploy the demo failure microservices

```powershell
kubectl apply -f k8s/detection-demo-errors.yaml
```

These pods are intentionally unhealthy and are meant to exercise detection.

## 6b. Route TestApp telemetry to the observation collector

If TestApp services are running in `default`, patch them so traces/metrics/logs export to the observation-layer OpenTelemetry Collector:

```powershell
.\scripts\patch-testapp-observability.ps1
```

Linux/macOS:

```bash
chmod +x scripts/patch-testapp-observability.sh
./scripts/patch-testapp-observability.sh
```

Optional overrides:

- `TESTAPP_NAMESPACE` (default: `default`)
- `OTEL_COLLECTOR_ENDPOINT` (default: `http://otel-collector.observability.svc.cluster.local:4318`)
- `OTEL_COLLECTOR_PROTOCOL` (default: `http/protobuf`)

## 7. Check rollout status

```powershell
kubectl rollout status deployment/loki -n observability --timeout=120s
kubectl rollout status deployment/prometheus -n observability --timeout=120s
kubectl rollout status deployment/jaeger -n observability --timeout=120s
kubectl rollout status deployment/otel-collector -n observability --timeout=120s

kubectl rollout status deployment/redis -n lerna --timeout=120s
kubectl rollout status deployment/lerna-backend -n lerna --timeout=120s
kubectl rollout status deployment/lerna-agents -n lerna --timeout=120s
kubectl rollout status deployment/lerna-detection -n lerna --timeout=120s
kubectl rollout status deployment/lerna-dashboard -n lerna --timeout=120s
```

If `kubectl rollout status` fails or crashes, use the safer fallback:

```powershell
kubectl get pods -n observability -o wide
kubectl get pods -n lerna -o wide
kubectl get svc -n lerna
kubectl get ingress -n lerna
```

## 8. Inspect running workloads

```powershell
kubectl get pods -n observability -o wide
kubectl get pods -n lerna -o wide
kubectl get svc -n lerna
kubectl get ingress -n lerna
```

## 9. Restart after rebuilding images

If you rebuild images later, reload them into `kind` and restart the deployments:

```powershell
kind load docker-image lerna-backend:latest lerna-agents:latest lerna-detection:latest lerna-dashboard:latest --name testapp

kubectl rollout restart deployment/lerna-backend -n lerna
kubectl rollout restart deployment/lerna-agents -n lerna
kubectl rollout restart deployment/lerna-detection -n lerna
kubectl rollout restart deployment/lerna-dashboard -n lerna
```

## 10. Useful cleanup commands

Delete only the demo failure workloads:

```powershell
kubectl delete -f k8s/detection-demo-errors.yaml
```

Delete the Lerna app stack:

```powershell
kubectl delete -f k8s/lerna-ingress.yaml
kubectl delete -f dashboard/k8s/dashboard-deployment.yaml
kubectl delete -f detection-service/k8s/detection-deployment.yaml
kubectl delete -f agents-layer/k8s/agents-deployment.yaml
kubectl delete -f backend/k8s/backend-deployment.yaml
kubectl delete -f backend/k8s/backend-rbac.yaml
kubectl delete -f k8s/redis-deployment.yaml
kubectl delete -f k8s/namespace-lerna.yaml
```

Delete the observability stack:

```powershell
kubectl delete -f observation-layer/k8s/otel-collector-deployment.yaml
kubectl delete -f observation-layer/k8s/otel-collector-rbac.yaml
kubectl delete -f observation-layer/k8s/otel-collector-configmap.yaml
kubectl delete -f observation-layer/k8s/prometheus-deployment.yaml
kubectl delete -f observation-layer/k8s/prometheus-configmap.yaml
kubectl delete -f observation-layer/k8s/jaeger-deployment.yaml
kubectl delete -f observation-layer/k8s/loki-deployment.yaml
kubectl delete -f observation-layer/k8s/loki-configmap.yaml
kubectl delete -f observation-layer/k8s/namespace.yaml
```
