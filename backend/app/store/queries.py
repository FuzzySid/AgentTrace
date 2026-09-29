"""DuckDB-backed trace queries plus the remaining dashboard samples."""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from app.analysis.cost_model import compute_cost_summary, trace_costs
from app.analysis.failure_classifier import EvidenceSpan, classify_trace
from app.analysis.regression import compare_runs
from app.analysis.tax_harness import summarize_tax
from app.config.comparisons import BASELINE_COMPARISONS

_BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND / ".env")
_PRIVATE_NAMES = tuple(filter(None, (
    os.getenv("AGENTTRACE_PROVIDER_NAME", ""),
    os.getenv("AGENTTRACE_MODEL_CHEAP", ""),
    os.getenv("AGENTTRACE_MODEL_MID", ""),
    os.getenv("AGENTTRACE_MODEL_PREMIUM", ""),
)))
_COMMON_PROVIDER_NAMES = ("OpenAI", "Anthropic", "Google", "Gemini", "Vertex", "Amazon Bedrock", "AWS", "Azure", "Mistral", "Cohere", "Groq", "Together", "DeepSeek", "xAI")
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


def _public_text(value: str) -> str:
    for private_name in (*_PRIVATE_NAMES, *_COMMON_PROVIDER_NAMES):
        value = re.sub(re.escape(private_name), "[redacted]", value, flags=re.IGNORECASE)
    return value


def _public_attributes(attrs: dict) -> dict:
    result = {}
    for key, value in attrs.items():
        normalized = str(key).casefold()
        if "provider" in normalized or ("model" in normalized and normalized != "agenttrace.model_tier"):
            continue
        if isinstance(value, str):
            result[key] = _public_text(value)
        elif isinstance(value, dict):
            result[key] = _public_attributes(value)
        elif isinstance(value, list):
            result[key] = [_public_attributes(item) if isinstance(item, dict) else _public_text(item) if isinstance(item, str) else item for item in value]
        else:
            result[key] = value
    return result


def _evidence(rows: list[dict]) -> list[EvidenceSpan]:
    """Allowlist inference signals before constructing the classifier's input."""
    evidence = []
    for row in rows:
        attrs = _public_attributes(_attributes(row))
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
    costs = trace_costs(ordered)
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
        "cost_eur": next(iter(costs.values()), {}).get("cost_eur", 0.0),
        "span_count": len(rows),
        "capture_tier": next((str(row.get("capture_tier")) for row in rows if row.get("capture_tier")), "attrs"),
        "rows": ordered,
    }


def _run_statuses(rows: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("trace_id", ""))].append(row)
    result = {}
    for trace_id, trace_rows in groups.items():
        info = _trace_info(trace_rows)
        root = next((row for row in trace_rows if not row.get("parent_span_id")), trace_rows[0])
        attrs = _attributes(root)
        result[trace_id] = {
            "task_id": info["task_id"],
            "status": info["status"],
            "failure_class": info["failure_class"],
            "started_at": root.get("start_time").timestamp() if root.get("start_time") else 0,
            "prompt_version": attrs.get("agenttrace.prompt_version", "unknown"),
            "model_tier": attrs.get("agenttrace.model_tier", "unknown"),
        }
    return result

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
        attrs = _public_attributes(_attributes(row))
        # Injection labels are scoring ground truth and are never exposed as trace evidence.
        attrs.pop("agenttrace.injected_failure", None)
        start = row.get("start_time")
        parent_id = row.get("parent_span_id")
        depth = depths.get(str(parent_id), -1) + 1 if parent_id else 0
        depths[str(row.get("span_id", ""))] = depth
        spans.append({
            "span_id": str(row.get("span_id", "")),
            "parent_span_id": parent_id,
            "name": _public_text(str(row.get("name", ""))),
            "depth": depth,
            "start_ms": (start - origin).total_seconds() * 1000 if start and origin else 0,
            "duration_ms": float(row.get("duration_ms") or 0),
            "status": str(row.get("status", "UNSET")),
            "operation_name": _public_text(str(row.get("operation_name"))) if row.get("operation_name") else None,
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
    rows = _all_spans(run_id=run_id)
    return compute_cost_summary(rows, {trace_id: status["status"] for trace_id, status in _run_statuses(rows).items()})

def regression_comparison(comparison: str = "prompt", baseline: str | None = None, candidate: str | None = None):
    configured = BASELINE_COMPARISONS.get(comparison, BASELINE_COMPARISONS["prompt"])
    baseline_id = baseline or configured["baseline_run_id"]
    candidate_id = candidate or configured["candidate_run_id"]
    baseline_rows = _all_spans(run_id=baseline_id)
    candidate_rows = _all_spans(run_id=candidate_id)
    return compare_runs(
        baseline_id, baseline_rows, _run_statuses(baseline_rows),
        candidate_id, candidate_rows, _run_statuses(candidate_rows),
    )

def _tax_run_prefix(run_id: str) -> str:
    for suffix in ("-full", "-attrs", "-sampled"):
        if run_id.endswith(suffix):
            return run_id[:-len(suffix)]
    return run_id


def telemetry_tax(run_id: str):
    prefix = _tax_run_prefix(run_id)
    rows_by_tier = {tier: _all_spans(run_id=f"{prefix}-{tier}") for tier in ("full", "attrs", "sampled")}
    statuses_by_tier = {tier: _run_statuses(rows) for tier, rows in rows_by_tier.items()}
    return summarize_tax(rows_by_tier, statuses_by_tier)
