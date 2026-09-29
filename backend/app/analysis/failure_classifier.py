"""Evidence-only trace classifier.

The classifier accepts a deliberately narrow record type. It has no arbitrary span
attributes, answer text, fixture data, or injection ground truth available to read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    parent_span_id: str | None
    name: str
    operation_name: str
    status: str
    start_time_ms: float
    retrieval_document_count: int | None = None
    retrieval_top_score: float | None = None
    output_assertion_passed: bool | None = None
    critique_hit_cap: bool = False


@dataclass(frozen=True)
class Attribution:
    primary_failure_class: str
    primary_failure_span_id: str | None
    secondary_symptom_span_ids: tuple[str, ...]


def _error_class(span: EvidenceSpan) -> str:
    operation = f"{span.operation_name} {span.name}".casefold()
    if "tool" in operation or "execute_tool" in operation:
        return "tool"
    if "retriev" in operation:
        return "retrieval"
    if "chat" in operation or "model" in operation or "synthesize" in operation:
        return "model"
    return "orchestration"


def classify_trace(spans: Sequence[EvidenceSpan], *, retrieval_score_threshold: float = 0.1) -> Attribution:
    """Classify one trace; earliest failing span is primary, later findings are symptoms."""
    ordered = sorted(spans, key=lambda span: (span.start_time_ms, span.span_id))
    findings: list[tuple[float, str, str]] = []
    for span in ordered:
        status = span.status.upper()
        if status == "ERROR":
            findings.append((span.start_time_ms, span.span_id, _error_class(span)))
        elif span.critique_hit_cap:
            findings.append((span.start_time_ms, span.span_id, "orchestration"))
        elif span.retrieval_document_count == 0 or (
            span.retrieval_top_score is not None and span.retrieval_top_score < retrieval_score_threshold
        ):
            findings.append((span.start_time_ms, span.span_id, "retrieval"))
        elif span.output_assertion_passed is False:
            findings.append((span.start_time_ms, span.span_id, "model"))

    if not findings:
        return Attribution("passed", None, ())
    # Only the first rule applies to an individual span. Across spans, preserve time order.
    findings.sort(key=lambda finding: (finding[0], finding[1]))
    return Attribution(findings[0][2], findings[0][1], tuple(f[1] for f in findings[1:]))
