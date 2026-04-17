import os
from pathlib import Path
from typing import Optional


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
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.agents_service_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001").rstrip("/")

        self.enable_k8s_poller = _as_bool(os.getenv("ENABLE_K8S_POLLER", "True"), True)
        self.k8s_namespace_scope = os.getenv("K8S_NAMESPACE_SCOPE", "").strip()
        self.poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
        self.poll_timeout_seconds = int(os.getenv("POLL_TIMEOUT_SECONDS", "20"))
        # Orchestrator calls the LLM; default backend→agents HTTP client is too short otherwise.
        self.agents_orchestrator_timeout_seconds = float(os.getenv("AGENTS_ORCHESTRATOR_TIMEOUT_SECONDS", "120"))
        self.health_timeout_seconds = int(os.getenv("OBS_HEALTH_TIMEOUT_SECONDS", "6"))

        # SQLite path for operator settings (daily agent budget, etc.)
        raw_db = os.getenv("LERNA_PLATFORM_SETTINGS_DB", "").strip()
        if raw_db:
            self.platform_settings_db_path = Path(raw_db)
        else:
            self.platform_settings_db_path = (
                Path(__file__).resolve().parent.parent / "data" / "platform_settings.db"
            )

        # When no row exists in DB yet, this cap applies (set empty or "none" for unlimited)
        raw_cap = os.getenv("LERNA_DEFAULT_MAX_DAILY_AGENT_COST_USD", "100").strip().lower()
        if raw_cap in {"", "none", "unlimited", "off"}:
            self.default_max_daily_agent_cost_usd: Optional[float] = None
        else:
            try:
                self.default_max_daily_agent_cost_usd = float(raw_cap)
            except ValueError:
                self.default_max_daily_agent_cost_usd = 100.0


settings = Settings()
