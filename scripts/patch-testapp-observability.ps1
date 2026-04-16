$ErrorActionPreference = "Stop"

$namespace = if ($env:TESTAPP_NAMESPACE) { $env:TESTAPP_NAMESPACE } else { "default" }
$collectorEndpoint = if ($env:OTEL_COLLECTOR_ENDPOINT) { $env:OTEL_COLLECTOR_ENDPOINT } else { "http://otel-collector.observability.svc.cluster.local:4318" }
$collectorProtocol = if ($env:OTEL_COLLECTOR_PROTOCOL) { $env:OTEL_COLLECTOR_PROTOCOL } else { "http/protobuf" }

$deployments = @(
    "api-gateway",
    "inventory-service",
    "notification-service",
    "order-service",
    "payment-service",
    "product-service",
    "user-service"
)

Write-Host "Patching TestApp deployments in namespace '$namespace'..."
Write-Host "Collector endpoint: $collectorEndpoint"
Write-Host "Collector protocol: $collectorProtocol"

foreach ($name in $deployments) {
    $exists = kubectl get deployment/$name -n $namespace --ignore-not-found -o name
    if (-not $exists) {
        Write-Host "Skipping missing deployment: $name"
        continue
    }

    kubectl set env deployment/$name -n $namespace `
        OTEL_EXPORTER_OTLP_ENDPOINT=$collectorEndpoint `
        OTEL_EXPORTER_OTLP_PROTOCOL=$collectorProtocol `
        OTEL_TRACES_EXPORTER=otlp `
        OTEL_METRICS_EXPORTER=otlp `
        OTEL_LOGS_EXPORTER=otlp `
        OTEL_SERVICE_NAME=$name | Out-Host
}

Write-Host ""
Write-Host "Waiting for rollout to complete..."
foreach ($name in $deployments) {
    $exists = kubectl get deployment/$name -n $namespace --ignore-not-found -o name
    if (-not $exists) {
        continue
    }
    kubectl rollout status deployment/$name -n $namespace --timeout=120s | Out-Host
}

Write-Host ""
Write-Host "Done. TestApp OTEL routing now targets the observation-layer collector."
