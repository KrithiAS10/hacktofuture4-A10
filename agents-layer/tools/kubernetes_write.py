"""Kubernetes mutating tools (rollouts, scale, apply, node cordon)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional

from kubernetes import client as k8s_client
from kubernetes.client import V1EnvVar
from kubernetes.utils import create_from_yaml

from ._k8s import assert_namespace_allowed, get_k8s, sanitize
from .kubernetes_read import _match_labels_selector


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "error": msg}


def kubernetes_rollout_restart(namespace: str, deployment_name: str) -> Dict[str, Any]:
    """Set `kubectl.kubernetes.io/restartedAt` on the pod template to force a rollout."""
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        ts = datetime.now(tz=timezone.utc).isoformat()
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {"kubectl.kubernetes.io/restartedAt": ts},
                    }
                }
            }
        }
        dep = apis.apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=patch,
            _content_type="application/strategic-merge-patch+json",
        )
        return {"ok": True, "deployment": sanitize(dep)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def kubernetes_scale_deployment(namespace: str, deployment_name: str, replicas: int) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        patch = {"spec": {"replicas": replicas}}
        dep = apis.apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=patch,
            _content_type="application/strategic-merge-patch+json",
        )
        return {"ok": True, "deployment": sanitize(dep)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def kubernetes_delete_pod(
    namespace: str,
    pod_name: str,
    grace_period_seconds: Optional[int] = 30,
) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        opts = k8s_client.V1DeleteOptions(propagation_policy="Background")
        if grace_period_seconds is not None:
            opts.grace_period_seconds = grace_period_seconds
        apis.core.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            body=opts,
        )
        return {"ok": True, "deleted": f"{namespace}/{pod_name}"}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def kubernetes_apply_manifest(
    namespace: str,
    manifest_yaml: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Apply YAML documents using `kubernetes.utils.create_from_yaml`. Respects namespace for namespaced kinds."""
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        kwargs: Dict[str, Any] = {}
        if dry_run:
            kwargs["dry_run"] = "All"
        created = create_from_yaml(
            apis.api_client,
            StringIO(manifest_yaml),
            namespace=namespace,
            verbose=False,
            **kwargs,
        )
        return {"ok": True, "created": [str(x) for x in (created or [])]}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def kubernetes_server_side_apply_dry_run(namespace: str, manifest_yaml: str) -> Dict[str, Any]:
    """Convenience alias: `kubernetes_apply_manifest(..., dry_run=True)`."""
    return kubernetes_apply_manifest(namespace=namespace, manifest_yaml=manifest_yaml, dry_run=True)


