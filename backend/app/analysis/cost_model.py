"""Trace-level token pricing, evaluation separation, and wall-clock latency metrics."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from statistics import median
from typing import Any

from app.config.pricing import TIER_PRICING

NODE_TYPES = ("plan", "retrieve", "synthesize", "critique_loop")


def _attrs(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("attributes") or {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return dict(value)


def _price(input_tokens: int, output_tokens: int, tier: str) -> float:
    rates = TIER_PRICING.get(tier, TIER_PRICING.get("mid", {}))
    return (input_tokens * float(rates.get("input_per_million", 0)) + output_tokens * float(rates.get("output_per_million", 0))) / 1_000_000


def _node_type(attrs: dict[str, Any], operation: str | None) -> str | None:
    purpose = str(attrs.get("agenttrace.llm.purpose", "")).casefold()
    op = str(attrs.get("agenttrace.operation", operation or "")).casefold()
    name = purpose or op
    if name in {"critique", "critique_loop"}:
        return "critique_loop"
    if name == "summarize":
        return "synthesize"
    if name in NODE_TYPES:
        return name
    if "critique" in name:
        return "critique_loop"
    return None


def trace_costs(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate one output record per trace, separating evaluation spans."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("trace_id", ""))].append(row)
    traces: dict[str, dict[str, Any]] = {}
    for trace_id, spans in groups.items():
        root = next((span for span in spans if not span.get("parent_span_id")), None)
        duration = 0.0
        if root and root.get("start_time") and root.get("end_time"):
            duration = (root["end_time"] - root["start_time"]).total_seconds() * 1000
        output = {
            "trace_id": trace_id,
            "task_id": str((root or spans[0]).get("task_id", "")),
            "model_tier": "mid",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_eur": 0.0,
            "evaluation_input_tokens": 0,
            "evaluation_output_tokens": 0,
            "evaluation_cost_eur": 0.0,
            "duration_ms": duration,
            "span_count": len(spans),
            "status": "passed",
            "cost_by_span_type": {node: 0.0 for node in NODE_TYPES},
        }
        for span in spans:
            attrs = _attrs(span)
            tier = str(attrs.get("agenttrace.model_tier", output["model_tier"]))
            output["model_tier"] = tier
            # The wrapper span carries provider-reported usage; nested auto-instrumented
            # spans may repeat request metadata and must not double count the response.
            metered_call = bool(attrs.get("agenttrace.llm.purpose"))
            input_tokens = int(span.get("tokens_in") or 0) if metered_call else 0
            output_tokens = int(span.get("tokens_out") or 0) if metered_call else 0
            is_eval = attrs.get("agenttrace.is_eval") is True
            cost = _price(input_tokens, output_tokens, tier)
            if is_eval:
                output["evaluation_input_tokens"] += input_tokens
                output["evaluation_output_tokens"] += output_tokens
                output["evaluation_cost_eur"] += cost
            else:
                output["input_tokens"] += input_tokens
                output["output_tokens"] += output_tokens
                output["cost_eur"] += cost
                node_type = _node_type(attrs, span.get("operation_name"))
                if node_type:
                    output["cost_by_span_type"][node_type] += cost
        traces[trace_id] = output
    return traces


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return values[max(math.ceil(0.95 * len(values)) - 1, 0)]


def compute_cost_summary(rows: list[dict[str, Any]], statuses: dict[str, str]) -> dict[str, Any]:
    """Compute response metrics from exported span rows and classifier outcomes."""
    traces = trace_costs(rows)
    sessions = list(traces.values())
    for session in sessions:
        session["status"] = statuses.get(session["trace_id"], "passed")
    production_costs = [session["cost_eur"] for session in sessions]
    successful_costs = [session["cost_eur"] for session in sessions if session["status"] == "passed"]
    durations = [session["duration_ms"] for session in sessions]
    by_type = {node: sum(session["cost_by_span_type"][node] for session in sessions) for node in NODE_TYPES}
    buckets: dict[float, int] = defaultdict(int)
    for cost in production_costs:
        bucket = round(math.floor(cost * 1000 + 0.5) / 1000, 3)
        buckets[bucket] += 1
    total_evaluation_cost = sum(session["evaluation_cost_eur"] for session in sessions)
    return {
        "median_cost_eur": median(production_costs) if production_costs else 0.0,
        "median_cost_successful_eur": median(successful_costs) if successful_costs else 0.0,
        "cost_per_successful_session_eur": sum(production_costs) / len(successful_costs) if successful_costs else 0.0,
        "p50_latency_ms": median(durations) if durations else 0.0,
        "p95_latency_ms": _p95(durations),
        "cost_by_span_type": by_type,
        "distribution": [{"bucket_eur": bucket, "count": buckets[bucket]} for bucket in sorted(buckets)],
        "top_sessions": [
            {key: session[key] for key in ("task_id", "cost_eur", "duration_ms", "span_count", "status", "input_tokens", "output_tokens")}
            for session in sorted(sessions, key=lambda item: item["cost_eur"], reverse=True)[:8]
        ],
        "production_cost_eur": sum(production_costs),
        "evaluation_cost_eur": total_evaluation_cost,
        "evaluation_input_tokens": sum(session["evaluation_input_tokens"] for session in sessions),
        "evaluation_output_tokens": sum(session["evaluation_output_tokens"] for session in sessions),
        "total_input_tokens": sum(session["input_tokens"] for session in sessions),
        "total_output_tokens": sum(session["output_tokens"] for session in sessions),
        "session_count": len(sessions),
        "successful_session_count": len(successful_costs),
        "sessions": [
            {key: session[key] for key in ("trace_id", "task_id", "status", "input_tokens", "output_tokens", "cost_eur", "evaluation_input_tokens", "evaluation_output_tokens", "evaluation_cost_eur", "duration_ms", "span_count")}
            for session in sessions
        ],
    }
