"""Environment-backed provider and tier mapping; model identifiers live in backend/.env."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PROVIDER_NAME = os.getenv("AGENTTRACE_PROVIDER_NAME", "").strip()
DEFAULT_MODEL_TIER = os.getenv("AGENTTRACE_DEFAULT_MODEL_TIER", "mid").strip()
DEFAULT_CAPTURE_TIER = os.getenv("AGENTTRACE_CAPTURE_TIER", "attrs").strip()
MODEL_BY_TIER = {
    "cheap": os.getenv("AGENTTRACE_MODEL_CHEAP", "").strip(),
    "mid": os.getenv("AGENTTRACE_MODEL_MID", "").strip(),
    "premium": os.getenv("AGENTTRACE_MODEL_PREMIUM", "").strip(),
}
API_KEY = os.getenv("LLM_API_KEY") or None
API_BASE = os.getenv("LLM_API_BASE") or None


def model_for_tier(tier: str) -> str:
    if tier not in MODEL_BY_TIER:
        raise ValueError(f"Unknown model tier {tier!r}; choose cheap, mid, or premium")
    model = MODEL_BY_TIER[tier]
    if not model:
        raise RuntimeError(f"Set AGENTTRACE_MODEL_{tier.upper()} in backend/.env")
    if not PROVIDER_NAME:
        raise RuntimeError("Set AGENTTRACE_PROVIDER_NAME in backend/.env")
    return model
