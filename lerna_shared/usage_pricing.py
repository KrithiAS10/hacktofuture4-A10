"""Convert LLM token usage to USD using configurable per-million rates (OpenAI-style pricing)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

# Defaults match OpenAI published gpt-4.1-nano tier (verify on https://openai.com/api/pricing/).
_DEFAULT_IN_PER_M = 0.10
_DEFAULT_OUT_PER_M = 0.40


def _normalize_model_name(model: str) -> str:
    m = (model or "").strip().lower()
    if "/" in m:
        m = m.split("/")[-1]
    return m


def _load_model_price_overrides() -> Dict[str, Dict[str, float]]:
    raw = os.getenv("LERNA_MODEL_PRICE_JSON", "{\"gpt-4.1-nano-2025-04-14\": {\"input\": 0.00000001, \"output\": 0.00000004}}").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    out: Dict[str, Dict[str, float]] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and "input" in v and "output" in v:
                out[str(k).lower()] = {"input": float(v["input"]), "output": float(v["output"])}
    return out


def resolve_price_per_million_usd(model: str) -> Tuple[float, float]:
    """Return (input_usd_per_million, output_usd_per_million) for `model`."""
    default_in = float(os.getenv("LERNA_DEFAULT_INPUT_USD_PER_MILLION", str(_DEFAULT_IN_PER_M)))
    default_out = float(os.getenv("LERNA_DEFAULT_OUTPUT_USD_PER_MILLION", str(_DEFAULT_OUT_PER_M)))
    norm = _normalize_model_name(model)
    overrides = _load_model_price_overrides()
    if norm in overrides:
        o = overrides[norm]
        return o["input"], o["output"]
    for key, o in overrides.items():
        if key and (key in norm or norm.endswith(key)):
            return o["input"], o["output"]
    return default_in, default_out


def usd_cost_for_token_usage(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp_m, out_m = resolve_price_per_million_usd(model)
    return (max(0, prompt_tokens) / 1_000_000.0) * inp_m + (max(0, completion_tokens) / 1_000_000.0) * out_m


def extract_usage_from_openai_completion(completion: Any) -> Tuple[int, int, str]:
    """Return (prompt_tokens, completion_tokens, model_id) from a Chat Completions API response."""
    model = getattr(completion, "model", None) or ""
    if isinstance(model, str):
        pass
    else:
        model = str(model or "")
    usage = getattr(completion, "usage", None)
    if usage is None:
        return 0, 0, model
    if isinstance(usage, dict):
        pt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        ct = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        return pt, ct, model
    pt = int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0)
    ct = int(getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0)
    return pt, ct, model


def extract_usage_from_langchain_ai_message(message: Any) -> Tuple[int, int, str]:
    """Best-effort token extraction from LangChain AIMessage (varies by provider/version)."""
    model = ""
    rm = getattr(message, "response_metadata", None) or {}
    if isinstance(rm, dict):
        model = str(rm.get("model_name") or rm.get("model") or "")

    um = getattr(message, "usage_metadata", None)
    if isinstance(um, dict):
        pt = int(um.get("input_tokens") or um.get("prompt_tokens") or 0)
        ct = int(um.get("output_tokens") or um.get("completion_tokens") or 0)
        md = str(um.get("model") or model or "")
        return pt, ct, md

    if isinstance(rm, dict):
        tu = rm.get("token_usage") or {}
        if isinstance(tu, dict):
            pt = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            ct = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
            return pt, ct, model

    return 0, 0, model

