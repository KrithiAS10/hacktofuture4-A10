from lerna_shared.usage_pricing import usd_cost_for_token_usage


def test_usd_cost_matches_default_gpt41_nano_rates():
    # 1M in + 1M out at default $0.10 / $0.40 per million
    total = usd_cost_for_token_usage("gpt-4.1-nano-2025-04-14", 1_000_000, 1_000_000)
    assert abs(total - 0.50) < 1e-9
