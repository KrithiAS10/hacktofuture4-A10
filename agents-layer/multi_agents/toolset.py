from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable, Iterable

from langchain_core.tools import BaseTool, tool
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

TOOL_CALLABLES: dict[str, Callable[..., Any]] = {
    "check_observability_backends": check_observability_backends,
    "cordon_node": cordon_node,
    "create_job_from_manifest": create_job_from_manifest,
    "delete_job": delete_job,
    "drain_node": drain_node,
    "embed_query_text": embed_query_text,
    "get_configmap_secret_metadata": get_configmap_secret_metadata,
    "get_deployment_status": get_deployment_status,
    "get_horizontal_pod_autoscaler": get_horizontal_pod_autoscaler,
    "get_network_policies": get_network_policies,
    "get_node_conditions": get_node_conditions,
    "get_persistent_volume_claims": get_persistent_volume_claims,
    "get_pod_details": get_pod_details,
    "get_pod_logs": get_pod_logs,
    "get_rollout_history": get_rollout_history,
    "get_service_endpoints": get_service_endpoints,
    "jaeger_search_traces": jaeger_search_traces,
    "kubernetes_apply_manifest": kubernetes_apply_manifest,
    "kubernetes_cluster_snapshot": kubernetes_cluster_snapshot,
    "kubernetes_delete_pod": kubernetes_delete_pod,
    "kubernetes_rollout_restart": kubernetes_rollout_restart,
    "kubernetes_rollout_undo": kubernetes_rollout_undo,
    "kubernetes_scale_deployment": kubernetes_scale_deployment,
    "kubernetes_server_side_apply_dry_run": kubernetes_server_side_apply_dry_run,
    "list_jobs_and_cronjobs": list_jobs_and_cronjobs,
    "list_pods_on_node": list_pods_on_node,
    "list_recent_events": list_recent_events,
    "loki_query_range": loki_query_range,
    "patch_deployment_env_or_resources": patch_deployment_env_or_resources,
    "prometheus_query": prometheus_query,
    "qdrant_search_similar_incidents": qdrant_search_similar_incidents,
    "rollout_undo": rollout_undo,
    "run_detection_check": run_detection_check,
    "set_deployment_image": set_deployment_image,
    "uncordon_node": uncordon_node,
}

FILTER_AGENT_TOOLS = [
    "check_observability_backends",
    "run_detection_check",
    "qdrant_search_similar_incidents",
    "kubernetes_cluster_snapshot",
]

MATCHER_AGENT_TOOLS = [
    "qdrant_search_similar_incidents",
    "embed_query_text",
]

DIAGNOSIS_AGENT_TOOLS = [
    "prometheus_query",
    "loki_query_range",
    "jaeger_search_traces",
    "kubernetes_cluster_snapshot",
    "get_pod_logs",
    "get_pod_details",
    "list_recent_events",
    "get_deployment_status",
    "get_rollout_history",
]

PLANNING_AGENT_TOOLS = [
    "prometheus_query",
    "loki_query_range",
    "jaeger_search_traces",
    "kubernetes_cluster_snapshot",
    "get_deployment_status",
    "get_rollout_history",
]

EXECUTOR_AGENT_TOOLS = [
    "kubernetes_scale_deployment",
    "kubernetes_apply_manifest",
    "kubernetes_delete_pod",
    "kubernetes_rollout_restart",
    "kubernetes_rollout_undo",
    "patch_deployment_env_or_resources",
    "cordon_node",
    "uncordon_node",
    "drain_node",
    "rollout_undo",
    "set_deployment_image",
    "kubernetes_server_side_apply_dry_run",
]

VALIDATION_AGENT_TOOLS = [
    "prometheus_query",
    "loki_query_range",
    "kubernetes_cluster_snapshot",
    "list_recent_events",
    "get_deployment_status",
    "get_rollout_history",
    "check_observability_backends",
]


@lru_cache(maxsize=None)
def _get_tool(name: str) -> BaseTool:
    if name not in TOOL_CALLABLES:
        raise KeyError(f"Unknown tool: {name}")
    function = TOOL_CALLABLES[name]
    return tool(function, description=function.__doc__ or "")


def build_toolset(tool_names: Iterable[str]) -> list[BaseTool]:
    return [_get_tool(name) for name in tool_names]
