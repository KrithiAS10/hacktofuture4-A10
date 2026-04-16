param(
    [string]$RepoRoot = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [string]$ClusterName = 'testapp'
)

function Fail($message) {
    Write-Error $message
    exit 1
}

function RunCommand($command) {
    Write-Host "`n>> $command"
    iex $command
    if ($LASTEXITCODE -ne 0) {
        Fail ("Command failed with exit code {0}: {1}" -f $LASTEXITCODE, $command)
    }
}

Write-Host 'Checking local environment...'

docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail 'Docker engine is not running or not reachable. Start Docker Desktop / Docker daemon and retry.'
}

kind version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail 'kind is not installed or not on PATH.'
}

kubectl version --client > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail 'kubectl is not installed or not on PATH.'
}

Write-Host "Docker, kind, and kubectl are available. Checking kind cluster '$ClusterName'..."

$clusters = kind get clusters 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail 'kind failed to list clusters. Verify Docker is running and accessible.'
}

$clusterExists = $false
foreach ($line in $clusters -split "`n") {
    if ($line.Trim() -eq $ClusterName) {
        $clusterExists = $true
        break
    }
}

if (-not $clusterExists) {
    Write-Host "Cluster '$ClusterName' not found. Creating it..."
    RunCommand "kind create cluster --name $ClusterName"
}

Set-Location $RepoRoot

Write-Host 'Building Docker images...'
RunCommand "docker build -f backend/Dockerfile -t lerna-backend:latest ."
RunCommand "docker build -f agents-layer/Dockerfile -t lerna-agents:latest ."
RunCommand "docker build -f detection-service/Dockerfile -t lerna-detection:latest ."
RunCommand "docker build -f dashboard/Dockerfile -t lerna-dashboard:latest dashboard"

Write-Host 'Loading images into kind cluster...'
RunCommand "kind load docker-image lerna-backend:latest lerna-agents:latest lerna-detection:latest lerna-dashboard:latest --name $ClusterName"

Write-Host 'Applying Kubernetes manifests...'
RunCommand "kubectl apply -f observation-layer/k8s/namespace.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/loki-configmap.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/loki-deployment.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/jaeger-deployment.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/prometheus-configmap.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/prometheus-deployment.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/otel-collector-configmap.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/otel-collector-rbac.yaml"
RunCommand "kubectl apply -f observation-layer/k8s/otel-collector-deployment.yaml"
RunCommand "kubectl apply -f k8s/namespace-lerna.yaml"
RunCommand "kubectl apply -f k8s/redis-deployment.yaml"
RunCommand "kubectl apply -f backend/k8s/backend-rbac.yaml"
RunCommand "kubectl apply -f backend/k8s/backend-deployment.yaml"
RunCommand "kubectl apply -f agents-layer/k8s/agents-deployment.yaml"
RunCommand "kubectl apply -f detection-service/k8s/detection-deployment.yaml"
RunCommand "kubectl apply -f dashboard/k8s/dashboard-deployment.yaml"
RunCommand "kubectl apply -f k8s/lerna-ingress.yaml"

Write-Host 'Checking cluster resources...'
RunCommand "kubectl get pods -n lerna -o wide"
RunCommand "kubectl get svc -n lerna"
RunCommand "kubectl get ingress -n lerna"

Write-Host '`nDeployment completed. If you need rollout status, run `kubectl rollout status deployment/<deployment-name> -n <namespace>` manually.'
