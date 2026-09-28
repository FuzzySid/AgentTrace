from fastapi import APIRouter

from app.store.queries import confusion_matrix, list_runs, list_traces, trace_detail

router = APIRouter(tags=["traces"])


@router.get("/runs")
def runs():
    return list_runs()


@router.get("/traces")
def traces_list(run_id: str = "run_001"):
    return list_traces(run_id)


@router.get("/traces/confusion-matrix")
def traces_confusion_matrix(run_id: str = "run_001"):
    return confusion_matrix(run_id)


@router.get("/traces/{trace_id}")
def trace_by_id(trace_id: str):
    return trace_detail(trace_id)
