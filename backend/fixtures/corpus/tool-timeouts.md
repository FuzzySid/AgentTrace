---
doc_id: tool-timeouts
title: Responding to tool timeouts
---
# Responding to tool timeouts

When a tool call times out, record the tool name, timeout limit, attempt number, and error class. Retry only when the operation is safe to repeat and the failure may be temporary. Use a bounded retry count and a delay between attempts. Avoid retrying a non-idempotent action unless it has an idempotency key.

If the retry budget is exhausted, stop the loop, preserve the failure evidence, and return a clear status. Do not hide a timeout by converting it into an empty successful result.
