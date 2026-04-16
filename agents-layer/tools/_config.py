"""Environment-backed settings for agent tools (same env names as the FastAPI backend where applicable)."""

from __future__ import annotations

import os


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class ToolSettings:
    def __init__(self) -> None:
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
        self.loki_url = os.getenv("LOKI_URL", "http://localhost:3100").rstrip("/")
        self.jaeger_url = os.getenv("JAEGER_URL", "http://localhost:16686").rstrip("/")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "incidents").strip()
        self.k8s_namespace_scope = os.getenv("K8S_NAMESPACE_SCOPE", "").strip()

        # Incident memory embeddings (`qdrant_search_similar_incidents`)
        # Backends: `fastembed` (default, local ONNX), `openai`, `sentence_transformers`
        self.embedding_backend = os.getenv("EMBEDDING_BACKEND", "fastembed").strip().lower()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or None
        self.openai_embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.fastembed_model = os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5").strip()
        self.sentence_transformer_model = os.getenv(
            "SENTENCE_TRANSFORMER_MODEL",
            "all-MiniLM-L6-v2",
        ).strip()


settings = ToolSettings()
