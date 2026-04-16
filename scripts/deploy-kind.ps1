#Requires -Version 5.1
<#
.SYNOPSIS
  Create/load kind cluster and deploy observation stack + full Lerna app (kustomize).
  Requires: Docker Desktop, kind, kubectl
  From repo root: .\scripts\deploy-kind.ps1
  Env: KIND_CLUSTER_NAME (default lerna), LERNA_NAMESPACE (default lerna)
#>
$ErrorActionPreference = "Stop"
$ClusterName = if ($env:KIND_CLUSTER_NAME) { $env:KIND_CLUSTER_NAME } else { "lerna" }
$LernaNs = if ($env:LERNA_NAMESPACE) { $env:LERNA_NAMESPACE } else { "lerna" }
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Need-Cmd([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}
Need-Cmd docker
Need-Cmd kind
Need-Cmd kubectl

$clusterList = kind get clusters 2>$null
$haveCluster = $false
if ($clusterList) {
    foreach ($line in ($clusterList -split "`n")) {
        if ($line.Trim() -eq $ClusterName) { $haveCluster = $true; break }
    }
}
if (-not $haveCluster) {
    Write-Host "Creating kind cluster '$ClusterName'..."
    kind create cluster --name $ClusterName --config (Join-Path $Root "kind\cluster-config.yaml")
} else {
    Write-Host "Using existing kind cluster '$ClusterName'"
}
kubectl config use-context "kind-$ClusterName"

Write-Host "Installing ingress-nginx (kind provider)..."
kubectl apply -f "https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"
kubectl wait --namespace ingress-nginx `
    --for=condition=ready pod `
    --selector=app.kubernetes.io/component=controller `
    --timeout=180s

Write-Host "Building and loading app images..."
# Backend Dockerfile copies `lerna_shared` + `backend`; build context must be repo root.
docker build -t lerna-backend:latest -f (Join-Path $Root "backend\Dockerfile") $Root
docker build -t lerna-dashboard:latest -f (Join-Path $Root "dashboard\Dockerfile") (Join-Path $Root "dashboard")
docker build -t lerna-agents:latest -f (Join-Path $Root "agents-layer\Dockerfile") $Root
docker build -t lerna-detection:latest -f (Join-Path $Root "detection-service\Dockerfile") $Root
kind load docker-image lerna-backend:latest --name $ClusterName
kind load docker-image lerna-dashboard:latest --name $ClusterName
kind load docker-image lerna-agents:latest --name $ClusterName
kind load docker-image lerna-detection:latest --name $ClusterName

Write-Host "Applying observation layer..."
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\namespace.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\loki-configmap.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\loki-deployment.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\jaeger-deployment.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\prometheus-configmap.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\prometheus-deployment.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\otel-collector-configmap.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\otel-collector-rbac.yaml")
kubectl apply --validate=false -f (Join-Path $Root "observation-layer\k8s\otel-collector-deployment.yaml")

Write-Host "Applying Lerna app stack (namespace: $LernaNs)..."
kubectl create namespace $LernaNs --dry-run=client -o yaml | kubectl apply --validate=false -f -
$KustomPath = Join-Path $Root "k8s\lerna-stack\kustomization.yaml"
$KustomOrig = Get-Content -LiteralPath $KustomPath -Raw
try {
    $KustomPatched = $KustomOrig -replace '(?m)^namespace:\s+\S+$', "namespace: $LernaNs"
    Set-Content -LiteralPath $KustomPath -Value $KustomPatched
    # `kubectl apply -k` does not accept --load-restrictor on some clients; pipe `kubectl kustomize` instead.
    $kustDir = Join-Path $Root "k8s\lerna-stack"
    kubectl kustomize $kustDir --load-restrictor=LoadRestrictionsNone | kubectl apply --validate=false -f -
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl kustomize/apply failed (exit $LASTEXITCODE)"
    }
} finally {
    Set-Content -LiteralPath $KustomPath -Value $KustomOrig
}

kubectl rollout status deployment/prometheus -n observability --timeout=120s
kubectl rollout status deployment/loki -n observability --timeout=120s
kubectl rollout status deployment/jaeger -n observability --timeout=120s
kubectl rollout status deployment/otel-collector -n observability --timeout=300s
kubectl rollout status deployment/redis -n $LernaNs --timeout=120s
kubectl rollout status deployment/qdrant -n $LernaNs --timeout=120s
kubectl rollout status deployment/lerna-backend -n $LernaNs --timeout=120s
kubectl rollout status deployment/lerna-dashboard -n $LernaNs --timeout=120s
kubectl rollout status deployment/lerna-agents -n $LernaNs --timeout=120s
kubectl rollout status deployment/lerna-detection -n $LernaNs --timeout=120s

Write-Host ""
Write-Host "Done. Open: http://localhost:8080"
Write-Host "Optional hosts: 127.0.0.1 lerna.local  ->  http://lerna.local:8080"
Write-Host "kubectl context: kind-$ClusterName"
Write-Host "Lerna namespace: $LernaNs"
