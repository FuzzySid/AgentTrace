from fastapi import APIRouter

from app.store.queries import regression_comparison

router = APIRouter(prefix="/regressions", tags=["regressions"])


@router.get("")
def compare(baseline: str = "run_001", candidate: str = "run_002"):
    return regression_comparison(baseline, candidate)
