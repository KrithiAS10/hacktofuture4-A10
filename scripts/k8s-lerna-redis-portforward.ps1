# Forward Lerna cluster Redis (namespace lerna) to localhost:16379 so it does not clash with
# WSL or local Redis on 6379. Leave this running while you run scripts/trim_lerna_agent_redis.py
# with REDIS_URL=redis://127.0.0.1:16379/0
#
#   $env:REDIS_URL = 'redis://127.0.0.1:16379/0'
#   python scripts/trim_lerna_agent_redis.py

$ErrorActionPreference = "Stop"
$localPort = 16379
$remotePort = 6379

Write-Host "Forwarding lerna/redis -> 127.0.0.1:${localPort} (remote :${remotePort}). Ctrl+C to stop." -ForegroundColor Cyan
kubectl port-forward -n lerna service/redis "${localPort}:${remotePort}"
