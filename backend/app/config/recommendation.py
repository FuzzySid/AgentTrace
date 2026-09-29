"""Human product judgment shown with computed telemetry measurements."""

TELEMETRY_RECOMMENDATION = {
    "default_tier": "attrs",
    "tradeoff": "Use attrs for routine operation: it retains the attributes needed to find and classify failures while dropping prompt and completion content. Keep full capture for a bounded debugging run when the actual conversation is needed. Sampled capture can lower volume, but it may omit the trace needed to explain an individual task.",
}
