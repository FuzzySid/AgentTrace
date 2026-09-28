"""Tier pricing in EUR per million tokens; verify current rates before real billing."""

TIER_PRICING = {
    "cheap": {"input_per_million": 0.15, "output_per_million": 0.60},
    "mid": {"input_per_million": 2.50, "output_per_million": 10.00},
    "premium": {"input_per_million": 15.00, "output_per_million": 60.00},
}
