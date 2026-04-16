"""Detection scan combining Loki signals and cluster snapshot (aligned with backend `DetectionService`)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .kubernetes_snapshot import kubernetes_cluster_snapshot
from .observability import loki_query_range
from lerna_shared.detection import build_detection_run_result


def run_detection_check(log_query: str = "{}", log_limit: int = 150) -> Dict[str, Any]:
    """
    Run the same style of detection as `GET /api/detection/check`: Loki scan + recent events from cluster snapshot.
    """
    snapshot = kubernetes_cluster_snapshot()
    if not snapshot.get("available"):
        return {
            "ok": False,
            "has_error": False,
            "message": f"Cluster snapshot unavailable: {snapshot.get('reason')}",
            "checked_at": datetime.now(tz=timezone.utc).isoformat(),
            "summary": {},
            "evidence": [],
        }

    try:
        loki_raw = loki_query_range(query=log_query, limit=log_limit)
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "ok": False,
            "has_error": False,
            "message": f"Loki query failed: {exc}",
            "checked_at": datetime.now(tz=timezone.utc).isoformat(),
            "summary": {},
            "evidence": [],
        }
    result = build_detection_run_result(loki_raw, snapshot)
    return {
        "ok": True,
        **result.check.model_dump(),
        "incident": result.incident.model_dump() if result.incident else None,
    }