def set_deployment_image(namespace: str, deployment_name: str, container_name: str, image: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        dep = apis.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        found = False
        for c in dep.spec.template.spec.containers:
            if c.name == container_name:
                c.image = image
                found = True
                break
        if not found:
            return _err(f"container {container_name!r} not found")
        out = apis.apps.replace_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=dep,
        )
        return {"ok": True, "deployment": sanitize(out)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def patch_deployment_env_or_resources(
    namespace: str,
    deployment_name: str,
    container_name: str,
    env: Optional[Dict[str, str]] = None,
    resources: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Merge env vars (by name) and optionally set container resources (requests/limits) on one container.
    `resources` example: `{"requests": {"cpu": "100m"}, "limits": {"memory": "256Mi"}}`.
    """
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    if not env and not resources:
        return _err("provide env and/or resources")
    try:
        dep = apis.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        target = None
        for c in dep.spec.template.spec.containers:
            if c.name == container_name:
                target = c
                break
        if target is None:
            return _err(f"container {container_name!r} not found")
        if env:
            existing = {e.name: e for e in (target.env or [])}
            for k, v in env.items():
                existing[k] = V1EnvVar(name=k, value=v)
            target.env = list(existing.values())
        if resources is not None:
            from kubernetes.client import V1ResourceRequirements

            target.resources = V1ResourceRequirements(
                requests=resources.get("requests"),
                limits=resources.get("limits"),
            )
        out = apis.apps.replace_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=dep,
        )
        return {"ok": True, "deployment": sanitize(out)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def kubernetes_rollout_undo(namespace: str, deployment_name: str, to_revision: Optional[int] = None) -> Dict[str, Any]:
    """
    Roll back a Deployment by copying `spec.template` from a previous ReplicaSet revision.
    If `to_revision` is omitted, rolls back one revision from the Deployment's current revision.
    """
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        dep = apis.apps.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        sel = dep.spec.selector.match_labels or {}
        label_selector = _match_labels_selector(sel)
        rss = apis.apps.list_namespaced_replica_set(
            namespace=namespace,
            label_selector=label_selector or None,
        ).items
        rev_rs: List[tuple[int, Any]] = []
        for rs in rss:
            rev_raw = (rs.metadata.annotations or {}).get("deployment.kubernetes.io/revision", "0")
            try:
                rev = int(rev_raw)
            except ValueError:
                continue
            rev_rs.append((rev, rs))
        rev_rs.sort(key=lambda x: x[0])
        current = int((dep.metadata.annotations or {}).get("deployment.kubernetes.io/revision", "0"))
        target_rev = (current - 1) if to_revision is None else int(to_revision)
        target_rs = next((rs for rev, rs in rev_rs if rev == target_rev), None)
        if target_rs is None:
            return _err(f"revision {target_rev} not found among ReplicaSets")
        dep.spec.template = target_rs.spec.template
        out = apis.apps.replace_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=dep,
        )
        return {"ok": True, "deployment": sanitize(out), "rolled_back_to_revision": target_rev}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def rollout_undo(namespace: str, deployment_name: str, to_revision: Optional[int] = None) -> Dict[str, Any]:
    """Alias for `kubernetes_rollout_undo`."""
    return kubernetes_rollout_undo(namespace, deployment_name, to_revision=to_revision)


def create_job_from_manifest(namespace: str, manifest_yaml: str) -> Dict[str, Any]:
    """Create Job object(s) from YAML (delegates to `create_from_yaml`)."""
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        created = create_from_yaml(apis.api_client, StringIO(manifest_yaml), namespace=namespace)
        return {"ok": True, "created": [str(x) for x in (created or [])]}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def delete_job(namespace: str, job_name: str) -> Dict[str, Any]:
    assert_namespace_allowed(namespace)
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        opts = k8s_client.V1DeleteOptions(propagation_policy="Background")
        apis.batch.delete_namespaced_job(name=job_name, namespace=namespace, body=opts)
        return {"ok": True, "deleted": f"{namespace}/job/{job_name}"}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def cordon_node(node_name: str, cordon: bool = True) -> Dict[str, Any]:
    """Mark node unschedulable (or schedulable if cordon=False)."""
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        patch = {"spec": {"unschedulable": cordon}}
        node = apis.core.patch_node(
            name=node_name,
            body=patch,
            _content_type="application/strategic-merge-patch+json",
        )
        return {"ok": True, "node": sanitize(node)}
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))


def uncordon_node(node_name: str) -> Dict[str, Any]:
    return cordon_node(node_name, cordon=False)


def drain_node(
    node_name: str,
    cordon_first: bool = True,
) -> Dict[str, Any]:
    """
    Best-effort drain *plan*: optionally cordon the node, then list pods still on it.
    Does not evict or delete pods automatically; use `kubernetes_delete_pod` with policy after approval.
    """
    apis, kerr = get_k8s()
    if not apis:
        return _err(kerr or "k8s unavailable")
    try:
        if cordon_first:
            c = cordon_node(node_name, cordon=True)
            if not c.get("ok"):
                return c
        pods = apis.core.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}").items
        slim = [
            {"namespace": p.metadata.namespace, "name": p.metadata.name, "phase": p.status.phase}
            for p in pods
        ]
        return {
            "ok": True,
            "node": node_name,
            "cordon_applied": cordon_first,
            "pods": slim,
            "detail": "Pods listed for manual eviction or kubernetes_delete_pod; no automatic eviction performed.",
        }
    except Exception as exc:  # pylint: disable=broad-except
        return _err(str(exc))
