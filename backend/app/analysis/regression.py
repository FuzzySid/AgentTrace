"""Paired run comparisons by fixture task id."""

from __future__ import annotations

from typing import Any

from app.analysis.cost_model import trace_costs, _p95


def _comparison_side(run_id: str, rows: list[dict[str, Any]], trace_statuses: dict[str, dict[str, str]]) -> dict[str, Any]:
    costs = trace_costs(rows)
    tasks = {}
    for trace_id, cost in costs.items():
        metadata = trace_statuses.get(trace_id, {})
        task_id = str(metadata.get("task_id", cost["task_id"]))
        if task_id not in tasks or metadata.get("started_at", 0) > tasks[task_id].get("started_at", 0):
            tasks[task_id] = {
                **cost,
                "status": metadata.get("status", "passed"),
                "failure_class": metadata.get("failure_class"),
                "prompt_version": metadata.get("prompt_version", "unknown"),
                "model_tier": metadata.get("model_tier", cost["model_tier"]),
                "started_at": metadata.get("started_at", 0),
            }
    return {"run_id": run_id, "tasks": tasks}


def compare_runs(
    baseline_id: str,
    baseline_rows: list[dict[str, Any]],
    baseline_statuses: dict[str, dict[str, str]],
    candidate_id: str,
    candidate_rows: list[dict[str, Any]],
    candidate_statuses: dict[str, dict[str, str]],
) -> dict[str, Any]:
    baseline = _comparison_side(baseline_id, baseline_rows, baseline_statuses)
    candidate = _comparison_side(candidate_id, candidate_rows, candidate_statuses)
    paired = sorted(set(baseline["tasks"]) & set(candidate["tasks"]))
    base_tasks = [baseline["tasks"][task_id] for task_id in paired]
    candidate_tasks = [candidate["tasks"][task_id] for task_id in paired]

    def metrics(tasks: list[dict[str, Any]]) -> dict[str, float]:
        total = len(tasks)
        failed = sum(task["status"] == "failed" for task in tasks)
        successful_count = total - failed
        return {
            "failure_rate": failed / total if total else 0.0,
            "cost_per_success_eur": sum(task["cost_eur"] for task in tasks) / successful_count if successful_count else 0.0,
            "p95_latency_ms": _p95([task["duration_ms"] for task in tasks]),
            "task_count": total,
            "passed": total - failed,
            "failed": failed,
        }

    baseline_metrics = metrics(base_tasks)
    candidate_metrics = metrics(candidate_tasks)
    newly_failing = [
        {"task_id": task_id, "failure_class": candidate["tasks"][task_id]["failure_class"]}
        for task_id in paired
        if baseline["tasks"][task_id]["status"] == "passed" and candidate["tasks"][task_id]["status"] == "failed"
    ]
    newly_fixed = [
        {"task_id": task_id}
        for task_id in paired
        if baseline["tasks"][task_id]["status"] == "failed" and candidate["tasks"][task_id]["status"] == "passed"
    ]
    return {
        "baseline": {
            "run_id": baseline_id,
            "prompt_version": base_tasks[0]["prompt_version"] if base_tasks else "unknown",
            "model_tier": base_tasks[0]["model_tier"] if base_tasks else "unknown",
            "task_count": baseline_metrics["task_count"],
            "passed": baseline_metrics["passed"],
            "failed": baseline_metrics["failed"],
        },
        "candidate": {
            "run_id": candidate_id,
            "prompt_version": candidate_tasks[0]["prompt_version"] if candidate_tasks else "unknown",
            "model_tier": candidate_tasks[0]["model_tier"] if candidate_tasks else "unknown",
            "task_count": candidate_metrics["task_count"],
            "passed": candidate_metrics["passed"],
            "failed": candidate_metrics["failed"],
        },
        "paired_task_count": len(paired),
        "failure_rate": {"baseline": baseline_metrics["failure_rate"], "candidate": candidate_metrics["failure_rate"]},
        "cost_per_success_eur": {"baseline": baseline_metrics["cost_per_success_eur"], "candidate": candidate_metrics["cost_per_success_eur"]},
        "p95_latency_ms": {"baseline": baseline_metrics["p95_latency_ms"], "candidate": candidate_metrics["p95_latency_ms"]},
        "newly_failing": newly_failing,
        "newly_fixed": newly_fixed,
    }
