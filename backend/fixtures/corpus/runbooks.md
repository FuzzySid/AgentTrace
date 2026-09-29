---
doc_id: runbooks
title: Agent incident response runbook
---
# Agent incident response runbook

This runbook describes a repeatable investigation for a production agent that returns incomplete answers or spends too long in a tool loop. Begin by identifying the affected run and task IDs. Compare the failure rate and latency against a known-good baseline. Select one representative failing task and one nearby successful task so that the comparison can reveal what changed.

Open the failing trace and follow parent-child relationships from the request root. Check whether the graph reached its retrieval node, which document IDs were returned, whether a child summarizer ran, and whether model synthesis received that evidence. Inspect tool spans for attempt count, timeout status, and elapsed time. The trace ID groups all work for the request; span IDs and parent IDs show the exact operation path.

Next, check the capture tier. Attributes-only traces preserve timing, error categories, usage values, and model routing while omitting raw prompts and responses. If the missing evidence is content itself, request an approved full-content diagnostic run with a narrow retention window. Do not infer prompt content from token counts. After the investigation, return to the lower-volume tier.

If a timeout triggered retries, verify that the operation is safe to repeat, count both attempt limits and the delays between attempts, and check that the graph stops after its configured retry limit. A retry budget should be explicit; with three two-second attempts and two half-second backoffs, the maximum described wait is seven seconds. Preserve the terminal error when the budget is exhausted.

Before closing the incident, record the root cause, the supporting trace and document IDs, the mitigation, and a follow-up action. Replay the task after the fix and compare the new trace with the original. A successful replay should show the expected nodes, bounded work, and an answer supported by retrieved sources.
