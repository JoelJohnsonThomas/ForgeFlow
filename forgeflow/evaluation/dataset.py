"""EvalDataset — synthetic evaluation examples for the Sales Operations workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalExample:
    id: str
    company_name: str
    expected_qualified: bool
    expected_score_min: float
    expected_score_max: float
    description: str


# 20 synthetic eval examples spanning the qualification spectrum
EVAL_DATASET: list[EvalExample] = [
    # High-score leads (should qualify)
    EvalExample("e01", "Stripe", True, 8.5, 10.0, "Series H fintech, 8000 employees"),
    EvalExample("e02", "Snowflake", True, 8.0, 10.0, "Public cloud data company, 7000 emp"),
    EvalExample("e03", "Vercel", True, 7.5, 9.5, "Developer platform, Series D, 500 emp"),
    EvalExample("e04", "Retool", True, 7.0, 9.0, "Internal tools SaaS, Series C, 400 emp"),
    EvalExample("e05", "Linear", True, 6.5, 8.5, "PM tool SaaS, profitable, 150 emp"),
    EvalExample("e06", "Dbt Labs", True, 7.0, 9.0, "Data transformation SaaS, Series D"),
    EvalExample("e07", "Airbyte", True, 6.5, 8.5, "Open-source data integration, Series B"),
    EvalExample("e08", "Loom", True, 6.0, 8.0, "Video messaging, acquired by Atlassian"),
    EvalExample("e09", "Notion", True, 7.5, 9.5, "Workspace SaaS, unicorn, 500 emp"),
    EvalExample("e10", "Airtable", True, 7.0, 9.0, "Low-code database platform, Series F"),

    # Marginal leads (borderline qualification)
    EvalExample("e11", "StartupXYZ", False, 3.0, 6.0, "Pre-seed startup, 5 employees"),
    EvalExample("e12", "LocalCafe", False, 0.0, 3.0, "Coffee shop, 3 employees"),
    EvalExample("e13", "MidMarketCo", True, 4.0, 7.0, "Mid-size retail, 200 employees"),
    EvalExample("e14", "GrowthStage", True, 5.0, 7.5, "Series A startup, 80 employees"),

    # Clear disqualifications
    EvalExample("e15", "FamilyBakery", False, 0.0, 2.0, "Local bakery, 10 employees, no tech"),
    EvalExample("e16", "Stealth Mode", False, 1.0, 4.0, "No public info available"),
    EvalExample("e17", "LegacyBank", False, 2.0, 5.0, "Traditional bank, no API/cloud"),
    EvalExample("e18", "ShutteredCo", False, 0.0, 2.0, "Company closed in 2024"),

    # Edge cases
    EvalExample("e19", "OpenAI", True, 9.0, 10.0, "AI lab, massive scale, clear fit"),
    EvalExample("e20", "Anthropic", True, 9.0, 10.0, "AI safety company, Series E"),
]


def get_dataset() -> list[EvalExample]:
    return EVAL_DATASET


def get_sample(n: int = 5) -> list[EvalExample]:
    """Return a random sample for quick evaluation runs."""
    import random
    return random.sample(EVAL_DATASET, min(n, len(EVAL_DATASET)))
