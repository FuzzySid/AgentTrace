"""OpenTelemetry providers, OpenInference instrumentors, and per-run span context."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from openinference.instrumentation import TraceConfig
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor

from app.instrumentation.duckdb_exporter import DuckDBSpanExporter
from app.instrumentation.tier_exporter import CaptureTierSpanExporter

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class RunContext:
    run_id: str
    task_id: str
    model_tier: str
    capture_tier: str
    prompt_version: str
    is_eval: bool = False


_run_context: ContextVar[RunContext | None] = ContextVar("agenttrace_run_context", default=None)
_capture_tier: ContextVar[str] = ContextVar("agenttrace_capture_tier", default="attrs")
_is_eval_call: ContextVar[bool] = ContextVar("agenttrace_is_eval_call", default=False)
_prompt_version: ContextVar[str] = ContextVar("agenttrace_prompt_version", default="verbose")
_provider: TracerProvider | None = None


def current_capture_tier() -> str:
    return _capture_tier.get()


def current_prompt_version() -> str:
    return _prompt_version.get()


@contextmanager
def evaluation_call() -> Iterator[None]:
    """Tag spans for a judge/evaluation call without tagging the full agent session."""
    token = _is_eval_call.set(True)
    try:
        yield
    finally:
        _is_eval_call.reset(token)


@contextmanager
def run_context(context: RunContext) -> Iterator[None]:
    context_token = _run_context.set(context)
    tier_token = _capture_tier.set(context.capture_tier)
    prompt_token = _prompt_version.set(context.prompt_version)
    try:
        yield
    finally:
        _capture_tier.reset(tier_token)
        _prompt_version.reset(prompt_token)
        _run_context.reset(context_token)


class AgentTraceAttributesProcessor(SpanProcessor):
    """Apply run metadata to every span created in that run's active context."""

    def on_start(self, span: Span, parent_context=None) -> None:
        context = _run_context.get()
        if context is None:
            return
        span.set_attribute("agenttrace.prompt_version", context.prompt_version)
        span.set_attribute("agenttrace.model_tier", context.model_tier)
        span.set_attribute("agenttrace.task_id", context.task_id)
        span.set_attribute("agenttrace.run_id", context.run_id)
        span.set_attribute("agenttrace.capture_tier", context.capture_tier)
        if context.is_eval or _is_eval_call.get():
            span.set_attribute("agenttrace.is_eval", True)

    def on_end(self, span) -> None:
        return

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracing(run_id: str | None = None) -> TracerProvider:
    """Configure Phoenix OTLP and DuckDB exporters, then instrument graph and model calls."""
    global _provider
    if _provider is not None:
        return _provider

    database_path = os.getenv("AGENTTRACE_DB_PATH", "data/agenttrace.duckdb")
    phoenix_endpoint = os.getenv("PHOENIX_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    provider = TracerProvider(resource=Resource.create({"service.name": "agenttrace"}))
    provider.add_span_processor(AgentTraceAttributesProcessor())
    database_exporter = DuckDBSpanExporter(database_path)
    if run_id is not None:
        database_exporter.clear_run(run_id)
    provider.add_span_processor(SimpleSpanProcessor(CaptureTierSpanExporter(database_exporter)))
    otlp_exporter = OTLPSpanExporter(endpoint=phoenix_endpoint, insecure=phoenix_endpoint.startswith("http://"))
    provider.add_span_processor(BatchSpanProcessor(CaptureTierSpanExporter(otlp_exporter)))
    trace.set_tracer_provider(provider)

    # LangGraph is built on LangChain runnables; this instrumentor captures graph/node
    # execution. LiteLLM instrumentation captures the provider request as a child span.
    privacy_config = TraceConfig(
        hide_inputs=True,
        hide_outputs=True,
        hide_input_messages=True,
        hide_output_messages=True,
        hide_prompts=True,
    )
    LangChainInstrumentor().instrument(tracer_provider=provider, config=privacy_config)
    LiteLLMInstrumentor().instrument(tracer_provider=provider, config=privacy_config)
    _provider = provider
    return provider


def shutdown_tracing() -> None:
    global _provider
    if _provider is not None:
        _provider.force_flush()
        _provider.shutdown()
        _provider = None
