from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from kubernetes import client, config
from app.config import settings


class ClusterPoller:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._ready = False
        self._core: Optional[client.CoreV1Api] = None
        self._apps: Optional[client.AppsV1Api] = None
        self._snapshot: Dict[str, Any] = {
            "available": False,
            "reason": "poller_not_started",
            "namespace_scope": settings.k8s_namespace_scope or None,
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
            nodes, deployments, services, endpoints, pods, events = await asyncio.gather(
                asyncio.to_thread(self._list_nodes),
                asyncio.to_thread(self._list_deployments),
                asyncio.to_thread(self._list_services),
                asyncio.to_thread(self._list_endpoints),
                asyncio.to_thread(self._list_pods),
                asyncio.to_thread(self._list_events),
            )
            self._snapshot = {
                "available": True,
                "last_updated": datetime.now(tz=timezone.utc).isoformat(),
                "namespace_scope": settings.k8s_namespace_scope or None,
                "nodes": self._summarize_nodes(nodes),
                "deployments": self._summarize_deployments(deployments),
                "services": self._summarize_services(services, endpoints),
                "pods": self._summarize_pods(pods),
                "recent_events": self._summarize_events(events),
            }
        except Exception as exc:  # pylint: disable=broad-except
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
        return summary[:50]
