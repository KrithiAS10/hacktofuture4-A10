"""
Agent-callable tool functions for Lerna (observability, detection, K8s, Qdrant).

Add `agents-layer` to `PYTHONPATH`, then: `from tools import prometheus_query, ...`
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from .detection import run_detection_check
from .kubernetes_read import (
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
    list_jobs_and_cronjobs,
    list_pods_on_node,
    list_recent_events,
)
from .kubernetes_snapshot import kubernetes_cluster_snapshot
from .kubernetes_write import (
    cordon_node,
    create_job_from_manifest,
    delete_job,
    drain_node,
    kubernetes_apply_manifest,
    kubernetes_delete_pod,
    kubernetes_rollout_restart,
    kubernetes_rollout_undo,
    kubernetes_scale_deployment,
    kubernetes_server_side_apply_dry_run,
    patch_deployment_env_or_resources,
    rollout_undo,
    set_deployment_image,
    uncordon_node,
)
from .observability import (
    check_observability_backends,
    jaeger_search_traces,
    loki_query_range,
    prometheus_query,
)
from .qdrant_memory import embed_query_text, qdrant_search_similar_incidents, qdrant_upsert_incident_memory

__all__ = [
    "check_observability_backends",
    "cordon_node",
    "create_job_from_manifest",
    "delete_job",
    "drain_node",
    "embed_query_text",
    "get_configmap_secret_metadata",
    "get_deployment_status",
    "get_horizontal_pod_autoscaler",
    "get_network_policies",
    "get_node_conditions",
    "get_persistent_volume_claims",
    "get_pod_details",
    "get_pod_logs",
    "get_rollout_history",
    "get_service_endpoints",
    "jaeger_search_traces",
    "kubernetes_apply_manifest",
    "kubernetes_cluster_snapshot",
    "kubernetes_delete_pod",
    "kubernetes_rollout_restart",
    "kubernetes_rollout_undo",
    "kubernetes_scale_deployment",
    "kubernetes_server_side_apply_dry_run",
    "list_jobs_and_cronjobs",
    "list_pods_on_node",
    "list_recent_events",
    "loki_query_range",
    "patch_deployment_env_or_resources",
    "prometheus_query",
    "qdrant_search_similar_incidents",
    "qdrant_upsert_incident_memory",
    "rollout_undo",
    "run_detection_check",
    "set_deployment_image",
    "uncordon_node",
]
