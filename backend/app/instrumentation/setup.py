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
_provider: TracerProvider | None = None


def current_capture_tier() -> str:
    return _capture_tier.get()


@contextmanager
def run_context(context: RunContext) -> Iterator[None]:
    context_token = _run_context.set(context)
    tier_token = _capture_tier.set(context.capture_tier)
    try:
        yield
    finally:
        _capture_tier.reset(tier_token)
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
        if context.is_eval:
            span.set_attribute("agenttrace.is_eval", True)

    def on_end(self, span) -> None:
        return

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracing() -> TracerProvider:
    """Configure Phoenix OTLP and DuckDB exporters, then instrument graph and model calls."""
    global _provider
    if _provider is not None:
        return _provider

    database_path = os.getenv("AGENTTRACE_DB_PATH", "data/agenttrace.duckdb")
    phoenix_endpoint = os.getenv("PHOENIX_OTLP_ENDPOINT", "http://127.0.0.1:4317")
    provider = TracerProvider(resource=Resource.create({"service.name": "agenttrace"}))
    provider.add_span_processor(AgentTraceAttributesProcessor())
    provider.add_span_processor(SimpleSpanProcessor(DuckDBSpanExporter(database_path)))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=phoenix_endpoint, insecure=phoenix_endpoint.startswith("http://"))))
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
