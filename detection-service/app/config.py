from __future__ import annotations

import os


class Settings:
    def __init__(self) -> None:
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
        self.loki_url = os.getenv("LOKI_URL", "http://localhost:3100").rstrip("/")
        self.jaeger_url = os.getenv("JAEGER_URL", "http://localhost:16686").rstrip("/")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.agents_service_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8010").rstrip("/")
        self.k8s_namespace_scope = os.getenv("K8S_NAMESPACE_SCOPE", "").strip()
        self.poll_interval_seconds = int(os.getenv("DETECTION_POLL_INTERVAL_SECONDS", "15"))
        self.poll_timeout_seconds = int(os.getenv("DETECTION_POLL_TIMEOUT_SECONDS", "20"))
        # Empty `{}` is rejected by Loki with 400 in typical configs; use a broad valid selector.
        self.log_query = os.getenv("DETECTION_LOG_QUERY", '{namespace=~".+"}')
        self.log_limit = int(os.getenv("DETECTION_LOG_LIMIT", "150"))
        self.dedupe_ttl_seconds = int(os.getenv("DETECTION_DEDUPE_TTL_SECONDS", "300"))
        self.retry_delay_seconds = int(os.getenv("DETECTION_RETRY_DELAY_SECONDS", "30"))


settings = Settings()
