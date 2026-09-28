from fastapi import APIRouter

from app.store.queries import cost_summary

router = APIRouter(prefix="/cost", tags=["cost"])


@router.get("/summary")
def summary(run_id: str = "run_001"):
    return cost_summary(run_id)
