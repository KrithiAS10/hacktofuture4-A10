"""Lazy Kubernetes API client wiring (kubeconfig / in-cluster)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from kubernetes import client, config

from ._config import settings


@dataclass
class K8sApis:
    core: client.CoreV1Api
    apps: client.AppsV1Api
    batch: client.BatchV1Api
    autoscaling: client.AutoscalingV2Api
    networking: client.NetworkingV1Api
    policy: client.PolicyV1Api
    api_client: client.ApiClient


_apis: Optional[K8sApis] = None
_init_error: Optional[str] = None


def _load_config() -> None:
    global _apis, _init_error  # pylint: disable=global-statement
    if _apis is not None or _init_error is not None:
        return
    try:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        api_client = client.ApiClient()
        _apis = K8sApis(
            core=client.CoreV1Api(api_client),
            apps=client.AppsV1Api(api_client),
            batch=client.BatchV1Api(api_client),
            autoscaling=client.AutoscalingV2Api(api_client),
            networking=client.NetworkingV1Api(api_client),
            policy=client.PolicyV1Api(api_client),
            api_client=api_client,
        )
    except Exception as exc:  # pylint: disable=broad-except
        _init_error = str(exc)


def get_k8s() -> Tuple[Optional[K8sApis], Optional[str]]:
    """Return (apis, error)."""
    _load_config()
    return _apis, _init_error


def assert_namespace_allowed(namespace: str) -> None:
    scope = settings.k8s_namespace_scope
    if scope and namespace != scope:
        raise ValueError(f"namespace {namespace!r} is outside allowed scope {scope!r}")


def sanitize(obj: Any) -> Any:
    apis, _ = get_k8s()
    if not apis:
        return None
    return apis.api_client.sanitize_for_serialization(obj)
