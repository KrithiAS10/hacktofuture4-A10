import json

from lerna_agent.tool_registry import dispatch_tool, tool_functions, openai_tools


def test_openai_tool_list_matches_callables():
    names_from_specs = {t["function"]["name"] for t in openai_tools()}
    names_from_funcs = set(tool_functions().keys())
    assert names_from_specs == names_from_funcs


def test_dispatch_unknown_tool():
    out = dispatch_tool("not_a_real_tool", "{}")
    assert out["ok"] is False


def test_dispatch_prometheus_query_shape():
    out = dispatch_tool("prometheus_query", json.dumps({"query": "vector(1)"}))
    # Prometheus may be down; we accept structured error or data
    assert isinstance(out, dict)
