"""Read-only Kubernetes tools for diagnosis."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from kubernetes.client import ApiException

from ._k8s import assert_namespace_allowed, get_k8s, sanitize


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "error": msg}


def get_pod_details(namespace: str, pod_name: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        pod = apis.core.read_namespaced_pod(name=pod_name, namespace=namespace)
        return {"ok": True, "pod": sanitize(pod)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_pod_logs(
    namespace: str,
    pod_name: str,
    container: Optional[str] = None,
    tail_lines: int = 100,
    previous: bool = False,
    retry_attempts: int = 4,
    retry_delay_seconds: float = 1.0,
) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    attempts = max(1, int(retry_attempts))
    last_err: Optional[str] = None
    for attempt in range(attempts):
        try:
            logs = apis.core.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                previous=previous,
            )
            out: Dict[str, Any] = {"ok": True, "logs": logs}
            if attempt > 0:
                out["note"] = f"Succeeded after {attempt + 1} attempt(s); earlier failures were likely transient."
            return out
        except ApiException as exc:
            last_err = str(exc)
            if exc.status == 404 and attempt < attempts - 1:
                time.sleep(retry_delay_seconds)
                continue
            break
        except Exception as exc:  # pylint: disable=broad-except
            last_err = str(exc)
            break
    err = last_err or "unknown error"
    hint = (
        "If the pod was replaced (CrashLoop, rollout), the name from an older snapshot may be stale—"
        "call kubernetes_cluster_snapshot or list pods again. For logs from the last crashed instance, try previous=true."
    )
    return {**_err(err), "hint": hint}


def list_recent_events(
    namespace: Optional[str] = None,
    field_selector: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        if namespace:
            assert_namespace_allowed(namespace)
            ev = apis.core.list_namespaced_event(
                namespace=namespace,
                field_selector=field_selector,
                limit=limit,
            )
        else:
            ev = apis.core.list_event_for_all_namespaces(field_selector=field_selector, limit=limit)
        items = [sanitize(e) for e in ev.items]
        return {"ok": True, "events": items}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_deployment_status(namespace: str, deployment_name: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        dep = apis.apps.read_namespaced_deployment_status(name=deployment_name, namespace=namespace)
        return {"ok": True, "deployment": sanitize(dep)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def _match_labels_selector(match_labels: Optional[Dict[str, str]]) -> str:
    if not match_labels:
        return ""
    return ",".join(f"{k}={v}" for k, v in sorted(match_labels.items()))


def get_rollout_history(namespace: str, deployment_name: str) -> Dict[str, Any]:
    """List ReplicaSets for a Deployment with revision annotations (rollout history)."""
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        dep = apis.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        selector = dep.spec.selector.match_labels or {}
        label_selector = _match_labels_selector(selector)
        rss = apis.apps.list_namespaced_replica_set(
            namespace=namespace,
            label_selector=label_selector or None,
        ).items
        rows: List[Dict[str, Any]] = []
        for rs in rss:
            rev = (rs.metadata.annotations or {}).get("deployment.kubernetes.io/revision")
            rows.append(
                {
                    "name": rs.metadata.name,
                    "revision": rev,
                    "created": rs.metadata.creation_timestamp.isoformat() if rs.metadata.creation_timestamp else None,
                    "replicas": rs.spec.replicas,
                    "ready": rs.status.ready_replicas,
                }
            )
        rows.sort(key=lambda r: int(r["revision"] or 0))
        return {"ok": True, "replica_sets": rows}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_horizontal_pod_autoscaler(namespace: str, name: Optional[str] = None) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        if name:
            hpa = apis.autoscaling.read_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace)
            return {"ok": True, "hpas": [sanitize(hpa)]}
        lst = apis.autoscaling.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
        return {"ok": True, "hpas": [sanitize(x) for x in lst.items]}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def list_jobs_and_cronjobs(namespace: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        jobs = apis.batch.list_namespaced_job(namespace=namespace)
        crons = apis.batch.list_namespaced_cron_job(namespace=namespace)
        return {
            "ok": True,
            "jobs": [sanitize(j) for j in jobs.items],
            "cron_jobs": [sanitize(c) for c in crons.items],
        }
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_network_policies(namespace: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        lst = apis.networking.list_namespaced_network_policy(namespace=namespace)
        return {"ok": True, "network_policies": [sanitize(x) for x in lst.items]}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_service_endpoints(namespace: str, service_name: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        ep = apis.core.read_namespaced_endpoints(name=service_name, namespace=namespace)
        return {"ok": True, "endpoints": sanitize(ep)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_persistent_volume_claims(namespace: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        lst = apis.core.list_namespaced_persistent_volume_claim(namespace=namespace)
        return {"ok": True, "pvcs": [sanitize(x) for x in lst.items]}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_configmap_secret_metadata(namespace: str) -> Dict[str, Any]:
    """List ConfigMaps and Secrets with key names only (no secret values)."""
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        cms = apis.core.list_namespaced_config_map(namespace=namespace)
        secs = apis.core.list_namespaced_secret(namespace=namespace)
        configmaps = []
        for cm in cms.items:
            keys = list((cm.data or {}).keys()) + list((cm.binary_data or {}).keys())
            configmaps.append({"name": cm.metadata.name, "keys": keys})
        secrets = []
        for sec in secs.items:
            sd = getattr(sec, "string_data", None) or {}
            keys = list((sec.data or {}).keys()) + list(sd.keys())
            secrets.append({"name": sec.metadata.name, "keys": keys})
        return {"ok": True, "configmaps": configmaps, "secrets": secrets}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def get_node_conditions() -> Dict[str, Any]:
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        nodes = apis.core.list_node().items
        out: List[Dict[str, Any]] = []
        for node in nodes:
            conds = []
            for c in node.status.conditions or []:
                conds.append(
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message,
                        "last_heartbeat": c.last_heartbeat_time.isoformat() if c.last_heartbeat_time else None,
                    }
                )
            out.append({"name": node.metadata.name, "conditions": conds})
        return {"ok": True, "nodes": out}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def list_pods_on_node(node_name: str) -> Dict[str, Any]:
    """List pods scheduled on a given node (field selector)."""
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        pods = apis.core.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}").items
        slim = [
            {
                "namespace": p.metadata.namespace,
                "name": p.metadata.name,
                "phase": p.status.phase,
            }
            for p in pods
        ]
        return {"ok": True, "node": node_name, "pods": slim}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))
