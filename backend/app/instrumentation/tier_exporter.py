"""Apply capture policy at the exporter boundary, including trace-level sampling."""

from __future__ import annotations

import hashlib
import threading
from collections import defaultdict
from typing import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


CONTENT_ATTRIBUTES = {
    "gen_ai.input.messages",
    "gen_ai.output.messages",
    "agenttrace.retrieval.document_bodies",
}
CONTENT_EVENT_NAMES = {"gen_ai.prompt", "gen_ai.completion", "gen_ai.input.messages", "gen_ai.output.messages"}


def _trace_id(span: ReadableSpan) -> str:
    return f"{span.context.trace_id:032x}" if span.context else ""


def _sampled(trace_id: str) -> bool:
    digest = hashlib.sha256(trace_id.encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") < int(0.10 * (1 << 64))


def _with_capture_tier(span: ReadableSpan, tier: str) -> ReadableSpan:
    attributes = dict(span.attributes or {})
    if tier != "full":
        attributes = {
            key: value
            for key, value in attributes.items()
            if key.startswith(("gen_ai.", "agenttrace.")) and key not in CONTENT_ATTRIBUTES
        }
        events = tuple(
            event for event in span.events
            if event.name.casefold() not in CONTENT_EVENT_NAMES
            and not event.name.casefold().startswith(("gen_ai.prompt.", "gen_ai.completion."))
        )
    else:
        events = tuple(span.events)
    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=attributes,
        events=events,
        links=tuple(span.links),
        kind=span.kind,
        instrumentation_info=span.instrumentation_info,
        status=span.status,
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class CaptureTierSpanExporter(SpanExporter):
    """Buffer spans until the root arrives, then filter/sample and export one trace."""

    def __init__(self, exporter: SpanExporter):
        self.exporter = exporter
        self._pending: dict[str, list[ReadableSpan]] = defaultdict(list)
        self._lock = threading.Lock()
        self._closed = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._closed:
            return SpanExportResult.FAILURE
        ready: list[tuple[str, list[ReadableSpan]]] = []
        with self._lock:
            for span in spans:
                trace_id = _trace_id(span)
                if not trace_id:
                    continue
                self._pending[trace_id].append(span)
                if span.parent is None or not span.parent.is_valid:
                    ready.append((trace_id, self._pending.pop(trace_id)))
        for trace_id, trace_spans in ready:
            root = next((span for span in trace_spans if span.parent is None or not span.parent.is_valid), None)
            tier = str((root.attributes or {}).get("agenttrace.capture_tier", "attrs")) if root else "attrs"
            keep = tier != "sampled" or bool(
                root and root.status.status_code.name == "ERROR"
            ) or _sampled(trace_id)
            if keep:
                filtered = [_with_capture_tier(span, tier) for span in trace_spans]
                result = self.exporter.export(filtered)
                if result is not SpanExportResult.SUCCESS:
                    return result
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.exporter.force_flush(timeout_millis)

    def shutdown(self) -> None:
        if self._closed:
            return
        with self._lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for trace_id, spans in pending:
            tier = str(next((s.attributes.get("agenttrace.capture_tier") for s in spans if s.attributes), "attrs"))
            if tier != "sampled" or _sampled(trace_id):
                self.exporter.export([_with_capture_tier(span, tier) for span in spans])
        self.exporter.shutdown()
        self._closed = True
