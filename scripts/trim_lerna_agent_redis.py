"""
One-off maintenance: keep the N newest agent workflows in Redis (by accepted_at) and drop the rest,
including stale incident→workflow bindings and detection retry rows for removed incidents.

Does not import agents-layer code. Key prefixes must stay in sync with lerna_agent/store.py and
detection-service/app/services/store.py.

**Kubernetes (Lerna namespace)** — forward cluster Redis to a *non-default* local port so you do not
hit WSL/Docker Redis on 6379. In one terminal:

  .\\scripts\\k8s-lerna-redis-portforward.ps1

Or manually:

  kubectl port-forward -n lerna service/redis 16379:6379

Then (PowerShell, second terminal):

  $env:REDIS_URL = 'redis://127.0.0.1:16379/0'
  python scripts/trim_lerna_agent_redis.py

**Local Redis** (default URL if REDIS_URL is unset):

  redis://127.0.0.1:6379/0

Optional: KEEP=5 (default 5)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, List

# Must match agents-layer WorkflowStore
WORKFLOW_KEY_PREFIX = "lerna:agents:workflow:"
INCIDENT_WORKFLOW_KEY_PREFIX = "lerna:agents:incident:"
LAST_WORKFLOW_KEY = "lerna:agents:workflow:last"
# Must match detection-service DetectionStateStore
RETRY_KEY = "lerna:detection:retries"
RETRY_ITEM_PREFIX = "lerna:detection:retry:"


async def _run(redis_url: str, keep: int) -> Dict[str, Any]:
    from redis.asyncio import Redis

    r = Redis.from_url(redis_url, decode_responses=True)
    try:
        workflows: List[Dict[str, Any]] = []
        async for key in r.scan_iter(match=f"{WORKFLOW_KEY_PREFIX}*"):
            payload = await r.get(key)
            if not payload:
                continue
            try:
                workflow = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(workflow, dict):
                continue
            wid = workflow.get("workflow_id") or key.removeprefix(WORKFLOW_KEY_PREFIX)
            workflow["workflow_id"] = wid
            workflows.append(workflow)

        workflows.sort(key=lambda item: str(item.get("accepted_at") or ""), reverse=True)
        kept = workflows[:keep]
        removed = workflows[keep:]
        kept_ids = {str(w.get("workflow_id")) for w in kept if w.get("workflow_id")}

        deleted_workflows = 0
        removed_incident_ids: List[str] = []
        for w in removed:
            wid = w.get("workflow_id")
            if not wid:
                continue
            iid = w.get("incident_id")
            if iid:
                removed_incident_ids.append(str(iid))
            await r.delete(f"{WORKFLOW_KEY_PREFIX}{wid}")
            deleted_workflows += 1

        deleted_bindings = 0
        async for key in r.scan_iter(match=f"{INCIDENT_WORKFLOW_KEY_PREFIX}*"):
            workflow_id = await r.get(key)
            if workflow_id and str(workflow_id) not in kept_ids:
                await r.delete(key)
                deleted_bindings += 1

        if kept:
            first_id = kept[0].get("workflow_id")
            if first_id:
                await r.set(LAST_WORKFLOW_KEY, str(first_id))
            else:
                await r.delete(LAST_WORKFLOW_KEY)
        else:
            await r.delete(LAST_WORKFLOW_KEY)

        for iid in removed_incident_ids:
            await r.zrem(RETRY_KEY, iid)
            await r.delete(f"{RETRY_ITEM_PREFIX}{iid}")

        return {
            "kept_count": len(kept),
            "deleted_workflows": deleted_workflows,
            "deleted_incident_bindings": deleted_bindings,
            "kept_workflow_ids": sorted(kept_ids),
            "removed_incident_ids": removed_incident_ids,
        }
    finally:
        await r.aclose()


def main() -> None:
    # Default is local 6379; use redis://127.0.0.1:16379/0 when port-forwarding k8s (see docstring).
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:16378/0").strip()
    keep = int(os.getenv("KEEP", "5"))
    if keep < 0:
        print("KEEP must be >= 0", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(_run(redis_url, keep))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
