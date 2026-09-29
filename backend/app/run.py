"""Run the hand-written fixture tasks with live model calls and span export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from opentelemetry import trace

from app.config.models import DEFAULT_CAPTURE_TIER, DEFAULT_MODEL_TIER
from app.instrumentation.setup import RunContext, configure_tracing, run_context, shutdown_tracing


def run_tasks(tasks: list[dict[str, Any]], *, run_id: str, capture_tier: str, model_tier: str, force_eval: bool = False) -> list[dict[str, Any]]:
    configure_tracing()
    from app.agent.graph import run_question
    from app.agent.injections import fixture_node_wrapper

    tracer = trace.get_tracer("agenttrace.runner")
    results = []
    try:
        for task in tasks:
            task_id = str(task.get("task_id", "unknown"))
            question = str(task.get("prompt", task.get("question", task.get("description", "")))).strip()
            if not question:
                raise ValueError(f"Task {task_id} has neither question nor description")
            context = RunContext(
                run_id=run_id,
                task_id=task_id,
                model_tier=model_tier,
                capture_tier=capture_tier,
                prompt_version=str(task.get("prompt_version", "v1")),
                is_eval=force_eval or bool(task.get("is_eval", "expected_failure_class" in task)),
            )
            with run_context(context):
                with tracer.start_as_current_span("agent.invoke_agent") as root:
                    root.set_attribute("gen_ai.operation.name", "invoke_agent")
                    root.set_attribute("gen_ai.agent.name", "agenttrace")
                    root.set_attribute("agenttrace.operation", "invoke_agent")
                    try:
                        result = run_question(
                            question,
                            tier=model_tier,
                            corpus_ids=[str(doc_id) for doc_id in task.get("corpus_ids", [])] or None,
                            node_wrapper=fixture_node_wrapper(task, tier=model_tier),
                        )
                    except Exception as exc:
                        root.record_exception(exc)
                        root.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                        result = {"answer": "", "supported": False, "revision_count": 0, "error": str(exc)}
                    answer = str(result.get("answer", ""))
                    expected = [str(item) for item in task.get("expected_contains", [])]
                    passed = all(item.casefold() in answer.casefold() for item in expected)
                    with tracer.start_as_current_span("gen_ai.chat output assertion") as assertion:
                        assertion.set_attribute("agenttrace.operation", "chat")
                        assertion.set_attribute("gen_ai.operation.name", "chat")
                        assertion.set_attribute("agenttrace.output_assertion_passed", passed)
                row = {"task_id": task_id, "run_id": run_id, **result}
                results.append(row)
                print(json.dumps(row, ensure_ascii=False))
    finally:
        shutdown_tracing()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgentTrace fixture tasks")
    parser.add_argument("--tasks", type=Path, required=True, help="JSON array of task objects")
    parser.add_argument("--tier", choices=("attrs", "full"), default=DEFAULT_CAPTURE_TIER, help="Telemetry content-capture tier")
    parser.add_argument("--model-tier", choices=("cheap", "mid", "premium"), default=DEFAULT_MODEL_TIER)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--eval", action="store_true", help="Mark every span in this run as evaluation telemetry")
    args = parser.parse_args()
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise ValueError("Tasks file must contain a JSON array")
    run_tasks(tasks, run_id=args.run_id, capture_tier=args.tier, model_tier=args.model_tier, force_eval=args.eval)


if __name__ == "__main__":
    main()
