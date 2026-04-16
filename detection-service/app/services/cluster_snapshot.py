from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from kubernetes import client, config

from app.config import settings


class ClusterSnapshotService:
    def __init__(self) -> None:
        self._core: client.CoreV1Api | None = None
        self._apps: client.AppsV1Api | None = None
        self._ready = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except config.ConfigException:
                return
        self._core = client.CoreV1Api()
        self._apps = client.AppsV1Api()
        self._ready = True

    async def get_snapshot(self) -> Dict[str, Any]:
        if not self._ready or not self._core or not self._apps:
            return {
                "available": False,
                "reason": "k8s_config_unavailable",
                "namespace_scope": settings.k8s_namespace_scope or None,
            }

        try:
            nodes, deployments, services, endpoints, pods, events = await asyncio.wait_for(
                asyncio.gather(
                    asyncio.to_thread(self._core.list_node),
                    asyncio.to_thread(self._list_deployments),
                    asyncio.to_thread(self._list_services),
                    asyncio.to_thread(self._list_endpoints),
                    asyncio.to_thread(self._list_pods),
                    asyncio.to_thread(self._list_events),
                ),
                timeout=settings.poll_timeout_seconds,
            )
            return {
                "available": True,
                "last_updated": datetime.now(tz=timezone.utc).isoformat(),
                "namespace_scope": settings.k8s_namespace_scope or None,
                "nodes": self._summarize_nodes(nodes.items),
                "deployments": self._summarize_deployments(deployments.items),
                "services": self._summarize_services(services.items, endpoints.items),
                "pods": self._summarize_pods(pods.items),
                "recent_events": self._summarize_events(events.items),
            }
        except Exception as exc:  # pylint: disable=broad-except
            return {
                "available": False,
                "reason": str(exc),
                "namespace_scope": settings.k8s_namespace_scope or None,
            }

    def _list_deployments(self):
        if settings.k8s_namespace_scope:
            return self._apps.list_namespaced_deployment(namespace=settings.k8s_namespace_scope)
        return self._apps.list_deployment_for_all_namespaces()

    def _list_services(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_service(namespace=settings.k8s_namespace_scope)
        return self._core.list_service_for_all_namespaces()

    def _list_endpoints(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_endpoints(namespace=settings.k8s_namespace_scope)
        return self._core.list_endpoints_for_all_namespaces()

    def _list_pods(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_pod(namespace=settings.k8s_namespace_scope)
        return self._core.list_pod_for_all_namespaces()

    def _list_events(self):
        if settings.k8s_namespace_scope:
            return self._core.list_namespaced_event(namespace=settings.k8s_namespace_scope, limit=100)
        return self._core.list_event_for_all_namespaces(limit=100)

    @staticmethod
    def _summarize_nodes(nodes) -> Dict[str, Any]:
        not_ready: List[str] = []
        for node in nodes:
            ready = any(cond.type == "Ready" and cond.status == "True" for cond in node.status.conditions or [])
            if not ready:
                not_ready.append(node.metadata.name)
        return {"total": len(nodes), "ready": len(nodes) - len(not_ready), "not_ready": not_ready[:20]}

    @staticmethod
    def _summarize_deployments(deployments) -> Dict[str, Any]:
        degraded: List[Dict[str, Any]] = []
        for dep in deployments:
            desired = dep.spec.replicas or 0
            ready = dep.status.ready_replicas or 0
            if ready < desired:
                degraded.append({"namespace": dep.metadata.namespace, "name": dep.metadata.name, "ready": ready, "desired": desired})
        return {"total": len(deployments), "degraded_count": len(degraded), "degraded": degraded[:30]}

    @staticmethod
    def _summarize_services(services, endpoints) -> Dict[str, Any]:
        endpoint_map: Dict[str, int] = {}
        for ep in endpoints:
            key = f"{ep.metadata.namespace}/{ep.metadata.name}"
            ready = sum(len(subset.addresses or []) for subset in ep.subsets or [])
            endpoint_map[key] = ready
        without_ready: List[Dict[str, Any]] = []
        for svc in services:
            if svc.spec.type == "ExternalName":
                continue
            key = f"{svc.metadata.namespace}/{svc.metadata.name}"
            if endpoint_map.get(key, 0) == 0:
                without_ready.append({"namespace": svc.metadata.namespace, "name": svc.metadata.name, "type": svc.spec.type})
        return {"total": len(services), "without_ready_endpoints_count": len(without_ready), "without_ready_endpoints": without_ready[:30]}

    @staticmethod
    def _summarize_pods(pods) -> Dict[str, Any]:
        restarting: List[Dict[str, Any]] = []
        non_running: List[Dict[str, Any]] = []
        for pod in pods:
            phase = pod.status.phase
            if phase != "Running":
                non_running.append({"namespace": pod.metadata.namespace, "name": pod.metadata.name, "phase": phase})
            restart_count = 0
            reason = None
            for cs in pod.status.container_statuses or []:
                restart_count += cs.restart_count or 0
                if cs.state and cs.state.waiting and cs.state.waiting.reason:
                    reason = cs.state.waiting.reason
            if restart_count > 0:
                restarting.append({"namespace": pod.metadata.namespace, "name": pod.metadata.name, "restarts": restart_count, "reason": reason})
        restarting.sort(key=lambda item: item["restarts"], reverse=True)
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
                    "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None,
                }
            )
        summary.sort(key=lambda item: item["last_timestamp"] or "", reverse=True)
        return summary[:50]
