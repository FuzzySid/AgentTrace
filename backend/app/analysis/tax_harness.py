"""Exporter-tier comparison and real capability attempts over captured span data."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config.recommendation import TELEMETRY_RECOMMENDATION

CAPTURE_TIERS = ("full", "attrs", "sampled")
REGRESSION_TASK_IDS = ("fx_001", "fx_005", "fx_010", "fx_014")
REGRESSION_CLASSES = {"fx_001": "tool", "fx_005": "retrieval", "fx_010": "model", "fx_014": "orchestration"}
TRACE_LOOKUP_TASK_ID = "fx_014"
TREND_WINDOW_SECONDS = 10
QUESTIONS = (
    f"Find the full trace for task {TRACE_LOOKUP_TASK_ID}",
    "Attribute a regression affecting fx_001, fx_005, fx_010, and fx_014",
    "Retrieve the raw prompt text",
    "Compute the failure-rate trend across the run",
)


def _attrs(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("attributes") or {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return dict(value)


def _events(row: dict[str, Any]) -> list[dict[str, Any]]:
    value = row.get("events") or []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    return value if isinstance(value, list) else []


def _groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[str(row.get("trace_id", ""))].append(row)
    return result


def _attempt_trace(task_id: str, rows: list[dict[str, Any]], reference: list[dict[str, Any]]) -> str:
    actual = [row for row in rows if str(row.get("task_id")) == task_id]
    expected_count = len([row for row in reference if str(row.get("task_id")) == task_id])
    if not actual:
        return "fails"
    span_ids = {str(row.get("span_id")) for row in actual}
    roots = [row for row in actual if not row.get("parent_span_id")]
    connected = bool(roots) and all(not row.get("parent_span_id") or str(row["parent_span_id"]) in span_ids for row in actual)
    complete = len(actual) >= expected_count and connected and all(int(row.get("serialized_bytes") or 0) > 0 for row in actual)
    return "success" if complete else "degrades"


def _attempt_regression(rows: list[dict[str, Any]], statuses: dict[str, dict[str, Any]]) -> str:
    groups = _groups(rows)
    by_task = {}
    for trace_id in groups:
        info = statuses.get(trace_id, {})
        task_id = str(info.get("task_id", ""))
        if task_id in REGRESSION_TASK_IDS and task_id not in by_task:
            by_task[task_id] = info
    attributed = sum(
        by_task.get(task_id, {}).get("status") == "failed"
        and by_task.get(task_id, {}).get("failure_class") == expected_class
        for task_id, expected_class in REGRESSION_CLASSES.items()
    )
    if attributed == len(REGRESSION_CLASSES):
        return "success"
    return "degrades" if attributed or by_task else "fails"


def _attempt_prompt(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        attrs = _attrs(row)
        if attrs.get("gen_ai.input.messages"):
            return "success"
        for event in _events(row):
            if event.get("name") == "gen_ai.prompt" and (event.get("attributes") or {}).get("gen_ai.prompt.text"):
                return "success"
    return "fails"


def _attempt_trend(rows: list[dict[str, Any]], statuses: dict[str, dict[str, Any]]) -> str:
    roots = [row for row in rows if not row.get("parent_span_id") and row.get("start_time")]
    if not roots:
        return "fails"
    first = min(row["start_time"] for row in roots)
    bins: dict[int, list[str]] = defaultdict(list)
    by_trace = {str(row.get("trace_id")): row for row in roots}
    for trace_id, root in by_trace.items():
        bucket = math.floor((root["start_time"] - first).total_seconds() / TREND_WINDOW_SECONDS)
        status = str(statuses.get(trace_id, {}).get("status", ""))
        if status not in {"passed", "failed"}:
            return "degrades"
        bins[bucket].append(status)
    failure_rates = [sum(status == "failed" for status in bin_statuses) / len(bin_statuses) for _, bin_statuses in sorted(bins.items()) if bin_statuses]
    if len(failure_rates) >= 2:
        return "success"
    return "degrades" if len(bins) == 1 and len(roots) > 1 else "fails"


def summarize_tax(
    rows_by_tier: dict[str, list[dict[str, Any]]],
    statuses_by_tier: dict[str, dict[str, dict[str, Any]]],
    recommendation: dict[str, str] | None = None,
) -> dict[str, Any]:
    full_rows = rows_by_tier.get("full", [])
    full_total = sum(int(row.get("serialized_bytes") or 0) for row in full_rows)
    tiers = []
    capabilities = [
        {
            "question": QUESTIONS[0],
            "full": _attempt_trace(TRACE_LOOKUP_TASK_ID, full_rows, full_rows),
            "attrs": _attempt_trace(TRACE_LOOKUP_TASK_ID, rows_by_tier.get("attrs", []), full_rows),
            "sampled": _attempt_trace(TRACE_LOOKUP_TASK_ID, rows_by_tier.get("sampled", []), full_rows),
        },
        {
            "question": QUESTIONS[1],
            "full": _attempt_regression(full_rows, statuses_by_tier.get("full", {})),
            "attrs": _attempt_regression(rows_by_tier.get("attrs", []), statuses_by_tier.get("attrs", {})),
            "sampled": _attempt_regression(rows_by_tier.get("sampled", []), statuses_by_tier.get("sampled", {})),
        },
    ]
    for tier in CAPTURE_TIERS:
        rows = rows_by_tier.get(tier, [])
        total_bytes = sum(int(row.get("serialized_bytes") or 0) for row in rows)
        sessions = len(_groups(rows))
        tiers.append({
            "tier": tier,
            "span_count": len(rows),
            "total_bytes": total_bytes,
            "bytes_per_session": total_bytes / sessions if sessions else 0,
            "ratio_vs_full": total_bytes / full_total if full_total else 0,
        })
    # Each diagnostic is attempted independently for each tier's own captured data.
    capabilities.extend([
        {
            "question": QUESTIONS[2],
            **{tier: _attempt_prompt(rows_by_tier.get(tier, [])) for tier in CAPTURE_TIERS},
        },
        {
            "question": QUESTIONS[3],
            **{tier: _attempt_trend(rows_by_tier.get(tier, []), statuses_by_tier.get(tier, {})) for tier in CAPTURE_TIERS},
        },
    ])
    return {"tiers": tiers, "capabilities": capabilities, "recommendation": recommendation or TELEMETRY_RECOMMENDATION}


def run_capture_matrix(tasks_path: Path, run_prefix: str, model_tier: str = "mid", prompt_version: str = "verbose") -> dict[str, str]:
    """Execute the same fixture JSON through all three exporter policies."""
    backend = Path(__file__).resolve().parents[2]
    task_path = tasks_path if tasks_path.is_absolute() else (Path.cwd() / tasks_path).resolve()
    run_ids = {}
    for capture_tier in CAPTURE_TIERS:
        run_id = f"{run_prefix}-{capture_tier}"
        subprocess.run(
            [
                sys.executable, "-m", "app.run", "--tasks", str(task_path),
                "--tier", model_tier, "--capture-tier", capture_tier,
                "--prompt-version", prompt_version, "--run-id", run_id,
            ],
            cwd=backend,
            check=True,
        )
        run_ids[capture_tier] = run_id
    return run_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentTrace capture-tier tax harness")
    parser.add_argument("--tasks", type=Path, default=Path("fixtures/tasks.json"))
    parser.add_argument("--run-prefix", required=True)
    parser.add_argument("--tier", choices=("cheap", "mid", "premium"), default="mid")
    parser.add_argument("--prompt-version", choices=("verbose", "terse"), default="verbose")
    args = parser.parse_args()
    print(json.dumps(run_capture_matrix(args.tasks, args.run_prefix, args.tier, args.prompt_version), indent=2))


if __name__ == "__main__":
    main()
