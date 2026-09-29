---
doc_id: token-usage
title: Reporting model token usage
---
# Reporting model token usage

Record prompt and completion token counts from the provider response when they are present. Do not estimate counts from character or word lengths. Preserve the distinction between input and output tokens because pricing and latency analysis may treat them differently.

The requested model identifies the routing choice. The response model identifies the model that served the request when the provider returns that value. Keep the two fields separate so fallback routing is visible.
