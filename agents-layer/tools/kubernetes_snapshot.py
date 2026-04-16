"""Aggregated cluster snapshot (nodes, workloads, events, basic Prom hints)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ._config import settings
from ._k8s import get_k8s
from .observability import prometheus_query


def _summarize_nodes(nodes) -> Dict[str, Any]:
    not_ready: List[str] = []
    for node in nodes:
        ready = False
        for cond in node.status.conditions or []:
            if cond.type == "Ready" and cond.status == "True":
                ready = True
                break
        if not ready:
            not_ready.append(node.metadata.name)
    return {
        "total": len(nodes),
        "ready": len(nodes) - len(not_ready),
        "not_ready": not_ready[:20],
    }


def _summarize_deployments(deployments) -> Dict[str, Any]:
    degraded: List[Dict[str, Any]] = []
    for dep in deployments:
        desired = dep.spec.replicas or 0
        ready = dep.status.ready_replicas or 0
        if ready < desired:
            degraded.append(
                {
                    "namespace": dep.metadata.namespace,
                    "name": dep.metadata.name,
                    "ready": ready,
                    "desired": desired,
                }
            )
    return {
        "total": len(deployments),
        "degraded_count": len(degraded),
        "degraded": degraded[:30],
    }


def _summarize_services(services, endpoints) -> Dict[str, Any]:
    endpoint_map: Dict[str, int] = {}
    for ep in endpoints:
        key = f"{ep.metadata.namespace}/{ep.metadata.name}"
        ready = 0
        for subset in ep.subsets or []:
            ready += len(subset.addresses or [])
        endpoint_map[key] = ready

    without_ready: List[Dict[str, Any]] = []
    for svc in services:
        if svc.spec.type == "ExternalName":
            continue
        key = f"{svc.metadata.namespace}/{svc.metadata.name}"
        if endpoint_map.get(key, 0) == 0:
            without_ready.append(
                {
                    "namespace": svc.metadata.namespace,
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                }
            )
    return {
        "total": len(services),
        "without_ready_endpoints_count": len(without_ready),
        "without_ready_endpoints": without_ready[:30],
    }


def _summarize_pods(pods) -> Dict[str, Any]:
    restarting: List[Dict[str, Any]] = []
    non_running: List[Dict[str, Any]] = []
    for pod in pods:
        phase = pod.status.phase
        if phase != "Running":
            non_running.append(
                {
                    "namespace": pod.metadata.namespace,
                    "name": pod.metadata.name,
                    "phase": phase,
                }
            )

        restart_count = 0
        reason = None
        for cs in pod.status.container_statuses or []:
            restart_count += cs.restart_count or 0
            if cs.state and cs.state.waiting and cs.state.waiting.reason:
                reason = cs.state.waiting.reason
        if restart_count > 0:
            restarting.append(
                {
                    "namespace": pod.metadata.namespace,
                    "name": pod.metadata.name,
                    "restarts": restart_count,
                    "reason": reason,
                }
            )

    restarting.sort(key=lambda x: x["restarts"], reverse=True)
    return {
        "total": len(pods),
        "non_running_count": len(non_running),
        "restarting_count": len(restarting),
        "non_running": non_running[:30],
        "top_restarting": restarting[:30],
    }


def _summarize_events(events) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for event in events:
        if not event.type:
            continue
        summary.append(
            {
                "type": event.type,
                "reason": event.reason,
                "namespace": event.metadata.namespace,
                "object": event.involved_object.name if event.involved_object else None,
                "message": event.message,
                "count": event.count,
                "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
            }
        )
    summary.sort(key=lambda item: item["last_timestamp"] or "", reverse=True)
    return summary[:50]


def _fetch_cluster_metrics_hints() -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "cpu_percentage": None,
        "memory_percentage": None,
        "cpu_available": False,
        "memory_available": False,
        "cpu_query": None,
        "memory_query": None,
        "cpu_reason": None,
        "memory_reason": None,
    }
    cpu_queries = [
        "avg(k8s_node_cpu_utilization_ratio) * 100",
        "avg(k8s_node_cpu_utilization) * 100",
    ]
    mem_queries = [
        "sum(k8s_node_memory_usage_bytes) / (sum(k8s_node_memory_usage_bytes) + sum(k8s_node_memory_available_bytes)) * 100",
        "sum(k8s_node_memory_usage) / (sum(k8s_node_memory_usage) + sum(k8s_node_memory_available)) * 100",
    ]

    def resolve(queries: List[str], label: str) -> Dict[str, Any]:
        last_reason = "metric_not_found"
        for query in queries:
            try:
                response = prometheus_query(query)
            except Exception as exc:  # pylint: disable=broad-except
                last_reason = f"query_failed: {exc}"
                continue
            results = response.get("data", {}).get("result", [])
            if not results:
                last_reason = "query_returned_no_series"
                continue
            raw_value = results[0].get("value", [None, None])[1]
            if raw_value is None:
                last_reason = "query_returned_no_value"
                continue
            try:
                return {
                    "percentage": round(float(raw_value), 2),
                    "available": True,
                    "query": query,
                    "reason": None,
                }
            except (TypeError, ValueError):
                last_reason = f"query_returned_non_numeric_value: {raw_value}"
        return {"percentage": None, "available": False, "query": queries[0] if queries else None, "reason": last_reason}

    cpu = resolve(cpu_queries, "cpu")
    mem = resolve(mem_queries, "memory")
    metrics["cpu_percentage"] = cpu["percentage"]
    metrics["cpu_available"] = cpu["available"]
    metrics["cpu_query"] = cpu["query"]
    metrics["cpu_reason"] = cpu["reason"]
    metrics["memory_percentage"] = mem["percentage"]
    metrics["memory_available"] = mem["available"]
    metrics["memory_query"] = mem["query"]
    metrics["memory_reason"] = mem["reason"]
    return metrics


def kubernetes_cluster_snapshot() -> Dict[str, Any]:
    """
    Return a dashboard-style snapshot: nodes, deployments, services, pods, recent events, Prom hints.
    Honors `K8S_NAMESPACE_SCOPE` the same way the backend poller does (lists are scoped when set).
    """
    apis, err = get_k8s()
    if not apis:
        return {
            "ok": False,
            "available": False,
            "reason": err or "k8s_unavailable",
            "namespace_scope": settings.k8s_namespace_scope or None,
        }

    ns = settings.k8s_namespace_scope or None
    try:
        nodes = apis.core.list_node().items
        if ns:
            deployments = apis.apps.list_namespaced_deployment(namespace=ns).items
            services = apis.core.list_namespaced_service(namespace=ns).items
            endpoints = apis.core.list_namespaced_endpoints(namespace=ns).items
            pods = apis.core.list_namespaced_pod(namespace=ns).items
            events = apis.core.list_namespaced_event(namespace=ns, limit=100).items
        else:
            deployments = apis.apps.list_deployment_for_all_namespaces().items
            services = apis.core.list_service_for_all_namespaces().items
            endpoints = apis.core.list_endpoints_for_all_namespaces().items
            pods = apis.core.list_pod_for_all_namespaces().items
            events = apis.core.list_event_for_all_namespaces(limit=100).items

        metrics = _fetch_cluster_metrics_hints()
        return {
            "ok": True,
            "available": True,
            "last_updated": datetime.now(tz=timezone.utc).isoformat(),
            "namespace_scope": ns,
            "nodes": _summarize_nodes(nodes),
            "deployments": _summarize_deployments(deployments),
            "services": _summarize_services(services, endpoints),
            "pods": _summarize_pods(pods),
            "recent_events": _summarize_events(events),
            "metrics": metrics,
        }
    except Exception as exc:  # pylint: disable=broad-except
        return {
            "ok": False,
            "available": False,
            "reason": str(exc),
            "namespace_scope": ns,
        }
