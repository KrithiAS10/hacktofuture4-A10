import os


def _as_bool(raw: str, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))

        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
        self.loki_url = os.getenv("LOKI_URL", "http://localhost:3100").rstrip("/")
        self.jaeger_url = os.getenv("JAEGER_URL", "http://localhost:16686").rstrip("/")

        self.enable_k8s_poller = _as_bool(os.getenv("ENABLE_K8S_POLLER", "True"), True)
        self.k8s_namespace_scope = os.getenv("K8S_NAMESPACE_SCOPE", "").strip()
        self.poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))


settings = Settings()
