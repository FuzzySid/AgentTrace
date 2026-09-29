---
doc_id: trace-identity
title: Trace and span identity
---
# Trace and span identity

A trace groups the work done for one request. Its trace ID is shared by every span in that request, including spans created by child agents and external calls. A span ID identifies one operation within the trace. A span also records its parent span ID, which makes nested work a tree rather than a flat list.

Preserve both identifiers when exporting or copying telemetry. A trace ID answers “which request?” A span ID answers “which operation?” The parent span ID answers “what called it?” Together they let an operator follow a request from the agent entry point through retrieval, tools, model calls, and a child summarizer.
