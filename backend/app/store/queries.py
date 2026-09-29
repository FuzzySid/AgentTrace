"""DuckDB-backed trace queries plus the remaining dashboard samples."""

import json
import os
from collections import defaultdict
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from app.analysis.failure_classifier import EvidenceSpan, classify_trace

_BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND / ".env")
_INJECTION_CLASS = {
    "tool_timeout": "tool",
    "retrieval_miss": "retrieval",
    "model_hallucination": "model",
    "orchestration_loop": "orchestration",
    "cascade": "retrieval",
}


def _database_path() -> Path:
    value = Path(os.getenv("AGENTTRACE_DB_PATH", str(_BACKEND / "data" / "agenttrace.duckdb")))
    return value if value.is_absolute() else Path.cwd() / value


def _connect():
    path = _database_path()
    if not path.exists():
        return None
    return duckdb.connect(str(path), read_only=True)


def _fixtures() -> dict[str, dict]:
    path = _BACKEND / "fixtures" / "tasks.json"
    return {str(item["task_id"]): item for item in json.loads(path.read_text(encoding="utf-8"))}


def _all_spans(run_id: str | None = None, trace_id: str | None = None) -> list[dict]:
    connection = _connect()
    if connection is None:
        return []
    try:
        where, values = [], []
        if run_id is not None:
            where.append("run_id = ?")
            values.append(run_id)
        if trace_id is not None:
            where.append("trace_id = ?")
            values.append(trace_id)
        query = "SELECT * FROM spans" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY start_time, span_id"
        columns = [column[0] for column in connection.execute(query, values).description]
        return [dict(zip(columns, row)) for row in connection.execute(query, values).fetchall()]
    finally:
        connection.close()


