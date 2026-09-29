"""Fixture-only node wrappers used to inject repeatable failure modes."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.agent.graph import AgentState, Node
from app.agent.llm import chat

tracer = trace.get_tracer("agenttrace.fixture_injections")
TOOL_TIMEOUT_SECONDS = 0.03
TOOL_HANG_SECONDS = 0.06
HALLUCINATION = "Confirmed. This result is certain and verified."


def fixture_node_wrapper(fixture: dict[str, Any], *, tier: str) -> Callable[[str, Node], Node]:
    """Wrap existing nodes; injected labels are written only by this boundary."""
    inject = fixture.get("inject")
    task_id = str(fixture.get("task_id", "fixture"))

    def wrap(name: str, node: Node) -> Node:
        if name == "tool" and inject == "tool_timeout":
            def timeout_tool(state: AgentState) -> dict[str, Any]:
                with tracer.start_as_current_span("tool.execute fixture timeout") as span:
                    span.set_attribute("agenttrace.operation", "execute_tool")
                    span.set_attribute("gen_ai.operation.name", "execute_tool")
                    span.set_attribute("error.type", "TimeoutError")
                    span.set_attribute("agenttrace.injected_failure", inject)
                    time.sleep(TOOL_HANG_SECONDS)
                    error = TimeoutError(f"fixture tool exceeded {TOOL_TIMEOUT_SECONDS}s timeout")
                    span.record_exception(error)
                    span.set_status(Status(StatusCode.ERROR, str(error)))
                return {"tool_result": f"Tool timeout: {error}"}
            return timeout_tool

        if name == "retrieve" and inject in {"retrieval_miss", "cascade"}:
            def miss_retrieval(state: AgentState) -> dict[str, Any]:
                restricted = {**state, "corpus_ids": [f"__absent_{task_id}__"]}
                with tracer.start_as_current_span("fixture.retrieve injected miss") as span:
                    span.set_attribute("agenttrace.operation", "retrieve")
                    span.set_attribute("gen_ai.operation.name", "retrieval")
                    span.set_attribute("gen_ai.retrieval.documents", "[]")
                    span.set_attribute("agenttrace.injected_failure", inject)
                    return node(restricted)
            return miss_retrieval

        if name == "synthesize":
            def validate_or_hallucinate(state: AgentState) -> dict[str, Any]:
                variant = state
                if inject in {"model_hallucination", "cascade"}:
                    # Make the single synthesis call with the abstention instruction
                    # removed, then stabilize the fixture's unsupported completion.
                    references = "\n\n".join(f"[{d['doc_id']}] {d['title']}\n{d['text']}" for d in state.get("documents", []))
                    prompt = (
                        f"Question: {state['question']}\nPlan: {state.get('plan', '')}\n"
                        f"Tool result: {state.get('tool_result', '')}\n"
                        f"Retrieved reference text:\n{references or '(No matching reference documents.)'}"
                    )
                    chat(
                        [
                            {"role": "system", "content": "You are a technical support agent. Answer confidently and concisely."},
                            {"role": "user", "content": prompt},
                        ],
                        tier=tier,
                        purpose="synthesize",
                    )
                    with tracer.start_as_current_span("fixture.model_hallucination") as span:
                        span.set_attribute("agenttrace.operation", "chat")
                        span.set_attribute("gen_ai.operation.name", "chat")
                        span.set_attribute("agenttrace.injected_failure", inject)
                    original = {"answer": HALLUCINATION}
                else:
                    original = node(variant)
                return original
            return validate_or_hallucinate

        if name == "critique" and inject == "orchestration_loop":
            def force_loop(state: AgentState) -> dict[str, Any]:
                result = node(state)
                iteration = int(state.get("revision", 0)) + 1
                with tracer.start_as_current_span("fixture.critique iteration cap") as span:
                    span.set_attribute("agenttrace.operation", "critique")
                    span.set_attribute("agenttrace.critique.iteration", iteration)
                    span.set_attribute("agenttrace.critique.hit_cap", iteration >= 3)
                    span.set_attribute("agenttrace.injected_failure", inject)
                return {**result, "supported": False, "revision": iteration}
            return force_loop

        return node

    return wrap
