"""OpenTelemetry SpanExporter that writes OTLP-sized spans into DuckDB."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import duckdb
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


def _as_datetime(timestamp_ns: int | None) -> datetime | None:
    if timestamp_ns is None:
        return None
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, timezone.utc).replace(tzinfo=None)


def _json_safe(value):
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def serialized_span_size(span: ReadableSpan) -> int:
    """Return the encoded OTLP protobuf Span message size, not a text estimate."""
    request = encode_spans([span])
    protobuf_span = request.resource_spans[0].scope_spans[0].spans[0]
    return len(protobuf_span.SerializeToString())


class DuckDBSpanExporter(SpanExporter):
    """Persist ended spans and the size of their OTLP protobuf representation."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        if not self.database_path.is_absolute():
            self.database_path = Path.cwd() / self.database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        schema = Path(__file__).resolve().parents[1] / "store" / "schema.sql"
        self._connection = duckdb.connect(str(self.database_path))
        self._connection.execute(schema.read_text(encoding="utf-8"))
        self._connection.execute("ALTER TABLE spans ADD COLUMN IF NOT EXISTS serialized_bytes BIGINT DEFAULT 0")
        self._lock = threading.Lock()
        self._closed = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._closed:
            return SpanExportResult.FAILURE
        rows = []
        for span in spans:
            attrs = dict(span.attributes or {})
            context = span.context
            if context is None:
                continue
            parent = span.parent
            start_ns, end_ns = span.start_time, span.end_time
            duration_ms = None if start_ns is None or end_ns is None else (end_ns - start_ns) / 1_000_000
            status = getattr(span.status.status_code, "name", str(span.status.status_code))
            input_tokens = attrs.get("gen_ai.usage.input_tokens")
            output_tokens = attrs.get("gen_ai.usage.output_tokens")
            rows.append((
                f"{context.trace_id:032x}",
                f"{context.span_id:016x}",
                f"{parent.span_id:016x}" if parent and parent.is_valid else None,
                str(attrs.get("agenttrace.task_id", "unknown")),
                str(attrs.get("agenttrace.run_id", "unknown")),
                str(span.name),
                str(attrs.get("agenttrace.operation", attrs.get("gen_ai.operation.name", ""))) or None,
                int(attrs.get("agenttrace.depth", 0)),
                _as_datetime(start_ns),
                _as_datetime(end_ns),
                duration_ms,
                status,
                str(attrs.get("agenttrace.capture_tier", "attrs")),
                int(input_tokens) if isinstance(input_tokens, int) else None,
                int(output_tokens) if isinstance(output_tokens, int) else None,
                None,
                json.dumps(_json_safe(attrs), ensure_ascii=False, separators=(",", ":")),
                serialized_span_size(span),
            ))
        if not rows:
            return SpanExportResult.SUCCESS
        with self._lock:
            self._connection.executemany(
                """INSERT OR REPLACE INTO spans (
                    trace_id, span_id, parent_span_id, task_id, run_id, name,
                    operation_name, depth, start_time, end_time, duration_ms,
                    status, capture_tier, tokens_in, tokens_out, cost_eur,
                    attributes, serialized_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::JSON, ?)""",
                rows,
            )
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return not self._closed

    def shutdown(self) -> None:
        if not self._closed:
            with self._lock:
                self._connection.close()
                self._closed = True
