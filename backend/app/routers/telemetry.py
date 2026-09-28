from fastapi import APIRouter

from app.store.queries import telemetry_tax

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/tax")
def tax(run_id: str = "run_001"):
    return telemetry_tax(run_id)
