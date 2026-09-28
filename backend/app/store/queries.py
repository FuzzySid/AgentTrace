"""Mock query payloads; replace the functions here with DuckDB reads later."""

RUNS = [
    {"run_id": "run_001", "label": "run_2026-09-28T14:22", "task_count": 30, "passed": 24, "failed": 6, "capture_tier": "attrs"},
    {"run_id": "run_002", "label": "run_2026-09-21T09:15", "task_count": 30, "passed": 28, "failed": 2, "capture_tier": "attrs"},
]

TRACE_ROWS = [
    {"task_id": "fx_014", "trace_id": "7f3a9c2e", "status": "failed", "failure_class": "tool", "duration_ms": 4210, "cost_eur": 0.0042, "span_count": 14},
    {"task_id": "fx_021", "trace_id": "9c1b12a0", "status": "failed", "failure_class": "retrieval", "duration_ms": 2190, "cost_eur": 0.0018, "span_count": 8},
    {"task_id": "fx_008", "trace_id": "6a2d8841", "status": "failed", "failure_class": "orchestration", "duration_ms": 8410, "cost_eur": 0.0079, "span_count": 28},
    {"task_id": "fx_019", "trace_id": "1ef85c77", "status": "passed", "failure_class": None, "duration_ms": 1420, "cost_eur": 0.0011, "span_count": 6},
    {"task_id": "fx_004", "trace_id": "43ae19d1", "status": "passed", "failure_class": None, "duration_ms": 890, "cost_eur": 0.0008, "span_count": 5},
    {"task_id": "fx_011", "trace_id": "1a962be0", "status": "passed", "failure_class": None, "duration_ms": 3110, "cost_eur": 0.0029, "span_count": 9},
    {"task_id": "fx_029", "trace_id": "ad172c03", "status": "failed", "failure_class": "model", "duration_ms": 5120, "cost_eur": 0.0055, "span_count": 19},
]

SPAN_ROWS = [
    {"span_id": "a1", "parent_span_id": None, "name": "agent.execute_cycle", "depth": 0, "start_ms": 0, "duration_ms": 4210, "status": "OK", "operation_name": "agent", "tokens_in": None, "tokens_out": None, "attributes": {}},
    {"span_id": "b2", "parent_span_id": "a1", "name": "orchestrator.plan", "depth": 1, "start_ms": 0, "duration_ms": 410, "status": "OK", "operation_name": "plan", "tokens_in": 220, "tokens_out": 80, "attributes": {}},
    {"span_id": "c2", "parent_span_id": "a1", "name": "retrieval.vector_search", "depth": 1, "start_ms": 520, "duration_ms": 550, "status": "OK", "operation_name": "retrieve", "tokens_in": None, "tokens_out": None, "attributes": {}},
    {"span_id": "c3", "parent_span_id": "a1", "name": "model.completion", "depth": 1, "start_ms": 1120, "duration_ms": 1460, "status": "OK", "operation_name": "synthesize", "tokens_in": 1284, "tokens_out": 182, "attributes": {}},
    {"span_id": "c4", "parent_span_id": "a1", "name": "tool.execute.sql_client", "depth": 1, "start_ms": 2680, "duration_ms": 1820, "status": "ERROR", "operation_name": "tool", "tokens_in": None, "tokens_out": None, "attributes": {"error.type": "SocketTimeoutException", "error.message": "terminating connection due to idle-in-transaction timeout"}},
    {"span_id": "d6", "parent_span_id": "c4", "name": "db.postgres.connect", "depth": 2, "start_ms": 2700, "duration_ms": 280, "status": "OK", "operation_name": "tool", "tokens_in": None, "tokens_out": None, "attributes": {}},
    {"span_id": "d7", "parent_span_id": "c4", "name": "db.query.statement", "depth": 2, "start_ms": 2990, "duration_ms": 1520, "status": "ERROR", "operation_name": "tool", "tokens_in": None, "tokens_out": None, "attributes": {"error.type": "SocketTimeoutException"}},
    {"span_id": "e1", "parent_span_id": "a1", "name": "synthesizer.fallback_retry", "depth": 1, "start_ms": 3650, "duration_ms": 530, "status": "OK", "operation_name": "critique_loop", "tokens_in": 120, "tokens_out": 55, "attributes": {}},
]

