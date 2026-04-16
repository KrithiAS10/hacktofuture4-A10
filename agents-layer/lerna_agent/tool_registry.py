"""
OpenAI function-calling schemas + callables for all `tools` exports.

Keep parameter shapes aligned with `tools.*` function signatures.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from tools import (
    check_observability_backends,
    cordon_node,
    create_job_from_manifest,
    delete_job,
    drain_node,
    embed_query_text,
    get_configmap_secret_metadata,
    get_deployment_status,
    get_horizontal_pod_autoscaler,
    get_network_policies,
    get_node_conditions,
    get_persistent_volume_claims,
    get_pod_details,
    get_pod_logs,
    get_rollout_history,
    get_service_endpoints,
    jaeger_search_traces,
    kubernetes_apply_manifest,
    kubernetes_cluster_snapshot,
    kubernetes_delete_pod,
    kubernetes_rollout_restart,
    kubernetes_rollout_undo,
    kubernetes_scale_deployment,
    kubernetes_server_side_apply_dry_run,
    list_jobs_and_cronjobs,
    list_pods_on_node,
    list_recent_events,
    loki_query_range,
    patch_deployment_env_or_resources,
    prometheus_query,
    qdrant_search_similar_incidents,
    rollout_undo,
    run_detection_check,
    set_deployment_image,
    uncordon_node,
)


def _json_safe(value: Any) -> Any:
    """Make tool results JSON-serializable (tuples, numpy scalars, etc.)."""
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        import numpy as np  # type: ignore[import-untyped]

        if isinstance(value, np.generic):
            return value.item()
    except Exception:  # pylint: disable=broad-except
        pass
    return str(value)


def _obj(
    description: str,
    properties: Dict[str, Any],
    required: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "type": "object",
        "description": description,
        "properties": properties,
        "additionalProperties": False,
        "required": required or [],
    }


def openai_tools() -> List[Dict[str, Any]]:
    """Return the `tools=[...]` payload for `chat.completions.create`."""
    specs: List[tuple[str, str, Dict[str, Any]]] = [
        (
            "prometheus_query",
            "Run a PromQL instant query against Prometheus.",
            _obj(
                "Prometheus instant query",
                {
                    "query": {"type": "string", "description": "PromQL expression"},
                    "time": {
                        "type": ["string", "null"],
                        "description": "Optional RFC3339 evaluation time",
                    },
                },
                ["query"],
            ),
        ),
        (
            "loki_query_range",
            "Run a LogQL range query against Loki.",
            _obj(
                "Loki query",
                {
                    "query": {"type": "string", "description": "LogQL"},
                    "limit": {"type": "integer", "default": 200},
                    "start": {"type": ["string", "null"], "description": "Epoch nanoseconds"},
                    "end": {"type": ["string", "null"], "description": "Epoch nanoseconds"},
                    "direction": {"type": "string", "enum": ["forward", "backward"], "default": "backward"},
                },
                ["query"],
            ),
        ),
        (
            "jaeger_search_traces",
            "Search distributed traces via Jaeger.",
            _obj(
                "Jaeger traces",
                {
                    "service": {"type": ["string", "null"]},
                    "limit": {"type": "integer", "default": 20},
                    "lookback_minutes": {"type": "integer", "default": 60},
                },
                [],
            ),
        ),
        (
            "check_observability_backends",
            "Probe Prometheus, Loki, and Jaeger readiness endpoints.",
            _obj("Health check", {}, []),
        ),
        (
            "kubernetes_cluster_snapshot",
            "Summarize cluster nodes, workloads, pods, events, and basic Prom hints.",
            _obj("Snapshot", {}, []),
        ),
        (
            "run_detection_check",
            "Run error-oriented detection over Loki + recent cluster events.",
            _obj(
                "Detection",
                {
                    "log_query": {"type": "string", "default": "{}"},
                    "log_limit": {"type": "integer", "default": 150},
                },
                [],
            ),
        ),
        (
            "qdrant_search_similar_incidents",
            "Embed query text and search Qdrant for similar past incidents.",
            _obj(
                "Qdrant search",
                {
                    "query_text": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "collection": {"type": ["string", "null"]},
                    "with_payload": {"type": "boolean", "default": True},
                    "vector_name": {"type": ["string", "null"]},
                },
                ["query_text"],
            ),
        ),
        (
            "embed_query_text",
            "Embed text to a vector (same model as incident indexing). Debugging / utilities.",
            _obj("Embed", {"text": {"type": "string"}}, ["text"]),
        ),
        (
            "get_pod_details",
            "Read full Pod object (status, containers, node).",
            _obj(
                "Pod details",
                {
                    "namespace": {"type": "string"},
                    "pod_name": {"type": "string"},
                },
                ["namespace", "pod_name"],
            ),
        ),
        (
            "get_pod_logs",
            "Read container logs from kubelet (not Loki).",
            _obj(
                "Pod logs",
                {
                    "namespace": {"type": "string"},
                    "pod_name": {"type": "string"},
                    "container": {"type": ["string", "null"]},
                    "tail_lines": {"type": "integer", "default": 100},
                    "previous": {"type": "boolean", "default": False},
                },
                ["namespace", "pod_name"],
            ),
        ),
        (
            "list_recent_events",
            "List Kubernetes Events (optionally namespaced).",
            _obj(
                "Events",
                {
                    "namespace": {"type": ["string", "null"]},
                    "field_selector": {"type": ["string", "null"]},
                    "limit": {"type": "integer", "default": 100},
                },
                [],
            ),
        ),
        (
            "get_deployment_status",
            "Read Deployment status subresource.",
            _obj(
                "Deployment status",
                {"namespace": {"type": "string"}, "deployment_name": {"type": "string"}},
                ["namespace", "deployment_name"],
            ),
        ),
        (
            "get_rollout_history",
            "List ReplicaSets / revisions for a Deployment.",
            _obj(
                "Rollout history",
                {"namespace": {"type": "string"}, "deployment_name": {"type": "string"}},
                ["namespace", "deployment_name"],
            ),
        ),
        (
            "get_horizontal_pod_autoscaler",
            "Read or list HPAs in a namespace.",
            _obj(
                "HPA",
                {
                    "namespace": {"type": "string"},
                    "name": {"type": ["string", "null"], "description": "If null, list all in namespace"},
                },
                ["namespace"],
            ),
        ),
        (
            "list_jobs_and_cronjobs",
            "List Jobs and CronJobs in a namespace.",
            _obj("Jobs", {"namespace": {"type": "string"}}, ["namespace"]),
        ),
        (
            "get_network_policies",
            "List NetworkPolicies in a namespace.",
            _obj("NetPol", {"namespace": {"type": "string"}}, ["namespace"]),
        ),
        (
            "get_service_endpoints",
            "Read Endpoints for a Service.",
            _obj(
                "Endpoints",
                {"namespace": {"type": "string"}, "service_name": {"type": "string"}},
                ["namespace", "service_name"],
            ),
        ),
        (
            "get_persistent_volume_claims",
            "List PVCs in a namespace.",
            _obj("PVCs", {"namespace": {"type": "string"}}, ["namespace"]),
        ),
        (
            "get_configmap_secret_metadata",
            "List ConfigMap/Secret names and key names (no secret values).",
            _obj("Config/secret metadata", {"namespace": {"type": "string"}}, ["namespace"]),
        ),
        (
            "get_node_conditions",
            "Summarize node Ready / pressure conditions.",
            _obj("Nodes", {}, []),
        ),
        (
            "list_pods_on_node",
            "List pods scheduled on a node.",
            _obj("Pods on node", {"node_name": {"type": "string"}}, ["node_name"]),
        ),
        (
            "kubernetes_rollout_restart",
            "Force Deployment rollout via restartedAt annotation.",
            _obj(
                "Rollout restart",
                {"namespace": {"type": "string"}, "deployment_name": {"type": "string"}},
                ["namespace", "deployment_name"],
            ),
        ),
        (
            "kubernetes_scale_deployment",
            "Scale a Deployment to a replica count.",
            _obj(
                "Scale",
                {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "replicas": {"type": "integer"},
                },
                ["namespace", "deployment_name", "replicas"],
            ),
        ),
        (
            "kubernetes_delete_pod",
            "Delete a Pod (respect approvals; destructive).",
            _obj(
                "Delete pod",
                {
                    "namespace": {"type": "string"},
                    "pod_name": {"type": "string"},
                    "grace_period_seconds": {"type": ["integer", "null"], "default": 30},
                },
                ["namespace", "pod_name"],
            ),
        ),
        (
            "kubernetes_apply_manifest",
            "Apply YAML manifest(s) to the cluster (sandbox recommended).",
            _obj(
                "Apply",
                {
                    "namespace": {"type": "string"},
                    "manifest_yaml": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                },
                ["namespace", "manifest_yaml"],
            ),
        ),
        (
            "kubernetes_server_side_apply_dry_run",
            "Dry-run apply YAML (validation only).",
            _obj(
                "Dry run apply",
                {"namespace": {"type": "string"}, "manifest_yaml": {"type": "string"}},
                ["namespace", "manifest_yaml"],
            ),
        ),
        (
            "set_deployment_image",
            "Set container image on a Deployment.",
            _obj(
                "Set image",
                {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "container_name": {"type": "string"},
                    "image": {"type": "string"},
                },
                ["namespace", "deployment_name", "container_name", "image"],
            ),
        ),
        (
            "patch_deployment_env_or_resources",
            "Patch env vars and/or resources for one container.",
            _obj(
                "Patch deployment",
                {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "container_name": {"type": "string"},
                    "env": {"type": ["object", "null"], "additionalProperties": {"type": "string"}},
                    "resources": {
                        "type": ["object", "null"],
                        "description": '{"requests": {...}, "limits": {...}}',
                    },
                },
                ["namespace", "deployment_name", "container_name"],
            ),
        ),
        (
            "kubernetes_rollout_undo",
            "Roll back Deployment to a prior ReplicaSet revision.",
            _obj(
                "Rollout undo",
                {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "to_revision": {"type": ["integer", "null"]},
                },
                ["namespace", "deployment_name"],
            ),
        ),
        (
            "rollout_undo",
            "Alias for kubernetes_rollout_undo.",
            _obj(
                "Rollout undo alias",
                {
                    "namespace": {"type": "string"},
                    "deployment_name": {"type": "string"},
                    "to_revision": {"type": ["integer", "null"]},
                },
                ["namespace", "deployment_name"],
            ),
        ),
        (
            "create_job_from_manifest",
            "Create Job(s) from YAML.",
            _obj(
                "Create job",
                {"namespace": {"type": "string"}, "manifest_yaml": {"type": "string"}},
                ["namespace", "manifest_yaml"],
            ),
        ),
        (
            "delete_job",
            "Delete a Job.",
            _obj("Delete job", {"namespace": {"type": "string"}, "job_name": {"type": "string"}}, ["namespace", "job_name"]),
        ),
        (
            "cordon_node",
            "Set node scheduling disabled (or enable if cordon=false).",
            _obj(
                "Cordon",
                {"node_name": {"type": "string"}, "cordon": {"type": "boolean", "default": True}},
                ["node_name"],
            ),
        ),
        (
            "uncordon_node",
            "Mark node schedulable again.",
            _obj("Uncordon", {"node_name": {"type": "string"}}, ["node_name"]),
        ),
        (
            "drain_node",
            "Cordon (optional) and list pods on node; does not auto-delete pods.",
            _obj(
                "Drain plan",
                {"node_name": {"type": "string"}, "cordon_first": {"type": "boolean", "default": True}},
                ["node_name"],
            ),
        ),
    ]

    out: List[Dict[str, Any]] = []
    for name, desc, params in specs:
        out.append({"type": "function", "function": {"name": name, "description": desc, "parameters": params}})
    return out


def tool_functions() -> Dict[str, Callable[..., Any]]:
    return {
        "prometheus_query": prometheus_query,
        "loki_query_range": loki_query_range,
        "jaeger_search_traces": jaeger_search_traces,
        "check_observability_backends": check_observability_backends,
        "kubernetes_cluster_snapshot": kubernetes_cluster_snapshot,
        "run_detection_check": run_detection_check,
        "qdrant_search_similar_incidents": qdrant_search_similar_incidents,
        "embed_query_text": embed_query_text,
        "get_pod_details": get_pod_details,
        "get_pod_logs": get_pod_logs,
        "list_recent_events": list_recent_events,
        "get_deployment_status": get_deployment_status,
        "get_rollout_history": get_rollout_history,
        "get_horizontal_pod_autoscaler": get_horizontal_pod_autoscaler,
        "list_jobs_and_cronjobs": list_jobs_and_cronjobs,
        "get_network_policies": get_network_policies,
        "get_service_endpoints": get_service_endpoints,
        "get_persistent_volume_claims": get_persistent_volume_claims,
        "get_configmap_secret_metadata": get_configmap_secret_metadata,
        "get_node_conditions": get_node_conditions,
        "list_pods_on_node": list_pods_on_node,
        "kubernetes_rollout_restart": kubernetes_rollout_restart,
        "kubernetes_scale_deployment": kubernetes_scale_deployment,
        "kubernetes_delete_pod": kubernetes_delete_pod,
        "kubernetes_apply_manifest": kubernetes_apply_manifest,
        "kubernetes_server_side_apply_dry_run": kubernetes_server_side_apply_dry_run,
        "set_deployment_image": set_deployment_image,
        "patch_deployment_env_or_resources": patch_deployment_env_or_resources,
        "kubernetes_rollout_undo": kubernetes_rollout_undo,
        "rollout_undo": rollout_undo,
        "create_job_from_manifest": create_job_from_manifest,
        "delete_job": delete_job,
        "cordon_node": cordon_node,
        "uncordon_node": uncordon_node,
        "drain_node": drain_node,
    }


def dispatch_tool(name: str, arguments_json: str) -> Any:
    """Parse JSON arguments and invoke the tool; returns a JSON-serializable-friendly value."""
    funcs = tool_functions()
    if name not in funcs:
        return {"ok": False, "error": f"unknown tool {name!r}"}
    raw = json.loads(arguments_json or "{}")
    if not isinstance(raw, dict):
        return {"ok": False, "error": "tool arguments must be a JSON object"}
    try:
        out = funcs[name](**raw)
        return _json_safe(out)
    except TypeError as exc:
        return {"ok": False, "error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:  # pylint: disable=broad-except
        return {"ok": False, "error": str(exc)}


def tool_result_to_json_content(result: Any) -> str:
    try:
        return json.dumps(_json_safe(result), default=str)
    except TypeError:
        return json.dumps({"repr": repr(result)})
