"""Qdrant vector search for incident memory: embeds query text, then searches."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ._config import settings

logger = logging.getLogger(__name__)

# Lazy singletons for local embedding models
_fastembed_model: Any = None
_sentence_transformer_model: Any = None


def _ensure_collection_exists(client: Any, coll: str, vector_size: int) -> None:
    from qdrant_client.models import Distance, VectorParams  # type: ignore[import-untyped]

    if client.collection_exists(collection_name=coll):
        return
    try:
        client.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
    except Exception:  # pylint: disable=broad-except
        if not client.collection_exists(collection_name=coll):
            raise


def _embed_fastembed(text: str) -> Tuple[List[float], Dict[str, Any]]:
    try:
        from fastembed import TextEmbedding  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("fastembed not installed; pip install fastembed") from exc

    global _fastembed_model  # pylint: disable=global-statement
    if _fastembed_model is None:
        _fastembed_model = TextEmbedding(model_name=settings.fastembed_model)
    vectors = list(_fastembed_model.embed([text]))
    if not vectors:
        raise RuntimeError("fastembed returned no vectors")
    vec = vectors[0]
    if hasattr(vec, "tolist"):
        out = vec.tolist()
    else:
        out = list(vec)
    meta = {"backend": "fastembed", "model": settings.fastembed_model}
    return out, meta


def _embed_sentence_transformers(text: str) -> Tuple[List[float], Dict[str, Any]]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers not installed; pip install sentence-transformers"
        ) from exc

    global _sentence_transformer_model  # pylint: disable=global-statement
    if _sentence_transformer_model is None:
        _sentence_transformer_model = SentenceTransformer(settings.sentence_transformer_model)
    emb = _sentence_transformer_model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    meta = {"backend": "sentence_transformers", "model": settings.sentence_transformer_model}
    return emb.tolist(), meta


def _embed_openai(text: str) -> Tuple[List[float], Dict[str, Any]]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required when EMBEDDING_BACKEND=openai")
    url = f"{settings.openrouter_base_url}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    body = {"model": settings.openai_embedding_model, "input": text}
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=body, headers=headers)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") or []
    if not data or "embedding" not in data[0]:
        raise RuntimeError("OpenAI embeddings response missing data[0].embedding")
    meta = {
        "backend": "openai",
        "model": settings.openai_embedding_model,
    }
    return data[0]["embedding"], meta


def embed_query_text(text: str) -> Tuple[List[float], Dict[str, Any]]:
    """
    Turn natural language into a dense vector using `EMBEDDING_BACKEND`.

    Backends (see also module docstring on models):

    - **fastembed** (default): ONNX models via `fastembed`, e.g. `BAAI/bge-small-en-v1.5` (384-dim).
    - **openai**: `text-embedding-3-small` (1536-dim) or override with `OPENAI_EMBEDDING_MODEL`.
    - **sentence_transformers**: local PyTorch, e.g. `all-MiniLM-L6-v2` (384-dim).

    The Qdrant collection must be built with the **same** model and dimension as queries.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("query text is empty")

    backend = settings.embedding_backend
    if backend == "fastembed":
        return _embed_fastembed(text)
    if backend == "openai":
        return _embed_openai(text)
    if backend in {"sentence_transformers", "sentence-transformers", "st"}:
        return _embed_sentence_transformers(text)
    raise ValueError(
        f"Unknown EMBEDDING_BACKEND={backend!r}; use fastembed, openai, or sentence_transformers"
    )


def qdrant_search_similar_incidents(
    query_text: str,
    top_k: int = 5,
    collection: Optional[str] = None,
    with_payload: bool = True,
    vector_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Embed `query_text`, then run nearest-neighbor search in Qdrant.

    **Embedding models (pick one stack and use it for indexing + queries):**

    | Backend | Default model | Notes |
    |---------|----------------|--------|
    | `fastembed` | `BAAI/bge-small-en-v1.5` | Local ONNX, small footprint, good default. |
    | `openai` | `text-embedding-3-small` | Cloud API; set `OPENROUTER_API_KEY`. Strong quality. |
    | `sentence_transformers` | `all-MiniLM-L6-v2` | Local PyTorch; heavier install, no API. |

    Env: `QDRANT_URL`, optional `QDRANT_API_KEY`, `QDRANT_COLLECTION`, `EMBEDDING_BACKEND`,
    `FASTEMBED_MODEL`, `OPENAI_EMBEDDING_MODEL`, `OPENROUTER_BASE_URL`, `SENTENCE_TRANSFORMER_MODEL`.
    """
    try:
        from qdrant_client import QdrantClient  # type: ignore[import-untyped]
    except ImportError:
        return {
            "ok": False,
            "error": "qdrant-client not installed; pip install qdrant-client",
        }

    try:
        query_vector, embed_meta = embed_query_text(query_text)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Embedding failed")
        return {"ok": False, "error": str(exc), "embed_meta": None}

    coll = collection or settings.qdrant_collection
    try:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        _ensure_collection_exists(client, coll, len(query_vector))
        kwargs: Dict[str, Any] = {
            "collection_name": coll,
            "query": query_vector,
            "limit": top_k,
            "with_payload": with_payload,
        }
        if vector_name:
            kwargs["using"] = vector_name
        response = client.query_points(**kwargs)
        hits = []
        for p in response.points or []:
            hits.append(
                {
                    "id": p.id,
                    "score": getattr(p, "score", None),
                    "payload": getattr(p, "payload", None),
                }
            )
        return {
            "ok": True,
            "collection": coll,
            "hits": hits,
            "embed_meta": embed_meta,
        }
    except Exception as exc:  # pylint: disable=broad-except
        return {"ok": False, "error": str(exc), "embed_meta": embed_meta}


def qdrant_upsert_incident_memory(
    embedding_source_text: str,
    payload: Dict[str, Any],
    point_id: str,
    collection: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Embed `embedding_source_text` and upsert one point into Qdrant (incident memory).

    `point_id` must be unique per stored report (e.g. UUID string). Payload is stored as-is
    (keep values JSON-friendly: strings, numbers, booleans).
    """
    try:
        from qdrant_client import QdrantClient  # type: ignore[import-untyped]
        from qdrant_client.models import PointStruct  # type: ignore[import-untyped]
    except ImportError:
        return {"ok": False, "error": "qdrant-client not installed; pip install qdrant-client"}

    text = (embedding_source_text or "").strip()
    if not text:
        return {"ok": False, "error": "embedding_source_text is empty"}

    try:
        vector, embed_meta = embed_query_text(text)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Embedding failed for upsert")
        return {"ok": False, "error": str(exc), "embed_meta": None}

    coll = collection or settings.qdrant_collection
    try:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        _ensure_collection_exists(client, coll, len(vector))
        client.upsert(
            collection_name=coll,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return {
            "ok": True,
            "collection": coll,
            "point_id": point_id,
            "embed_meta": embed_meta,
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Qdrant upsert failed")
        return {"ok": False, "error": str(exc), "embed_meta": embed_meta}