def _attributes(row: dict) -> dict:
    value = row.get("attributes") or {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return dict(value)


def _evidence(rows: list[dict]) -> list[EvidenceSpan]:
    """Allowlist inference signals before constructing the classifier's input."""
    evidence = []
    for row in rows:
        attrs = _attributes(row)
        operation = str(row.get("operation_name") or attrs.get("agenttrace.operation") or attrs.get("gen_ai.operation.name") or "")
        retrieval_count = None
        top_score = None
        if operation.casefold() in {"retrieve", "retrieval"} or "retriev" in operation.casefold():
            docs = attrs.get("gen_ai.retrieval.documents")
            if isinstance(docs, str):
                try:
                    docs = json.loads(docs)
                except json.JSONDecodeError:
                    docs = None
            if isinstance(docs, list):
                retrieval_count = len(docs)
                scores = [item.get("score") for item in docs if isinstance(item, dict) and isinstance(item.get("score"), (int, float))]
                top_score = max(scores) if scores else None
        start = row.get("start_time")
        start_ms = start.timestamp() * 1000 if start is not None else 0.0
        evidence.append(EvidenceSpan(
            span_id=str(row.get("span_id", "")),
            parent_span_id=row.get("parent_span_id"),
            name=str(row.get("name", "")),
            operation_name=operation,
            status=str(row.get("status", "UNSET")),
            start_time_ms=start_ms,
            retrieval_document_count=retrieval_count,
            retrieval_top_score=top_score,
            output_assertion_passed=attrs.get("agenttrace.output_assertion_passed") if isinstance(attrs.get("agenttrace.output_assertion_passed"), bool) else None,
            critique_hit_cap=attrs.get("agenttrace.critique.hit_cap") is True,
        ))
    return evidence


def _trace_info(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda r: (r.get("start_time") or 0, r.get("span_id", "")))
    attribution = classify_trace(_evidence(ordered))
    starts = [row["start_time"] for row in ordered if row.get("start_time")]
    ends = [row["end_time"] for row in ordered if row.get("end_time")]
    duration = (max(ends) - min(starts)).total_seconds() * 1000 if starts and ends else 0.0
    tasks = {str(row.get("task_id", "")) for row in rows}
    run_ids = {str(row.get("run_id", "")) for row in rows}
    trace_ids = {str(row.get("trace_id", "")) for row in rows}
    return {
        "trace_id": next(iter(trace_ids), ""),
        "task_id": next(iter(tasks), ""),
        "run_id": next(iter(run_ids), ""),
        "attribution": attribution,
        "status": "passed" if attribution.primary_failure_class == "passed" else "failed",
        "failure_class": None if attribution.primary_failure_class == "passed" else attribution.primary_failure_class,
        "duration_ms": duration,
        "cost_eur": sum(float(row.get("cost_eur") or 0) for row in rows),
        "span_count": len(rows),
        "capture_tier": next((str(row.get("capture_tier")) for row in rows if row.get("capture_tier")), "attrs"),
        "rows": ordered,
    }

def list_runs():
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in _all_spans():
        groups[str(row.get("run_id", ""))].append(row)
    runs = []
    for run_id, rows in groups.items():
        by_trace = defaultdict(list)
        for row in rows:
            by_trace[str(row.get("trace_id", ""))].append(row)
        infos = [_trace_info(spans) for spans in by_trace.values()]
        runs.append({
            "run_id": run_id,
            "label": run_id,
            "task_count": len({info["task_id"] for info in infos}),
            "passed": sum(info["status"] == "passed" for info in infos),
            "failed": sum(info["status"] == "failed" for info in infos),
            "capture_tier": next((str(row.get("capture_tier")) for row in rows if row.get("capture_tier")), "attrs"),
            "_sort_time": min((row["start_time"] for row in rows if row.get("start_time")), default=None),
        })
    return [{key: run[key] for key in ("run_id", "label", "task_count", "passed", "failed", "capture_tier")} for run in sorted(runs, key=lambda item: item["_sort_time"] or 0, reverse=True)]

def list_traces(run_id: str):
    groups = defaultdict(list)
    for row in _all_spans(run_id=run_id):
        groups[str(row.get("trace_id", ""))].append(row)
    infos = [_trace_info(rows) for rows in groups.values()]
    # Keep one latest trace per fixture task when a run was resumed or repeated.
    latest = {}
    for info in infos:
        key = info["task_id"]
        if key not in latest or info["rows"][-1].get("start_time") > latest[key]["rows"][-1].get("start_time"):
            latest[key] = info
    return [{key: info[key] for key in ("task_id", "trace_id", "status", "failure_class", "duration_ms", "cost_eur", "span_count")} for info in sorted(latest.values(), key=lambda item: item["rows"][0].get("start_time") or 0)]

def trace_detail(trace_id: str):
    rows = _all_spans(trace_id=trace_id)
    if not rows:
        return {"trace_id": trace_id, "task_id": "", "capture_tier": "attrs", "primary_failure_span_id": None, "secondary_symptom_span_ids": [], "spans": []}
    info = _trace_info(rows)
    origin = min((row["start_time"] for row in info["rows"] if row.get("start_time")), default=None)
    spans = []
    depths = {}
    for row in info["rows"]:
        attrs = _attributes(row)
        # Injection labels are scoring ground truth and are never exposed as trace evidence.
        attrs.pop("agenttrace.injected_failure", None)
        start = row.get("start_time")
        parent_id = row.get("parent_span_id")
        depth = depths.get(str(parent_id), -1) + 1 if parent_id else 0
        depths[str(row.get("span_id", ""))] = depth
        spans.append({
            "span_id": str(row.get("span_id", "")),
            "parent_span_id": parent_id,
            "name": str(row.get("name", "")),
            "depth": depth,
            "start_ms": (start - origin).total_seconds() * 1000 if start and origin else 0,
            "duration_ms": float(row.get("duration_ms") or 0),
            "status": str(row.get("status", "UNSET")),
            "operation_name": row.get("operation_name"),
            "tokens_in": row.get("tokens_in"),
            "tokens_out": row.get("tokens_out"),
            "attributes": attrs,
        })
    return {
        "trace_id": trace_id,
        "task_id": info["task_id"],
        "capture_tier": info["capture_tier"],
        "primary_failure_span_id": info["attribution"].primary_failure_span_id,
        "secondary_symptom_span_ids": list(info["attribution"].secondary_symptom_span_ids),
        "spans": spans,
    }

def confusion_matrix(run_id: str):
    labels = ["tool", "retrieval", "model", "orchestration"]
    matrix = [[0 for _ in labels] for _ in labels]
    fixture_map = _fixtures()
    groups = defaultdict(list)
    for row in _all_spans(run_id=run_id):
        groups[str(row.get("trace_id", ""))].append(row)
    latest = {}
    for rows in groups.values():
        info = _trace_info(rows)
        task_id = info["task_id"]
        if task_id not in fixture_map:
            continue
        if task_id not in latest or info["rows"][-1].get("start_time") > latest[task_id]["rows"][-1].get("start_time"):
            latest[task_id] = info
    correct = 0
    for task_id, info in latest.items():
        # Ground truth is read here by the scorer. _evidence has already reduced
        # the same spans to EvidenceSpan records before the classifier is called.
        injected = next((str(value) for row in info["rows"] for value in [_attributes(row).get("agenttrace.injected_failure")] if value), None)
        truth = _INJECTION_CLASS.get(injected, str(fixture_map[task_id].get("expected_failure_class", "passed")))
        predicted = info["attribution"].primary_failure_class
        if truth == "passed":
            if predicted == "passed":
                correct += 1
            continue
        if truth not in labels:
            continue
        if predicted in labels:
            matrix[labels.index(truth)][labels.index(predicted)] += 1
        if predicted == truth:
            correct += 1
    return {"labels": labels, "matrix": matrix, "accuracy": correct / len(latest) if latest else 0.0}

def cost_summary(run_id: str):
    return {"median_cost_eur": 0.0031, "median_cost_successful_eur": 0.0024, "p50_latency_ms": 1420, "p95_latency_ms": 4820, "cost_by_span_type": {"plan": 0.0152, "retrieve": 0.0076, "synthesize": 0.0447, "critique_loop": 0.0414}, "distribution": [{"bucket_eur": 0.001, "count": 4}, {"bucket_eur": 0.002, "count": 6}, {"bucket_eur": 0.003, "count": 9}, {"bucket_eur": 0.004, "count": 4}, {"bucket_eur": 0.006, "count": 3}, {"bucket_eur": 0.008, "count": 4}], "top_sessions": [{"task_id": "fx_008", "cost_eur": 0.0079, "duration_ms": 8410, "span_count": 28, "status": "failed"}, {"task_id": "fx_029", "cost_eur": 0.0055, "duration_ms": 5120, "span_count": 19, "status": "failed"}, {"task_id": "fx_014", "cost_eur": 0.0042, "duration_ms": 4820, "span_count": 14, "status": "failed"}, {"task_id": "fx_003", "cost_eur": 0.0038, "duration_ms": 3920, "span_count": 12, "status": "passed"}, {"task_id": "fx_017", "cost_eur": 0.0031, "duration_ms": 2440, "span_count": 8, "status": "passed"}, {"task_id": "fx_012", "cost_eur": 0.0028, "duration_ms": 1890, "span_count": 7, "status": "passed"}]}

def regression_comparison(baseline: str, candidate: str):
    return {"baseline": {"run_id": baseline, "prompt_version": "v1-verbose", "model_tier": "mid"}, "candidate": {"run_id": candidate, "prompt_version": "v3-terse", "model_tier": "cheap"}, "failure_rate": {"baseline": 0.067, "candidate": 0.20}, "cost_per_success_eur": {"baseline": 0.0048, "candidate": 0.0024}, "p95_latency_ms": {"baseline": 3100, "candidate": 4820}, "newly_failing": [{"task_id": "fx_014", "failure_class": "tool"}, {"task_id": "fx_021", "failure_class": "retrieval"}, {"task_id": "fx_008", "failure_class": "orchestration"}, {"task_id": "fx_029", "failure_class": "model"}], "newly_fixed": [{"task_id": "fx_019"}]}

def telemetry_tax(run_id: str):
    return {"tiers": [{"tier": "full", "span_count": 420, "total_bytes": 42600000, "bytes_per_session": 1420000, "ratio_vs_full": 1.0}, {"tier": "attrs", "span_count": 420, "total_bytes": 13200000, "bytes_per_session": 440000, "ratio_vs_full": 0.31}, {"tier": "sampled", "span_count": 42, "total_bytes": 1700000, "bytes_per_session": 57000, "ratio_vs_full": 0.04}], "capabilities": [{"question": "Find a named session from last Tuesday", "full": "yes", "attrs": "yes", "sampled": "no"}, {"question": "Attribute a regression affecting 4 tasks", "full": "yes", "attrs": "yes", "sampled": "partial"}, {"question": "Read the actual prompt text", "full": "yes", "attrs": "no", "sampled": "no"}, {"question": "Trend failure rate over time", "full": "yes", "attrs": "yes", "sampled": "yes"}], "recommendation": {"default_tier": "attrs", "tradeoff": "Run Attributes only in production to localize failures and monitor unit economics at 69% lower storage cost; use Full only when prompt text debugging is required."}}
