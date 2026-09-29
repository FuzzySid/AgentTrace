---
doc_id: incident-severity
title: Agent incident severity
---
# Agent incident severity

Prioritize an incident by user impact, frequency, and whether the agent can recover safely. A single failed tool call may be low severity when a bounded fallback works. A repeated failure that affects most requests or produces misleading answers needs immediate investigation.

Use trace evidence to distinguish a tool outage from retrieval gaps, unsupported synthesis, and orchestration loops. Preserve representative successful and failing traces for comparison.