def list_runs():
    return RUNS

def list_traces(run_id: str):
    return TRACE_ROWS

def trace_detail(trace_id: str):
    return {"trace_id": trace_id, "task_id": "fx_014", "capture_tier": "attrs", "primary_failure_span_id": "c4", "secondary_symptom_span_ids": ["d7"], "spans": SPAN_ROWS}

def confusion_matrix(run_id: str):
    return {"labels": ["tool", "retrieval", "model", "orchestration"], "matrix": [[11, 0, 1, 0], [0, 7, 0, 0], [0, 0, 5, 0], [1, 0, 0, 5]], "accuracy": 0.933}

def cost_summary(run_id: str):
    return {"median_cost_eur": 0.0031, "median_cost_successful_eur": 0.0024, "p50_latency_ms": 1420, "p95_latency_ms": 4820, "cost_by_span_type": {"plan": 0.0152, "retrieve": 0.0076, "synthesize": 0.0447, "critique_loop": 0.0414}, "distribution": [{"bucket_eur": 0.001, "count": 4}, {"bucket_eur": 0.002, "count": 6}, {"bucket_eur": 0.003, "count": 9}, {"bucket_eur": 0.004, "count": 4}, {"bucket_eur": 0.006, "count": 3}, {"bucket_eur": 0.008, "count": 4}], "top_sessions": [{"task_id": "fx_008", "cost_eur": 0.0079, "duration_ms": 8410, "span_count": 28, "status": "failed"}, {"task_id": "fx_029", "cost_eur": 0.0055, "duration_ms": 5120, "span_count": 19, "status": "failed"}, {"task_id": "fx_014", "cost_eur": 0.0042, "duration_ms": 4820, "span_count": 14, "status": "failed"}, {"task_id": "fx_003", "cost_eur": 0.0038, "duration_ms": 3920, "span_count": 12, "status": "passed"}, {"task_id": "fx_017", "cost_eur": 0.0031, "duration_ms": 2440, "span_count": 8, "status": "passed"}, {"task_id": "fx_012", "cost_eur": 0.0028, "duration_ms": 1890, "span_count": 7, "status": "passed"}]}

def regression_comparison(baseline: str, candidate: str):
    return {"baseline": {"run_id": baseline, "prompt_version": "v1-verbose", "model_tier": "mid"}, "candidate": {"run_id": candidate, "prompt_version": "v3-terse", "model_tier": "cheap"}, "failure_rate": {"baseline": 0.067, "candidate": 0.20}, "cost_per_success_eur": {"baseline": 0.0048, "candidate": 0.0024}, "p95_latency_ms": {"baseline": 3100, "candidate": 4820}, "newly_failing": [{"task_id": "fx_014", "failure_class": "tool"}, {"task_id": "fx_021", "failure_class": "retrieval"}, {"task_id": "fx_008", "failure_class": "orchestration"}, {"task_id": "fx_029", "failure_class": "model"}], "newly_fixed": [{"task_id": "fx_019"}]}

def telemetry_tax(run_id: str):
    return {"tiers": [{"tier": "full", "span_count": 420, "total_bytes": 42600000, "bytes_per_session": 1420000, "ratio_vs_full": 1.0}, {"tier": "attrs", "span_count": 420, "total_bytes": 13200000, "bytes_per_session": 440000, "ratio_vs_full": 0.31}, {"tier": "sampled", "span_count": 42, "total_bytes": 1700000, "bytes_per_session": 57000, "ratio_vs_full": 0.04}], "capabilities": [{"question": "Find a named session from last Tuesday", "full": "yes", "attrs": "yes", "sampled": "no"}, {"question": "Attribute a regression affecting 4 tasks", "full": "yes", "attrs": "yes", "sampled": "partial"}, {"question": "Read the actual prompt text", "full": "yes", "attrs": "no", "sampled": "no"}, {"question": "Trend failure rate over time", "full": "yes", "attrs": "yes", "sampled": "yes"}], "recommendation": {"default_tier": "attrs", "tradeoff": "Run Attributes only in production to localize failures and monitor unit economics at 69% lower storage cost; use Full only when prompt text debugging is required."}}
