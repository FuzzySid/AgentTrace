---
doc_id: retry-budget
title: Retry budget arithmetic
---
# Retry budget arithmetic

The maximum elapsed retry budget includes each attempt limit and each delay that occurs between attempts. For three attempts of two seconds each with two half-second backoffs, calculate `3 * 2 + 2 * 0.5`, which is seven seconds. There are only two backoffs because no delay is needed after the final attempt.

State assumptions when reporting a retry budget. The arithmetic is an upper bound if each attempt reaches its timeout. Network setup and cleanup time may add overhead outside the stated attempt limits.
