from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

ERROR_KEYWORDS = ("error", "exception", "fail", "failed", "panic", "fatal", "timeout")
WARN_KEYWORDS = ("warn", "warning", "degraded", "retry")


class DetectionEvidence(BaseModel):
    signal_type: str
    source: str
    severity: str
    message: str
    timestamp: Optional[str] = None
    namespace: Optional[str] = None


class DetectionCheckResponse(BaseModel):
    has_error: bool
    message: str
    checked_at: str
    summary: Dict[str, int]
    evidence: List[DetectionEvidence]


class DetectionIncident(BaseModel):
    incident_id: str
    fingerprint: str
    detected_at: str
    service: str
    namespace: str
    severity: str
    summary: str
    evidence: List[DetectionEvidence]
    cluster_snapshot: Optional[Dict[str, Any]] = None
    incident_class: str
    dominant_signature: str
    correlation: Dict[str, int] = Field(default_factory=dict)
    cost: float = Field(
        default=0.0,
        ge=0,
        description="Optional client hint; agents service bills from measured LLM usage at workflow completion.",
    )


class DetectionRunResult(BaseModel):
    check: DetectionCheckResponse
    incident: Optional[DetectionIncident] = None


class AgentTriggerResponse(BaseModel):
    accepted: bool
    workflow_id: str
    status: str


def severity_from_text(text: str) -> str:
    raw = text.lower()
    if any(token in raw for token in ERROR_KEYWORDS):
        return "error"
    if any(token in raw for token in WARN_KEYWORDS):
        return "warning"
    return "info"


def nanos_to_iso(raw: str) -> Optional[str]:
    try:
        ts_seconds = int(raw) / 1_000_000_000
        return datetime.fromtimestamp(ts_seconds, tz=timezone.utc).isoformat()
    except Exception:
        return None


def normalize_signals(
    loki_raw: Dict[str, Any],
    cluster_snapshot: Dict[str, Any],
) -> List[DetectionEvidence]:
    output: List[DetectionEvidence] = []
    for stream in loki_raw.get("data", {}).get("result", []):
        labels = stream.get("stream", {})
        service = labels.get("lerna.source.service") or labels.get("service_name") or "unknown-service"
        namespace = labels.get("lerna.source.namespace") or cluster_snapshot.get("namespace_scope")
        for ts, line in stream.get("values", []):
            output.append(
                DetectionEvidence(
                    signal_type="log",
                    source=service,
                    severity=severity_from_text(line),
                    message=line,
                    timestamp=nanos_to_iso(ts),
                    namespace=namespace,
                )
            )

    for event in cluster_snapshot.get("recent_events", []):
        event_type = (event.get("type") or "").lower()
        msg = event.get("message") or event.get("reason") or "Kubernetes event"
        # Same keyword rules as log lines so e.g. "Back-off restarting failed container" counts as error.
        text_sev = severity_from_text(msg)
        if text_sev == "error":
            severity: str = "error"
        elif text_sev == "warning":
            severity = "warning"
        elif event_type == "warning":
            severity = "warning"
        else:
            severity = "info"
        output.append(
            DetectionEvidence(
                signal_type="event",
                source=event.get("object") or event.get("namespace") or "k8s-event",
                severity=severity,
                message=msg,
                timestamp=event.get("last_timestamp"),
                namespace=event.get("namespace") or cluster_snapshot.get("namespace_scope"),
            )
        )
    return output


def correlation_summary(items: List[DetectionEvidence]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        bucket = f"{item.source}:{item.severity}"
        counter[bucket] += 1
    return dict(counter)


def incident_class_from_evidence(items: List[DetectionEvidence]) -> str:
    corpus = " ".join(item.message.lower() for item in items[:10])
    if "crashloopbackoff" in corpus or "back-off restarting failed container" in corpus:
        return "crashloop"
    if "oomkilled" in corpus or "out of memory" in corpus:
        return "resource-pressure"
    if "timeout" in corpus:
        return "timeout"
    if "imagepullbackoff" in corpus or "errimagepull" in corpus:
        return "image-pull"
    return "application-error"


def _stable_message_signature(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    normalized = re.sub(r"[0-9a-f]{8,}", "<id>", normalized)
    return normalized[:160]


def evidence_signature(items: List[DetectionEvidence]) -> str:
    relevant = [item for item in items if item.severity in {"error", "warning"}]
    if not relevant:
        return "no-signal"
    counts = Counter(_stable_message_signature(item.message) for item in relevant)
    return counts.most_common(1)[0][0]


def _dominant_service(items: List[DetectionEvidence]) -> str:
    ranked = Counter(item.source for item in items if item.severity in {"error", "warning"})
    if ranked:
        return ranked.most_common(1)[0][0]
    return items[0].source if items else "unknown-service"


def _dominant_namespace(items: List[DetectionEvidence], cluster_snapshot: Dict[str, Any]) -> str:
    ranked = Counter(item.namespace for item in items if item.namespace)
    if ranked:
        return ranked.most_common(1)[0][0] or "default"
    return cluster_snapshot.get("namespace_scope") or "default"


def _incident_severity(error_count: int) -> str:
    if error_count >= 5:
        return "critical"
    if error_count >= 1:
        return "error"
    return "warning"


def fingerprint_incident(service: str, namespace: str, incident_class: str, dominant_signature: str) -> str:
    raw = "::".join([service, namespace, incident_class, dominant_signature])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_detection_run_result(
    loki_raw: Dict[str, Any],
    cluster_snapshot: Dict[str, Any],
    *,
    checked_at: Optional[str] = None,
    evidence_limit: int = 20,
) -> DetectionRunResult:
    normalized = normalize_signals(loki_raw, cluster_snapshot)
    correlated = correlation_summary(normalized)

    error_items = [item for item in normalized if item.severity in {"error", "critical"}]
    warning_count = sum(1 for item in normalized if item.severity == "warning")
    error_count = len(error_items)
    checked = checked_at or datetime.now(tz=timezone.utc).isoformat()
    has_error = error_count > 0
    check = DetectionCheckResponse(
        has_error=has_error,
        message=(
            f"Errors detected in observation signals ({error_count} high-severity matches)."
            if has_error
            else "No errors detected in the latest observation signals."
        ),
        checked_at=checked,
        summary={
            "signals_scanned": len(normalized),
            "error_count": error_count,
            "warning_count": warning_count,
            "correlated_groups": len(correlated),
        },
        evidence=normalized[:evidence_limit],
    )
    if not has_error:
        return DetectionRunResult(check=check, incident=None)

    incident_items = error_items or normalized
    service = _dominant_service(incident_items)
    namespace = _dominant_namespace(incident_items, cluster_snapshot)
    incident_class = incident_class_from_evidence(incident_items)
    dominant_signature = evidence_signature(incident_items)
    fingerprint = fingerprint_incident(service, namespace, incident_class, dominant_signature)
    incident_hash = hashlib.sha1(f"{fingerprint}:{checked}".encode("utf-8")).hexdigest()[:12]
    summary = f"{incident_class} detected for {service} in {namespace}: {dominant_signature}"
    incident = DetectionIncident(
        incident_id=f"inc-{incident_hash}",
        fingerprint=fingerprint,
        detected_at=checked,
        service=service,
        namespace=namespace,
        severity=_incident_severity(error_count),
        summary=summary,
        evidence=normalized[:evidence_limit],
        cluster_snapshot=cluster_snapshot,
        incident_class=incident_class,
        dominant_signature=dominant_signature,
        correlation=correlated,
        cost=0.0,
    )
    return DetectionRunResult(check=check, incident=incident)
