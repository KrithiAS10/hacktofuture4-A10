from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from kubernetes import client, config
from app.config import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.observability import ObservabilityService


class ClusterPoller:
    def __init__(self, obs_service: "ObservabilityService") -> None:
        self._obs_service = obs_service
        self._task: Optional[asyncio.Task] = None
        self._ready = False
        self._core: Optional[client.CoreV1Api] = None
        self._apps: Optional[client.AppsV1Api] = None
        self._snapshot: Dict[str, Any] = {
            "available": False,
            "reason": "poller_not_started",
            "namespace_scope": settings.k8s_namespace_scope or None,
            "metrics": {
                "cpu_percentage": None,
                "memory_percentage": None,
                "cpu_available": False,
                "memory_available": False,
                "cpu_reason": "poller_not_started",
                "memory_reason": "poller_not_started",
            },
        }

    async def start(self) -> None:
        if self._task or not settings.enable_k8s_poller:
            return
        self._initialize_client()
        self._task = asyncio.create_task(self._run(), name="cluster-poller")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def get_snapshot(self) -> Dict[str, Any]:
        return self._snapshot

    def _initialize_client(self) -> None:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException as exc:
                self._snapshot = {
                    "available": False,
                    "reason": f"k8s_config_unavailable: {exc}",
                    "namespace_scope": settings.k8s_namespace_scope or None,
                }
                return
        self._core = client.CoreV1Api()
        self._apps = client.AppsV1Api()
        self._ready = True

    async def _run(self) -> None:
        while True:
            await self._poll_once()
            await asyncio.sleep(settings.poll_interval_seconds)

    async def _poll_once(self) -> None:
        if not self._ready or not self._core or not self._apps:
            return

        try:
            nodes, deployments, services, endpoints, pods, events = await asyncio.wait_for(
                asyncio.gather(
                    asyncio.to_thread(self._list_nodes),
                    asyncio.to_thread(self._list_deployments),
                    asyncio.to_thread(self._list_services),
                    asyncio.to_thread(self._list_endpoints),
                    asyncio.to_thread(self._list_pods),
                    asyncio.to_thread(self._list_events),
                ),
                timeout=settings.poll_timeout_seconds,
            )

            # Fetch metrics from Prometheus (non-blocking, best-effort)
            metrics = await self._fetch_metrics()

            self._snapshot = {
                "available": True,
                "last_updated": datetime.now(tz=timezone.utc).isoformat(),
                "namespace_scope": settings.k8s_namespace_scope or None,
                "nodes": self._summarize_nodes(nodes),
                "deployments": self._summarize_deployments(deployments),
                "services": self._summarize_services(services, endpoints),
                "pods": self._summarize_pods(pods),
                "recent_events": self._summarize_events(events),
                "metrics": metrics,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Cluster poller failed to refresh snapshot")
            self._snapshot = {
                "available": False,
                "last_updated": datetime.now(tz=timezone.utc).isoformat(),
                "reason": str(exc),
                "namespace_scope": settings.k8s_namespace_scope or None,
            }

    def _list_nodes(self):
        return self._core.list_node().items

    def _list_deployments(self):
        if settings.k8s_namespace_scope:
            return self._apps.list_namespaced_deployment(namespace=settings.k8s_namespace_scope).items
        return self._apps.list_deployment_for_all_namespaces().items

    def _list_services(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_service(namespace=settings.k8s_namespace_scope).items
        return self._core.list_service_for_all_namespaces().items

    def _list_endpoints(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_endpoints(namespace=settings.k8s_namespace_scope).items
        return self._core.list_endpoints_for_all_namespaces().items

    def _list_pods(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_pod(namespace=settings.k8s_namespace_scope).items
        return self._core.list_pod_for_all_namespaces().items

    def _list_events(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_event(namespace=settings.k8s_namespace_scope, limit=100).items
        return self._core.list_event_for_all_namespaces(limit=100).items

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
                    "last_timestamp": (
                        event.last_timestamp.isoformat() if event.last_timestamp else None
                    ),
                }
            )
        summary.sort(key=lambda item: item["last_timestamp"] or "", reverse=True)
        return summary[:50]

    async def _fetch_metrics(self) -> Dict[str, Any]:
        """Fetch basic cluster-level metrics from Prometheus."""
        metrics: Dict[str, Any] = {
            "cpu_percentage": None,
            "memory_percentage": None,
            "cpu_available": False,
            "memory_available": False,
            "cpu_query": None,
            "memory_query": None,
            "cpu_reason": "metric_not_found",
            "memory_reason": "metric_not_found",
        }
        try:
            cpu_queries = [
                'avg(k8s_node_cpu_utilization_ratio) * 100',
                'avg(k8s_node_cpu_utilization) * 100',
            ]
            mem_queries = [
                'sum(k8s_node_memory_usage_bytes) / (sum(k8s_node_memory_usage_bytes) + sum(k8s_node_memory_available_bytes)) * 100',
                'sum(k8s_node_memory_usage) / (sum(k8s_node_memory_usage) + sum(k8s_node_memory_available)) * 100',
            ]

            async def resolve_metric(queries: List[str], label: str) -> Dict[str, Any]:
                last_reason = "metric_not_found"
                for query in queries:
                    try:
                        response = await self._obs_service.query_metrics(query)
                    except Exception as exc:  # pylint: disable=broad-except
                        last_reason = f"query_failed: {exc}"
                        logger.warning("Prometheus %s query failed", label, extra={"query": query}, exc_info=True)
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

                return {
                    "percentage": None,
                    "available": False,
                    "query": queries[0] if queries else None,
                    "reason": last_reason,
                }

            cpu_metric, memory_metric = await asyncio.gather(
                resolve_metric(cpu_queries, "cpu"),
                resolve_metric(mem_queries, "memory"),
            )

            metrics["cpu_percentage"] = cpu_metric["percentage"]
            metrics["cpu_available"] = cpu_metric["available"]
            metrics["cpu_query"] = cpu_metric["query"]
            metrics["cpu_reason"] = cpu_metric["reason"]

            metrics["memory_percentage"] = memory_metric["percentage"]
            metrics["memory_available"] = memory_metric["available"]
            metrics["memory_query"] = memory_metric["query"]
            metrics["memory_reason"] = memory_metric["reason"]
        except Exception:  # pylint: disable=broad-except
            logger.warning("Failed to fetch metrics from Prometheus, skipping", exc_info=True)
            metrics["cpu_reason"] = "metrics_fetch_failed"
            metrics["memory_reason"] = "metrics_fetch_failed"

        return metrics
