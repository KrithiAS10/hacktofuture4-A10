from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models import DetectionCheckResponse, DetectionEvidence
from app.services.observability import ObservabilityService

logger = logging.getLogger(__name__)

ERROR_KEYWORDS = ("error", "exception", "fail", "failed", "panic", "fatal", "timeout")
WARN_KEYWORDS = ("warn", "warning", "degraded", "retry")


class DetectionService:
    def __init__(self, obs_service: ObservabilityService) -> None:
        self._obs = obs_service

    async def run_check(
        self,
        cluster_snapshot: Dict[str, Any],
        log_query: str = "{}",
        log_limit: int = 150,
    ) -> DetectionCheckResponse:
        loki_raw = await self._obs.query_logs(query=log_query, limit=log_limit)
        normalized = self._normalize_signals(loki_raw, cluster_snapshot)
        correlated = self._correlate(normalized)

        error_count = sum(1 for item in normalized if item.severity in {"error", "critical"})
        warning_count = sum(1 for item in normalized if item.severity == "warning")
        has_error = error_count > 0
        message = (
            f"Errors detected in observation signals ({error_count} high-severity matches)."
            if has_error
            else "No errors detected in the latest observation signals."
        )
        return DetectionCheckResponse(
            has_error=has_error,
            message=message,
            checked_at=datetime.now(tz=timezone.utc).isoformat(),
            summary={
                "signals_scanned": len(normalized),
                "error_count": error_count,
                "warning_count": warning_count,
                "correlated_groups": len(correlated),
            },
            evidence=normalized[:20],
        )

    def _normalize_signals(
        self,
        loki_raw: Dict[str, Any],
        cluster_snapshot: Dict[str, Any],
    ) -> List[DetectionEvidence]:
        output: List[DetectionEvidence] = []
        for stream in loki_raw.get("data", {}).get("result", []):
            service = (
                stream.get("stream", {}).get("lerna.source.service")
                or stream.get("stream", {}).get("service_name")
                or "unknown-service"
            )
            for ts, line in stream.get("values", []):
                output.append(
                    DetectionEvidence(
                        signal_type="log",
                        source=service,
                        severity=self._severity_from_text(line),
                        message=line,
                        timestamp=self._nanos_to_iso(ts),
                    )
                )

        for event in cluster_snapshot.get("recent_events", []):
            event_type = (event.get("type") or "").lower()
            severity = "warning" if event_type == "warning" else "info"
            output.append(
                DetectionEvidence(
                    signal_type="event",
                    source=event.get("object") or event.get("namespace") or "k8s-event",
                    severity=severity,
                    message=event.get("message") or event.get("reason") or "Kubernetes event",
                    timestamp=event.get("last_timestamp"),
                )
            )
        return output

    @staticmethod
    def _correlate(items: List[DetectionEvidence]) -> Dict[str, int]:
        counter = Counter()
        for item in items:
            bucket = f"{item.source}:{item.severity}"
            counter[bucket] += 1
        return dict(counter)

    @staticmethod
    def _severity_from_text(text: str) -> str:
        raw = text.lower()
        if any(token in raw for token in ERROR_KEYWORDS):
            return "error"
        if any(token in raw for token in WARN_KEYWORDS):
            return "warning"
        return "info"

    @staticmethod
    def _nanos_to_iso(raw: str) -> Optional[str]:
        try:
            ts_seconds = int(raw) / 1_000_000_000
            return datetime.fromtimestamp(ts_seconds, tz=timezone.utc).isoformat()
        except Exception:  # pylint: disable=broad-except
            logger.warning("Could not parse Loki timestamp nanoseconds: %r", raw)
            return None
