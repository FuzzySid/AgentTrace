---
doc_id: parent-child
title: Parent-child span relationships
---
# Parent-child span relationships

Start a child span while its caller is active. OpenTelemetry context propagation assigns the caller's span ID as the child parent ID. In asynchronous work, pass the active context explicitly when tasks cross thread or process boundaries.

A trace with disconnected roots is harder to read and can hide causal relationships. Keep the request span active while invoking a graph, and keep a summarizer sub-agent inside the retrieval node's active context.
