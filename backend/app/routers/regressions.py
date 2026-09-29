from fastapi import APIRouter

from app.store.queries import regression_comparison

router = APIRouter(prefix="/regressions", tags=["regressions"])


@router.get("")
def compare(comparison: str = "prompt", baseline: str | None = None, candidate: str | None = None):
    return regression_comparison(comparison, baseline, candidate)
