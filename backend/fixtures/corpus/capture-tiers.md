---
doc_id: capture-tiers
title: Choosing a telemetry capture tier
---
# Choosing a telemetry capture tier

An attributes-only tier stores identifiers, operation names, status, timing, error classes, model identifiers, and usage counts without prompt or response bodies. It supports most latency, failure-rate, and token-cost investigations while reducing sensitive content storage.

A full-content tier stores prompts and responses as well as attributes. Use it only when content is needed to diagnose a specific issue and access controls permit retention. A sampled tier lowers volume but can omit the exact failure being investigated. Record which tier produced a trace so analysts understand what evidence is absent.
